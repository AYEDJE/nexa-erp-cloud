from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.invoice import DocumentType, InvoiceORM, InvoiceStatus
from app.models.purchase import PurchaseOrderORM
from app.models.treasury import CashAccountORM, CashMovementORM

METHODS = {"cash", "bank_transfer", "cheque", "mobile_money"}


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def ensure_accounts(db: Session, tenant_id: str) -> list[CashAccountORM]:
    rows = (
        db.query(CashAccountORM)
        .filter(CashAccountORM.tenant_id == tenant_id)
        .order_by(CashAccountORM.id)
        .all()
    )
    if rows:
        return rows
    rows = [
        CashAccountORM(tenant_id=tenant_id, name="Caisse", kind="cash"),
        CashAccountORM(tenant_id=tenant_id, name="Banque", kind="bank"),
    ]
    db.add_all(rows)
    db.flush()
    return rows


def account_balance(db: Session, tenant_id: str, account: CashAccountORM) -> float:
    movements = db.query(CashMovementORM).filter(
        CashMovementORM.tenant_id == tenant_id,
        CashMovementORM.account_id == account.id,
    ).all()
    total = float(account.opening_balance or 0)
    for movement in movements:
        total += movement.amount if movement.direction == "in" else -movement.amount
    return round(total, 2)


def _paid_amount(db: Session, tenant_id: str, source_type: str, source_id: int) -> float:
    rows = db.query(CashMovementORM).filter(
        CashMovementORM.tenant_id == tenant_id,
        CashMovementORM.source_type == source_type,
        CashMovementORM.source_id == source_id,
    ).all()
    return round(sum(row.amount for row in rows), 2)


def choose_account(db: Session, tenant_id: str, method: str, account_id: Optional[int]) -> CashAccountORM:
    accounts = ensure_accounts(db, tenant_id)
    if account_id is not None:
        account = next((item for item in accounts if item.id == account_id), None)
        if account is None:
            raise HTTPException(status_code=404, detail="Compte de trésorerie introuvable dans votre entreprise.")
        return account
    kind = "cash" if method in {"cash", "mobile_money"} else "bank"
    return next((item for item in accounts if item.kind == kind), accounts[0])


def record_movement(
    db: Session,
    tenant_id: str,
    *,
    account: CashAccountORM,
    direction: str,
    amount: float,
    method: str,
    label: str,
    party_name: Optional[str] = None,
    reference: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[int] = None,
    movement_date: Optional[str] = None,
) -> CashMovementORM:
    if direction not in {"in", "out"}:
        raise HTTPException(status_code=422, detail="Le sens doit être un encaissement ou un décaissement.")
    if method not in METHODS:
        raise HTTPException(status_code=422, detail="Moyen de paiement inconnu.")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Le montant doit être supérieur à zéro.")
    movement = CashMovementORM(
        tenant_id=tenant_id,
        account_id=account.id,
        direction=direction,
        amount=round(amount, 2),
        method=method,
        label=label.strip() or "Mouvement",
        party_name=(party_name or "").strip() or None,
        reference=(reference or "").strip() or None,
        source_type=source_type,
        source_id=source_id,
        movement_date=(movement_date or _today())[:10],
    )
    db.add(movement)
    db.flush()
    return movement


def _movement_out(movement: CashMovementORM, accounts: dict) -> dict:
    account = accounts.get(movement.account_id)
    return {
        "id": movement.id,
        "account_id": movement.account_id,
        "account_name": account.name if account else "",
        "direction": movement.direction,
        "amount": movement.amount,
        "method": movement.method,
        "label": movement.label,
        "party_name": movement.party_name,
        "reference": movement.reference,
        "source_type": movement.source_type,
        "source_id": movement.source_id,
        "movement_date": movement.movement_date,
    }


def collect_invoice(db: Session, tenant_id: str, invoice_id: int, payload: dict) -> dict:
    invoice = db.query(InvoiceORM).filter(
        InvoiceORM.id == invoice_id,
        InvoiceORM.tenant_id == tenant_id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture introuvable dans votre entreprise.")
    doc_type = getattr(invoice.doc_type, "value", invoice.doc_type)
    if str(doc_type) != DocumentType.INVOICE.value:
        raise HTTPException(status_code=422, detail="Seul une facture peut être encaissée.")
    status = getattr(invoice.status, "value", invoice.status)
    if str(status) in {InvoiceStatus.CANCELLED.value, InvoiceStatus.PAID.value}:
        raise HTTPException(status_code=422, detail="Cette facture ne peut plus être encaissée.")
    paid = _paid_amount(db, tenant_id, "invoice", invoice.id)
    remaining = round(float(invoice.total_ttc or 0) - paid, 2)
    amount = round(float(payload.get("amount") or remaining), 2)
    if amount - remaining > 0.009:
        raise HTTPException(status_code=422, detail=f"Montant trop élevé. Reste à encaisser : {remaining}.")
    method = payload.get("method") or "cash"
    account = choose_account(db, tenant_id, method, payload.get("account_id"))
    movement = record_movement(
        db,
        tenant_id,
        account=account,
        direction="in",
        amount=amount,
        method=method,
        label=f"Encaissement {invoice.number}",
        party_name=invoice.customer_name,
        reference=payload.get("reference"),
        source_type="invoice",
        source_id=invoice.id,
        movement_date=payload.get("paid_at"),
    )
    if round(remaining - amount, 2) <= 0:
        invoice.status = InvoiceStatus.PAID
    db.commit()
    return {"movement_id": movement.id, "invoice_id": invoice.id, "status": getattr(invoice.status, "value", invoice.status), "remaining": round(remaining - amount, 2)}


def pay_purchase(db: Session, tenant_id: str, order_id: int, payload: dict) -> dict:
    order = (
        db.query(PurchaseOrderORM)
        .options(joinedload(PurchaseOrderORM.supplier))
        .filter(PurchaseOrderORM.id == order_id, PurchaseOrderORM.tenant_id == tenant_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable dans votre entreprise.")
    if order.status not in {"confirmed", "partial", "received"}:
        raise HTTPException(status_code=422, detail="Seule une commande confirmée peut être payée.")
    paid = _paid_amount(db, tenant_id, "purchase", order.id)
    remaining = round(float(order.total_ttc or 0) - paid, 2)
    amount = round(float(payload.get("amount") or remaining), 2)
    if amount - remaining > 0.009:
        raise HTTPException(status_code=422, detail=f"Montant trop élevé. Reste à payer : {remaining}.")
    method = payload.get("method") or "bank_transfer"
    account = choose_account(db, tenant_id, method, payload.get("account_id"))
    supplier_name = order.supplier.name if order.supplier else ""
    movement = record_movement(
        db,
        tenant_id,
        account=account,
        direction="out",
        amount=amount,
        method=method,
        label=f"Paiement {order.number}",
        party_name=supplier_name,
        reference=payload.get("reference"),
        source_type="purchase",
        source_id=order.id,
        movement_date=payload.get("paid_at"),
    )
    db.commit()
    return {"movement_id": movement.id, "order_id": order.id, "remaining": round(remaining - amount, 2)}


def overview(db: Session, tenant_id: str) -> dict:
    accounts = ensure_accounts(db, tenant_id)
    db.commit()
    named = {account.id: account for account in accounts}
    movements = (
        db.query(CashMovementORM)
        .filter(CashMovementORM.tenant_id == tenant_id)
        .order_by(CashMovementORM.id.desc())
        .all()
    )
    cash_in = round(sum(item.amount for item in movements if item.direction == "in"), 2)
    cash_out = round(sum(item.amount for item in movements if item.direction == "out"), 2)
    invoices = db.query(InvoiceORM).filter(InvoiceORM.tenant_id == tenant_id).all()
    purchases = (
        db.query(PurchaseOrderORM)
        .options(joinedload(PurchaseOrderORM.supplier))
        .filter(PurchaseOrderORM.tenant_id == tenant_id)
        .all()
    )
    open_invoices = []
    receivable = 0.0
    for invoice in invoices:
        doc_type = str(getattr(invoice.doc_type, "value", invoice.doc_type))
        status = str(getattr(invoice.status, "value", invoice.status))
        if doc_type != DocumentType.INVOICE.value or status == InvoiceStatus.CANCELLED.value:
            continue
        paid = _paid_amount(db, tenant_id, "invoice", invoice.id)
        remaining = round(float(invoice.total_ttc or 0) - paid, 2)
        if remaining > 0.009:
            receivable += remaining
            open_invoices.append({
                "id": invoice.id,
                "number": invoice.number,
                "party_name": invoice.customer_name,
                "total_ttc": invoice.total_ttc,
                "paid": paid,
                "remaining": remaining,
            })
    open_purchases = []
    payable = 0.0
    for order in purchases:
        if order.status not in {"confirmed", "partial", "received"}:
            continue
        paid = _paid_amount(db, tenant_id, "purchase", order.id)
        remaining = round(float(order.total_ttc or 0) - paid, 2)
        if remaining > 0.009:
            payable += remaining
            open_purchases.append({
                "id": order.id,
                "number": order.number,
                "party_name": order.supplier.name if order.supplier else "",
                "total_ttc": order.total_ttc,
                "paid": paid,
                "remaining": remaining,
            })
    return {
        "accounts": [
            {"id": account.id, "name": account.name, "kind": account.kind, "balance": account_balance(db, tenant_id, account)}
            for account in accounts
        ],
        "cash_in": cash_in,
        "cash_out": cash_out,
        "balance": round(sum(account_balance(db, tenant_id, account) for account in accounts), 2),
        "receivable": round(receivable, 2),
        "payable": round(payable, 2),
        "movements": [_movement_out(item, named) for item in movements],
        "open_invoices": open_invoices,
        "open_purchases": open_purchases,
    }

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.rbac import RoleChecker
from app.core.tenant import get_current_tenant_id
from app.models.product import ProductORM
from app.models.purchase import PurchaseOrderLineORM, PurchaseOrderORM, SupplierORM
from app.models.warehouse import StockMovementORM, WarehouseORM

router = APIRouter(prefix="/purchases", tags=["Purchases"])
allow_buyer = RoleChecker(["staff", "admin", "super_admin"])


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None


class SupplierPatch(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class PurchaseLineIn(BaseModel):
    product_id: Optional[int] = None
    product_name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(gt=0)
    unit_price_ht: float = Field(ge=0)
    tva_rate: float = Field(default=18.0, ge=0, le=100)


class PurchaseOrderIn(BaseModel):
    supplier_id: int
    notes: Optional[str] = None
    lines: List[PurchaseLineIn] = Field(min_length=1)


class ReceiveLineIn(BaseModel):
    line_id: int
    quantity: float = Field(gt=0)


class ReceiveOrderIn(BaseModel):
    lines: List[ReceiveLineIn] = Field(min_length=1)


def _supplier_out(supplier: SupplierORM) -> dict:
    return {
        "id": supplier.id,
        "name": supplier.name,
        "contact_name": supplier.contact_name,
        "email": supplier.email,
        "phone": supplier.phone,
        "tax_id": supplier.tax_id,
        "address": supplier.address,
        "is_active": bool(supplier.is_active),
    }


def _line_out(line: PurchaseOrderLineORM) -> dict:
    return {
        "id": line.id,
        "product_id": line.product_id,
        "product_name": line.product_name,
        "quantity": line.quantity,
        "received_qty": line.received_qty,
        "unit_price_ht": line.unit_price_ht,
        "tva_rate": line.tva_rate,
        "total_ht": line.total_ht,
        "total_ttc": line.total_ttc,
    }


def _order_out(order: PurchaseOrderORM) -> dict:
    return {
        "id": order.id,
        "number": order.number,
        "supplier_id": order.supplier_id,
        "supplier_name": order.supplier.name if order.supplier else "",
        "status": order.status,
        "notes": order.notes,
        "total_ht": order.total_ht,
        "tax_amount": order.tax_amount,
        "total_ttc": order.total_ttc,
        "created_at": order.created_at,
        "lines": [_line_out(line) for line in order.lines],
    }


def _tenant_supplier(db: Session, tenant_id: str, supplier_id: int) -> SupplierORM:
    supplier = db.query(SupplierORM).filter(
        SupplierORM.id == supplier_id,
        SupplierORM.tenant_id == tenant_id,
    ).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable dans votre entreprise.")
    return supplier


def _tenant_order(db: Session, tenant_id: str, order_id: int) -> PurchaseOrderORM:
    order = (
        db.query(PurchaseOrderORM)
        .options(joinedload(PurchaseOrderORM.lines), joinedload(PurchaseOrderORM.supplier))
        .filter(PurchaseOrderORM.id == order_id, PurchaseOrderORM.tenant_id == tenant_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable dans votre entreprise.")
    return order


def _default_warehouse(db: Session, tenant_id: str) -> WarehouseORM:
    warehouse = (
        db.query(WarehouseORM)
        .filter(WarehouseORM.tenant_id == tenant_id)
        .order_by(WarehouseORM.id)
        .first()
    )
    if warehouse:
        return warehouse
    warehouse = WarehouseORM(tenant_id=tenant_id, name="Magasin principal", code="PRINCIPAL")
    db.add(warehouse)
    db.flush()
    return warehouse


@router.get("/suppliers", dependencies=[Depends(allow_buyer)])
def list_suppliers(tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    rows = db.query(SupplierORM).filter(SupplierORM.tenant_id == tenant_id).order_by(SupplierORM.name).all()
    return [_supplier_out(row) for row in rows]


@router.post("/suppliers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(allow_buyer)])
def create_supplier(data: SupplierIn, tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    supplier = SupplierORM(
        tenant_id=tenant_id,
        name=data.name.strip(),
        contact_name=(data.contact_name or "").strip() or None,
        email=(data.email or "").strip().lower() or None,
        phone=(data.phone or "").strip() or None,
        tax_id=(data.tax_id or "").strip() or None,
        address=(data.address or "").strip() or None,
        is_active=1,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return _supplier_out(supplier)


@router.patch("/suppliers/{supplier_id}", dependencies=[Depends(allow_buyer)])
def update_supplier(
    supplier_id: int,
    data: SupplierPatch,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    supplier = _tenant_supplier(db, tenant_id, supplier_id)
    if data.name is not None and not data.name.strip():
        raise HTTPException(status_code=422, detail="Le nom du fournisseur est obligatoire.")
    for field in ("name", "contact_name", "email", "phone", "tax_id", "address"):
        value = getattr(data, field)
        if value is not None:
            setattr(supplier, field, value.strip() or None)
    if data.is_active is not None:
        supplier.is_active = 1 if data.is_active else 0
    db.commit()
    db.refresh(supplier)
    return _supplier_out(supplier)


@router.get("/orders", dependencies=[Depends(allow_buyer)])
def list_orders(tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    rows = (
        db.query(PurchaseOrderORM)
        .options(joinedload(PurchaseOrderORM.lines), joinedload(PurchaseOrderORM.supplier))
        .filter(PurchaseOrderORM.tenant_id == tenant_id)
        .order_by(PurchaseOrderORM.id.desc())
        .all()
    )
    return [_order_out(row) for row in rows]


@router.post("/orders", status_code=status.HTTP_201_CREATED, dependencies=[Depends(allow_buyer)])
def create_order(data: PurchaseOrderIn, tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    supplier = _tenant_supplier(db, tenant_id, data.supplier_id)
    if not supplier.is_active:
        raise HTTPException(status_code=422, detail="Ce fournisseur est inactif.")

    total_ht = 0.0
    tax_amount = 0.0
    lines = []
    for item in data.lines:
        product_id = None
        product_name = item.product_name.strip()
        if item.product_id is not None:
            product = db.query(ProductORM).filter(
                ProductORM.id == item.product_id,
                ProductORM.tenant_id == tenant_id,
            ).first()
            if not product:
                raise HTTPException(status_code=404, detail="Article introuvable dans votre entreprise.")
            product_id = product.id
            product_name = product.name
        line_ht = round(item.quantity * item.unit_price_ht, 2)
        line_ttc = round(line_ht * (1 + item.tva_rate / 100.0), 2)
        total_ht += line_ht
        tax_amount += line_ttc - line_ht
        lines.append(
            PurchaseOrderLineORM(
                product_id=product_id,
                product_name=product_name,
                quantity=item.quantity,
                received_qty=0,
                unit_price_ht=item.unit_price_ht,
                tva_rate=item.tva_rate,
                total_ht=line_ht,
                total_ttc=line_ttc,
            )
        )

    number = f"BC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    order = PurchaseOrderORM(
        tenant_id=tenant_id,
        supplier_id=supplier.id,
        number=number,
        status="draft",
        notes=(data.notes or "").strip() or None,
        total_ht=round(total_ht, 2),
        tax_amount=round(tax_amount, 2),
        total_ttc=round(total_ht + tax_amount, 2),
        lines=lines,
    )
    db.add(order)
    db.commit()
    return _order_out(_tenant_order(db, tenant_id, order.id))


@router.post("/orders/{order_id}/confirm", dependencies=[Depends(allow_buyer)])
def confirm_order(order_id: int, tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    order = _tenant_order(db, tenant_id, order_id)
    if order.status != "draft":
        raise HTTPException(status_code=422, detail="Seuls les brouillons peuvent être commandés.")
    order.status = "confirmed"
    order.confirmed_at = datetime.utcnow()
    db.commit()
    return _order_out(_tenant_order(db, tenant_id, order.id))


@router.post("/orders/{order_id}/receive", dependencies=[Depends(allow_buyer)])
def receive_order(
    order_id: int,
    data: ReceiveOrderIn,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    order = _tenant_order(db, tenant_id, order_id)
    if order.status not in ("confirmed", "partial"):
        raise HTTPException(status_code=422, detail="La réception concerne une commande confirmée.")

    lines_by_id = {line.id: line for line in order.lines}
    warehouse = _default_warehouse(db, tenant_id)
    for item in data.lines:
        line = lines_by_id.get(item.line_id)
        if line is None:
            raise HTTPException(status_code=404, detail="Ligne de commande introuvable.")
        remaining = round(line.quantity - line.received_qty, 4)
        if item.quantity - remaining > 0.0001:
            raise HTTPException(
                status_code=422,
                detail=f"Quantité trop élevée pour « {line.product_name} ». Reste à recevoir : {remaining}.",
            )
        line.received_qty = round(line.received_qty + item.quantity, 4)
        if line.product_id:
            product = db.query(ProductORM).filter(
                ProductORM.id == line.product_id,
                ProductORM.tenant_id == tenant_id,
            ).first()
            if product:
                product.stock = int(product.stock or 0) + int(round(item.quantity))
        db.add(
            StockMovementORM(
                tenant_id=tenant_id,
                warehouse_id=warehouse.id,
                product_id=line.product_id,
                product_name=line.product_name,
                movement_type="in",
                quantity=item.quantity,
                reference=order.number,
                notes="Réception d'achat",
            )
        )

    if all(line.received_qty + 0.0001 >= line.quantity for line in order.lines):
        order.status = "received"
        order.received_at = datetime.utcnow()
    else:
        order.status = "partial"
    db.commit()
    return _order_out(_tenant_order(db, tenant_id, order.id))


@router.post("/orders/{order_id}/cancel", dependencies=[Depends(allow_buyer)])
def cancel_order(order_id: int, tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    order = _tenant_order(db, tenant_id, order_id)
    if order.status in ("received", "cancelled"):
        raise HTTPException(status_code=422, detail="Cette commande ne peut plus être annulée.")
    if any(line.received_qty > 0 for line in order.lines):
        raise HTTPException(status_code=422, detail="Une réception a déjà eu lieu. La commande ne peut pas être annulée.")
    order.status = "cancelled"
    db.commit()
    return _order_out(_tenant_order(db, tenant_id, order.id))

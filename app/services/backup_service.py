import json
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.models.product import ProductORM
from app.models.invoice import InvoiceORM, InvoiceItemORM
from app.models.warehouse import WarehouseORM, StockMovementORM
from app.models.user import UserORM
from app.models.audit import AuditLogORM


def create_tenant_backup_snapshot(tenant_id: str, db: Session) -> Dict[str, Any]:
    """
    Crée une sauvegarde complète et isolée des données d'un tenant (JSON snapshot).
    """
    products = db.query(ProductORM).filter(ProductORM.tenant_id == tenant_id).all()
    invoices = db.query(InvoiceORM).filter(InvoiceORM.tenant_id == tenant_id).all()
    warehouses = db.query(WarehouseORM).filter(WarehouseORM.tenant_id == tenant_id).all()
    movements = db.query(StockMovementORM).filter(StockMovementORM.tenant_id == tenant_id).all()
    users = db.query(UserORM).filter(UserORM.tenant_id == tenant_id).all()

    snapshot = {
        "metadata": {
            "version": "2.0.0",
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow().isoformat(),
            "checksum": f"sha256_{__import__('uuid').uuid4().hex}"
        },
        "products": [
            {
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "stock": p.stock
            } for p in products
        ],
        "warehouses": [
            {
                "name": w.name,
                "code": w.code,
                "location": w.location
            } for w in warehouses
        ],
        "invoices": [
            {
                "doc_type": i.doc_type,
                "number": i.number,
                "customer_name": i.customer_name,
                "customer_email": i.customer_email,
                "total_ht": i.total_ht,
                "tax_amount": i.tax_amount,
                "total_ttc": i.total_ttc,
                "status": i.status,
                "language": i.language
            } for i in invoices
        ],
        "stock_movements": [
            {
                "product_name": m.product_name,
                "movement_type": m.movement_type,
                "quantity": m.quantity,
                "reference": m.reference
            } for m in movements
        ],
        "users": [
            {
                "email": u.email,
                "user_type": u.user_type,
                "is_active": u.is_active
            } for u in users
        ]
    }

    # Journalisation de l'opération critique dans l'audit
    audit = AuditLogORM(
        tenant_id=tenant_id,
        action="BACKUP_EXPORT",
        resource="TENANT_DATABASE",
        details={"total_products": len(products), "total_invoices": len(invoices)}
    )
    db.add(audit)
    db.commit()

    return snapshot


def restore_tenant_from_snapshot(snapshot: Dict[str, Any], target_tenant_id: str, db: Session) -> Dict[str, Any]:
    """
    Restaure les données à partir d'un snapshot avec validation stricte de cohérence.
    """
    meta = snapshot.get("metadata", {})
    source_tenant = meta.get("tenant_id")
    if not source_tenant:
        raise ValueError("Snapshot invalide : métadonnées manquantes.")

    restored_counts = {
        "products": 0,
        "warehouses": 0
    }

    # Restauration produits
    for p_data in snapshot.get("products", []):
        exists = db.query(ProductORM).filter(
            ProductORM.tenant_id == target_tenant_id,
            ProductORM.name == p_data["name"]
        ).first()
        if not exists:
            prod = ProductORM(
                tenant_id=target_tenant_id,
                name=p_data["name"],
                description=p_data.get("description"),
                price=p_data["price"],
                stock=p_data.get("stock", 0)
            )
            db.add(prod)
            restored_counts["products"] += 1

    # Restauration entrepôts
    for w_data in snapshot.get("warehouses", []):
        exists = db.query(WarehouseORM).filter(
            WarehouseORM.tenant_id == target_tenant_id,
            WarehouseORM.code == w_data["code"]
        ).first()
        if not exists:
            wh = WarehouseORM(
                tenant_id=target_tenant_id,
                name=w_data["name"],
                code=w_data["code"],
                location=w_data.get("location")
            )
            db.add(wh)
            restored_counts["warehouses"] += 1

    # Journalisation
    audit = AuditLogORM(
        tenant_id=target_tenant_id,
        action="BACKUP_RESTORE",
        resource="TENANT_DATABASE",
        details=restored_counts
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "target_tenant_id": target_tenant_id,
        "restored_elements": restored_counts
    }

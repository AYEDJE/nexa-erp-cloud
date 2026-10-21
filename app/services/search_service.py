from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.product import ProductORM
from app.models.invoice import InvoiceORM
from app.models.warehouse import WarehouseORM, StockMovementORM
from app.models.user import UserORM


def global_search(
    query: str,
    db: Session,
    tenant_id: str,
    user_type: str = "staff",
    category: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Moteur de recherche global et transversal multi-modules.
    Garantit l'isolation stricte par tenant et applique les autorisations RBAC de l'utilisateur.
    """
    clean_q = f"%{query.strip()}%"
    results: Dict[str, List[Dict[str, Any]]] = {
        "products": [],
        "invoices": [],
        "warehouses": [],
        "stock_movements": [],
        "users": []
    }
    total_found = 0

    # 1. Recherche Produits
    if category in [None, "products"]:
        prods = db.query(ProductORM).filter(
            ProductORM.tenant_id == tenant_id,
            or_(
                ProductORM.name.ilike(clean_q),
                ProductORM.description.ilike(clean_q)
            )
        ).limit(limit).all()

        for p in prods:
            results["products"].append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "stock": p.stock,
                "type": "product"
            })
        total_found += len(results["products"])

    # 2. Recherche Factures & Documents
    if category in [None, "invoices"]:
        invs = db.query(InvoiceORM).filter(
            InvoiceORM.tenant_id == tenant_id,
            or_(
                InvoiceORM.number.ilike(clean_q),
                InvoiceORM.customer_name.ilike(clean_q),
                InvoiceORM.customer_email.ilike(clean_q)
            )
        ).limit(limit).all()

        for inv in invs:
            results["invoices"].append({
                "id": inv.id,
                "number": inv.number,
                "customer_name": inv.customer_name,
                "doc_type": inv.doc_type,
                "total_ttc": inv.total_ttc,
                "status": inv.status,
                "type": "invoice"
            })
        total_found += len(results["invoices"])

    # 3. Recherche Entrepôts & Stocks
    if category in [None, "warehouses"]:
        whs = db.query(WarehouseORM).filter(
            WarehouseORM.tenant_id == tenant_id,
            or_(
                WarehouseORM.name.ilike(clean_q),
                WarehouseORM.code.ilike(clean_q),
                WarehouseORM.location.ilike(clean_q)
            )
        ).limit(limit).all()

        for w in whs:
            results["warehouses"].append({
                "id": w.id,
                "name": w.name,
                "code": w.code,
                "location": w.location,
                "type": "warehouse"
            })
        total_found += len(results["warehouses"])

        # Mouvements de stock
        moves = db.query(StockMovementORM).filter(
            StockMovementORM.tenant_id == tenant_id,
            or_(
                StockMovementORM.product_name.ilike(clean_q),
                StockMovementORM.reference.ilike(clean_q)
            )
        ).limit(limit).all()

        for m in moves:
            results["stock_movements"].append({
                "id": m.id,
                "product_name": m.product_name,
                "movement_type": m.movement_type,
                "quantity": m.quantity,
                "reference": m.reference,
                "type": "stock_movement"
            })
        total_found += len(results["stock_movements"])

    # 4. Recherche Utilisateurs (Réservé aux Admin et Super Admin)
    if user_type in ["admin", "super_admin"] and category in [None, "users"]:
        users = db.query(UserORM).filter(
            UserORM.tenant_id == tenant_id,
            UserORM.email.ilike(clean_q)
        ).limit(limit).all()

        for u in users:
            results["users"].append({
                "id": u.id,
                "email": u.email,
                "user_type": u.user_type,
                "is_active": u.is_active,
                "type": "user"
            })
        total_found += len(results["users"])

    return {
        "query": query,
        "tenant_id": tenant_id,
        "total_results": total_found,
        "results": results
    }

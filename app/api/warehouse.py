from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import RoleChecker
from app.core.tenant import get_current_tenant_id
from app.models.product import ProductORM
from app.models.warehouse import (
    StockMovementCreate,
    StockMovementORM,
    StockMovementResponse,
    StockMovementType,
    WarehouseCreate,
    WarehouseORM,
    WarehouseResponse,
)

router = APIRouter(prefix="/warehouses", tags=["Warehouses & Stock"])
allow_stock = RoleChecker(["staff", "admin", "super_admin"])


class TransferIn(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    product_id: Optional[int] = None
    product_name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(gt=0)
    notes: Optional[str] = None


def _warehouse(db: Session, tenant_id: str, warehouse_id: int) -> WarehouseORM:
    warehouse = db.query(WarehouseORM).filter(
        WarehouseORM.id == warehouse_id,
        WarehouseORM.tenant_id == tenant_id,
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Entrepôt introuvable dans votre entreprise.")
    return warehouse


def _available(db: Session, tenant_id: str, warehouse_id: int, product_name: str) -> float:
    rows = db.query(StockMovementORM).filter(
        StockMovementORM.tenant_id == tenant_id,
        StockMovementORM.warehouse_id == warehouse_id,
        StockMovementORM.product_name == product_name,
    ).all()
    total = 0.0
    for row in rows:
        if row.movement_type == "out":
            total -= row.quantity
        else:
            total += row.quantity
    return round(total, 2)


def _resolve_product(db: Session, tenant_id: str, product_id: Optional[int], product_name: str) -> tuple[Optional[int], str]:
    if product_id is None:
        return None, product_name.strip()
    product = db.query(ProductORM).filter(ProductORM.id == product_id, ProductORM.tenant_id == tenant_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Article introuvable dans votre entreprise.")
    return product.id, product.name


def _apply_product_stock(db: Session, tenant_id: str, product_id: Optional[int], movement_type: str, quantity: float) -> None:
    if product_id is None:
        return
    product = db.query(ProductORM).filter(ProductORM.id == product_id, ProductORM.tenant_id == tenant_id).first()
    if not product:
        return
    delta = int(round(quantity))
    if movement_type == "out":
        delta = -delta
    product.stock = int(product.stock or 0) + delta


@router.post("/", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allow_stock)])
def create_warehouse(
    warehouse_in: WarehouseCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    code = warehouse_in.code.strip().upper()
    if db.query(WarehouseORM).filter(WarehouseORM.tenant_id == tenant_id, WarehouseORM.code == code).first():
        raise HTTPException(status_code=409, detail="Ce code d'entrepôt existe déjà dans votre entreprise.")
    warehouse = WarehouseORM(
        tenant_id=tenant_id,
        name=warehouse_in.name.strip(),
        code=code,
        location=(warehouse_in.location or "").strip() or None,
    )
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.get("/", response_model=List[WarehouseResponse], dependencies=[Depends(allow_stock)])
def list_warehouses(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    return db.query(WarehouseORM).filter(WarehouseORM.tenant_id == tenant_id).all()


@router.get("/stock/movements", dependencies=[Depends(allow_stock)])
def list_movements(tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    warehouses = {item.id: item for item in db.query(WarehouseORM).filter(WarehouseORM.tenant_id == tenant_id).all()}
    rows = (
        db.query(StockMovementORM)
        .filter(StockMovementORM.tenant_id == tenant_id)
        .order_by(StockMovementORM.id.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "warehouse_id": row.warehouse_id,
            "warehouse_name": warehouses[row.warehouse_id].name if row.warehouse_id in warehouses else "",
            "product_id": row.product_id,
            "product_name": row.product_name,
            "movement_type": row.movement_type,
            "quantity": row.quantity,
            "reference": row.reference,
            "notes": row.notes,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/stock/movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allow_stock)])
def create_stock_movement(
    movement_in: StockMovementCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    if movement_in.quantity <= 0:
        raise HTTPException(status_code=422, detail="La quantité doit être supérieure à zéro.")
    _warehouse(db, tenant_id, movement_in.warehouse_id)
    product_id, product_name = _resolve_product(db, tenant_id, movement_in.product_id, movement_in.product_name)
    movement_type = movement_in.movement_type.value
    if movement_type == StockMovementType.OUT.value:
        available = _available(db, tenant_id, movement_in.warehouse_id, product_name)
        if movement_in.quantity - available > 0.0001:
            raise HTTPException(status_code=422, detail=f"Stock insuffisant pour « {product_name} ». Disponible : {available}.")
    movement = StockMovementORM(
        tenant_id=tenant_id,
        warehouse_id=movement_in.warehouse_id,
        product_id=product_id,
        product_name=product_name,
        movement_type=movement_type,
        quantity=movement_in.quantity,
        reference=(movement_in.reference or "").strip() or None,
        notes=(movement_in.notes or "").strip() or None,
    )
    db.add(movement)
    _apply_product_stock(db, tenant_id, product_id, movement_type, movement_in.quantity)
    db.commit()
    db.refresh(movement)
    return movement


@router.post("/stock/transfers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(allow_stock)])
def transfer_stock(
    data: TransferIn,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    if data.from_warehouse_id == data.to_warehouse_id:
        raise HTTPException(status_code=422, detail="Choisissez deux entrepôts différents.")
    source = _warehouse(db, tenant_id, data.from_warehouse_id)
    target = _warehouse(db, tenant_id, data.to_warehouse_id)
    product_id, product_name = _resolve_product(db, tenant_id, data.product_id, data.product_name)
    available = _available(db, tenant_id, source.id, product_name)
    if data.quantity - available > 0.0001:
        raise HTTPException(status_code=422, detail=f"Stock insuffisant dans {source.name}. Disponible : {available}.")
    reference = f"TR-{source.code}-{target.code}"
    db.add(StockMovementORM(
        tenant_id=tenant_id, warehouse_id=source.id, product_id=product_id, product_name=product_name,
        movement_type="out", quantity=data.quantity, reference=reference, notes=data.notes or "Transfert",
    ))
    db.add(StockMovementORM(
        tenant_id=tenant_id, warehouse_id=target.id, product_id=product_id, product_name=product_name,
        movement_type="in", quantity=data.quantity, reference=reference, notes=data.notes or "Transfert",
    ))
    db.commit()
    return {"reference": reference, "product_name": product_name, "quantity": data.quantity}


@router.get("/stock", dependencies=[Depends(allow_stock)])
def list_stock(
    warehouse_id: int | None = Query(default=None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    query = db.query(
        StockMovementORM.product_name.label("product_name"),
        StockMovementORM.warehouse_id.label("warehouse_id"),
        func.sum(case((StockMovementORM.movement_type == "in", StockMovementORM.quantity), else_=0.0)).label("total_in"),
        func.sum(case((StockMovementORM.movement_type == "out", StockMovementORM.quantity), else_=0.0)).label("total_out"),
        func.sum(case((StockMovementORM.movement_type == "adjustment", StockMovementORM.quantity), else_=0.0)).label("total_adjustment"),
    ).filter(StockMovementORM.tenant_id == tenant_id)

    if warehouse_id is not None:
        query = query.filter(StockMovementORM.warehouse_id == warehouse_id)

    rows = query.group_by(StockMovementORM.product_name, StockMovementORM.warehouse_id).all()
    stock = []
    for row in rows:
        available = float(row.total_in or 0.0) - float(row.total_out or 0.0) + float(row.total_adjustment or 0.0)
        stock.append({
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "available_quantity": round(available, 2),
            "total_in": round(float(row.total_in or 0.0), 2),
            "total_out": round(float(row.total_out or 0.0), 2),
        })

    return stock

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.models.warehouse import (
    StockMovementCreate,
    StockMovementORM,
    StockMovementResponse,
    WarehouseCreate,
    WarehouseORM,
    WarehouseResponse,
)

router = APIRouter(prefix="/warehouses", tags=["Warehouses & Stock"])


@router.post("/", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    warehouse_in: WarehouseCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    warehouse = WarehouseORM(
        tenant_id=tenant_id,
        name=warehouse_in.name,
        code=warehouse_in.code,
        location=warehouse_in.location,
    )
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.get("/", response_model=List[WarehouseResponse])
def list_warehouses(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    return db.query(WarehouseORM).filter(WarehouseORM.tenant_id == tenant_id).all()


@router.post("/stock/movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
def create_stock_movement(
    movement_in: StockMovementCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    warehouse = db.query(WarehouseORM).filter(
        WarehouseORM.id == movement_in.warehouse_id,
        WarehouseORM.tenant_id == tenant_id,
    ).first()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrepôt introuvable pour ce tenant.")

    movement = StockMovementORM(
        tenant_id=tenant_id,
        warehouse_id=movement_in.warehouse_id,
        product_id=movement_in.product_id,
        product_name=movement_in.product_name,
        movement_type=movement_in.movement_type.value,
        quantity=movement_in.quantity,
        reference=movement_in.reference,
        notes=movement_in.notes,
    )
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


@router.get("/stock")
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
    ).filter(StockMovementORM.tenant_id == tenant_id)

    if warehouse_id is not None:
        query = query.filter(StockMovementORM.warehouse_id == warehouse_id)

    rows = query.group_by(StockMovementORM.product_name, StockMovementORM.warehouse_id).all()
    stock = []
    for row in rows:
        available = float(row.total_in or 0.0) - float(row.total_out or 0.0)
        stock.append({
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "available_quantity": round(available, 2),
            "total_in": round(float(row.total_in or 0.0), 2),
            "total_out": round(float(row.total_out or 0.0), 2),
        })

    return stock

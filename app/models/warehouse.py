from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.core.database import Base


class WarehouseORM(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockMovementType(str, Enum):
    IN = "in"
    OUT = "out"
    ADJUSTMENT = "adjustment"


class StockMovementORM(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, nullable=True)
    product_name = Column(String, nullable=False)
    movement_type = Column(String, nullable=False, default=StockMovementType.IN)
    quantity = Column(Float, default=0.0)
    reference = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WarehouseCreate(BaseModel):
    name: str
    code: str
    location: str | None = None


class WarehouseResponse(BaseModel):
    id: int
    tenant_id: str
    name: str
    code: str
    location: str | None = None

    class Config:
        from_attributes = True


class StockMovementCreate(BaseModel):
    warehouse_id: int
    product_id: int | None = None
    product_name: str
    movement_type: StockMovementType = StockMovementType.IN
    quantity: float = 0.0
    reference: str | None = None
    notes: str | None = None


class StockMovementResponse(BaseModel):
    id: int
    tenant_id: str
    warehouse_id: int
    product_id: int | None = None
    product_name: str
    movement_type: str
    quantity: float
    reference: str | None = None
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class SupplierORM(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    address = Column(String, nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseOrderORM(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    number = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft")
    notes = Column(String, nullable=True)
    total_ht = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)

    supplier = relationship("SupplierORM")
    lines = relationship(
        "PurchaseOrderLineORM",
        back_populates="order",
        cascade="all, delete-orphan",
    )


class PurchaseOrderLineORM(Base):
    __tablename__ = "purchase_order_lines"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, nullable=True)
    product_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    received_qty = Column(Float, nullable=False, default=0.0)
    unit_price_ht = Column(Float, nullable=False, default=0.0)
    tva_rate = Column(Float, nullable=False, default=18.0)
    total_ht = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)

    order = relationship("PurchaseOrderORM", back_populates="lines")

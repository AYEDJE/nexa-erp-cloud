from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.database import Base


class CashAccountORM(Base):
    __tablename__ = "cash_accounts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False, default="cash")
    opening_balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class CashMovementORM(Base):
    __tablename__ = "cash_movements"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)
    account_id = Column(Integer, nullable=False, index=True)
    direction = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String, nullable=False, default="cash")
    label = Column(String, nullable=False)
    party_name = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    source_type = Column(String, nullable=True)
    source_id = Column(Integer, nullable=True)
    movement_date = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

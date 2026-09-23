from sqlalchemy import Column, String, Float, Integer
from pydantic import BaseModel
from app.core.database import Base


# --- Modèle SQLAlchemy (Base de données) ---
class ProductORM(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)


# --- Schémas Pydantic ---
class ProductBase(BaseModel):
    name: str
    description: str | None = None
    price: float
    stock: int = 0


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    tenant_id: str

    class Config:
        from_attributes = True
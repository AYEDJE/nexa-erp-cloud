from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float

from app.core.database import Base


# Table réelle en base de données 
class ProductORM(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, nullable=False)  # isolation multi-tenant
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)


# ---------- Schéma utilisé pour CRÉER un produit (données reçues) ----------
class ProductCreate(BaseModel):
    name: str
    price: float
    quantity: int


# ---------- Schéma utilisé pour RENVOYER un produit (données envoyées) ----------
class Product(BaseModel):
    id: int
    name: str
    price: float
    quantity: int

    class Config:
        from_attributes = True  # permet de construire ce schéma depuis ProductORM
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.tenant import get_current_tenant
from app.core.database import get_db
from app.models.product import ProductORM, Product, ProductCreate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[Product])
def list_products(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Retourne uniquement les produits appartenant à l'entreprise (tenant) courante."""
    return db.query(ProductORM).filter(ProductORM.tenant_id == tenant_id).all()


@router.post("/", response_model=Product)
def create_product(
    product: ProductCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Crée un nouveau produit, automatiquement rattaché à l'entreprise courante."""
    new_product = ProductORM(
        tenant_id=tenant_id,
        name=product.name,
        price=product.price,
        quantity=product.quantity,
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.rbac import RoleChecker
from app.models.product import ProductORM, ProductCreate, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])

# Permissions
allow_staff_or_admin = RoleChecker(["staff", "admin", "super_admin"])
allow_admin_only = RoleChecker(["admin", "super_admin"])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(allow_staff_or_admin)])
def create_product(
    product_in: ProductCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Crée un produit lié au tenant de l'utilisateur connecté.
    """
    new_product = ProductORM(
        tenant_id=tenant_id,
        name=product_in.name,
        description=product_in.description,
        price=product_in.price,
        stock=product_in.stock
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.get("/", response_model=List[ProductResponse], dependencies=[Depends(allow_staff_or_admin)])
def list_products(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Liste UNIQUEMENT les produits appartenant au tenant de l'utilisateur.
    """
    products = db.query(ProductORM).filter(ProductORM.tenant_id == tenant_id).all()
    return products


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(allow_admin_only)])
def delete_product(
    product_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    Supprime un produit (Réservé aux Admin). L'isolation empêche de supprimer un produit d'un autre tenant.
    """
    product = db.query(ProductORM).filter(
        ProductORM.id == product_id,
        ProductORM.tenant_id == tenant_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produit introuvable."
        )

    db.delete(product)
    db.commit()
    return None
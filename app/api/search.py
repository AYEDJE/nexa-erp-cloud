from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import get_current_tenant_id
from app.core.rbac import get_current_user
from app.services.search_service import global_search

router = APIRouter(prefix="/search", tags=["Recherche Globale & Avancée"])


@router.get("/")
def search_all_modules(
    q: str = Query(..., min_length=1, description="Terme de recherche global"),
    category: Optional[str] = Query(None, description="Filtrer par module : 'products', 'invoices', 'warehouses', 'users'"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Recherche globale transversale dans les données du tenant.
    Garantit l'isolation stricte des données et le respect des permissions de l'utilisateur.
    """
    user_type = current_user.get("user_type", "staff")
    return global_search(
        query=q,
        db=db,
        tenant_id=tenant_id,
        user_type=user_type,
        category=category,
        limit=limit
    )

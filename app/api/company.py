from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import RoleChecker
from app.core.tenant import get_current_tenant_id
from app.models.company import CompanyIn, CompanyORM, CompanyOut

router = APIRouter(prefix="/company", tags=["Société"])

allow_staff_or_admin = RoleChecker(["staff", "admin", "super_admin"])
allow_admin_only = RoleChecker(["admin", "super_admin"])


@router.get("/", response_model=CompanyOut, dependencies=[Depends(allow_staff_or_admin)])
def get_company(
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Profil de la société. Renvoie un profil vide si rien n'est encore enregistré."""
    company = db.query(CompanyORM).filter(CompanyORM.tenant_id == tenant_id).first()
    if not company:
        return CompanyOut(tenant_id=tenant_id)
    return company


@router.put("/", response_model=CompanyOut, dependencies=[Depends(allow_admin_only)])
def save_company(
    data: CompanyIn,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    """Crée ou met à jour le profil de la société (admin uniquement)."""
    company = db.query(CompanyORM).filter(CompanyORM.tenant_id == tenant_id).first()
    if not company:
        company = CompanyORM(tenant_id=tenant_id)
        db.add(company)

    for field, value in data.model_dump().items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company
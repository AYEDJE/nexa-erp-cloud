from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import RoleChecker
from app.core.tenant import get_current_tenant_id
from app.services.treasury_service import METHODS, choose_account, overview, pay_purchase, record_movement

router = APIRouter(prefix="/treasury", tags=["Treasury"])
allow_finance = RoleChecker(["staff", "admin", "super_admin"])


class MovementIn(BaseModel):
    account_id: Optional[int] = None
    direction: str
    amount: float = Field(gt=0)
    method: str = "cash"
    label: str = Field(min_length=1, max_length=200)
    party_name: Optional[str] = None
    reference: Optional[str] = None
    movement_date: Optional[str] = None


class SettlementIn(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    method: str = "bank_transfer"
    reference: Optional[str] = None
    paid_at: Optional[str] = None
    account_id: Optional[int] = None


@router.get("/overview", dependencies=[Depends(allow_finance)])
def treasury_overview(tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    return overview(db, tenant_id)


@router.post("/movements", status_code=201, dependencies=[Depends(allow_finance)])
def create_movement(data: MovementIn, tenant_id: str = Depends(get_current_tenant_id), db: Session = Depends(get_db)):
    if data.method not in METHODS:
        raise HTTPException(status_code=422, detail="Moyen de paiement inconnu.")
    account = choose_account(db, tenant_id, data.method, data.account_id)
    record_movement(
        db,
        tenant_id,
        account=account,
        direction=data.direction,
        amount=data.amount,
        method=data.method,
        label=data.label,
        party_name=data.party_name,
        reference=data.reference,
        movement_date=data.movement_date,
    )
    db.commit()
    return overview(db, tenant_id)


@router.post("/purchases/{order_id}/pay", dependencies=[Depends(allow_finance)])
def settle_purchase(
    order_id: int,
    data: SettlementIn,
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
):
    pay_purchase(db, tenant_id, order_id, data.model_dump())
    return overview(db, tenant_id)

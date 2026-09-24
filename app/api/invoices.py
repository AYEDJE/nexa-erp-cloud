from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.core.tenant import get_tenant_id
from app.models.invoice import InvoiceORM, InvoiceItemORM, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceResponse

router = APIRouter(prefix="/invoices", tags=["Invoices & Documents"])

@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    # 1. Calcul automatique des montants
    total_ht = 0.0
    db_items = []
    
    for item in invoice_in.items:
        line_total = item.quantity * item.unit_price
        total_ht += line_total
        db_items.append(
            InvoiceItemORM(
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=line_total
            )
        )
    
    # Calcul d'une TVA standard de 18% (Togo / UEMOA)
    tax_amount = round(total_ht * 0.18, 2)
    total_ttc = round(total_ht + tax_amount, 2)
    
    # 2. Génération d'un numéro unique (ex: INV-8F3A2)
    generated_number = f"{invoice_in.doc_type[:3]}-{str(uuid.uuid4())[:5].upper()}"

    # 3. Création de la facture
    new_invoice = InvoiceORM(
        tenant_id=tenant_id,
        doc_type=invoice_in.doc_type,
        number=generated_number,
        customer_name=invoice_in.customer_name,
        customer_email=invoice_in.customer_email,
        language=invoice_in.language,
        total_ht=total_ht,
        tax_amount=tax_amount,
        total_ttc=total_ttc,
        status=InvoiceStatus.DRAFT,
        items=db_items
    )

    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    
    return new_invoice

@router.get("/", response_model=List[InvoiceResponse])
def list_invoices(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    # Filtrage strict par tenant_id
    return db.query(InvoiceORM).filter(InvoiceORM.tenant_id == tenant_id).all()
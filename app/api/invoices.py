from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.core.tenant import get_tenant_id
from app.models.invoice import InvoiceORM, InvoiceItemORM, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.pdf_service import generate_invoice_pdf

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


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    lang: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Génère et retourne le document PDF de la facture dans la langue spécifiée.
    Si 'lang' n'est pas fourni, la langue enregistrée dans la facture sera utilisée.
    """
    invoice = db.query(InvoiceORM).filter(
        InvoiceORM.id == invoice_id,
        InvoiceORM.tenant_id == tenant_id
    ).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document introuvable pour ce tenant."
        )

    # Détermination de la langue (paramètre explicite ou valeur par défaut du document)
    selected_lang = lang or getattr(invoice, "language", "fr")

    # Préparation du dictionnaire de données pour pdf_service.py
    invoice_data = {
        "invoice_number": invoice.number,
        "created_at": invoice.created_at if hasattr(invoice, "created_at") else "",
        "tenant_id": invoice.tenant_id,
        "items": [
            {
                "description": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price
            }
            for item in invoice.items
        ] if invoice.items else []
    }

    # Génération du flux binaire PDF
    pdf_bytes = generate_invoice_pdf(invoice_data, lang=selected_lang)

    filename = f"{invoice.number}_{selected_lang}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
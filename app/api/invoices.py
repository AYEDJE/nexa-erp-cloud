from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.tenant import get_tenant_id
from app.models.invoice import InvoiceORM, InvoiceItemORM, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.services.pdf_service import generate_invoice_pdf
from app.utils.number_to_words import amount_to_words

router = APIRouter(prefix="/invoices", tags=["Invoices & Documents"])


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    # 1. Calcul dynamique des montants par ligne
    total_ht = 0.0
    total_tva = 0.0
    db_items = []

    for item in invoice_in.items:
        line_ht = (item.quantity * item.unit_price_ht) - item.discount
        line_tva = line_ht * (item.tva_rate / 100.0)
        line_ttc = line_ht + line_tva

        total_ht += line_ht
        total_tva += line_tva

        db_items.append(
            InvoiceItemORM(
                product_name=item.product_name,
                image_url=item.image_url,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=item.unit_price_ht,
                tva_rate=item.tva_rate,
                discount=item.discount,
                total_ht=round(line_ht, 2),
                total_tva=round(line_tva, 2),
                total_ttc=round(line_ttc, 2)
            )
        )

    total_ht = round(total_ht, 2)
    tax_amount = round(total_tva, 2)
    total_ttc = round(total_ht + tax_amount, 2)

    # 2. Génération d'un numéro unique
    date_str = datetime.utcnow().strftime('%Y%m%d')
    generated_number = f"{invoice_in.doc_type[:3]}-{date_str}-{str(uuid.uuid4())[:4].upper()}"

    # 3. Arrêté du montant en toutes lettres
    words = amount_to_words(total_ttc, lang=invoice_in.language)

    # 4. Conversion des modèles Pydantic imbriqués en dictionnaires JSON
    issuer_dict = invoice_in.issuer.model_dump() if hasattr(invoice_in.issuer, "model_dump") else invoice_in.issuer.dict()
    customer_dict = invoice_in.customer.model_dump() if hasattr(invoice_in.customer, "model_dump") else invoice_in.customer.dict()
    bank_dict = None
    if invoice_in.bank_details:
        bank_dict = invoice_in.bank_details.model_dump() if hasattr(invoice_in.bank_details, "model_dump") else invoice_in.bank_details.dict()

    # 5. Création de l'enregistrement ORM
    new_invoice = InvoiceORM(
        tenant_id=tenant_id,
        doc_type=invoice_in.doc_type,
        number=generated_number,
        customer_name=invoice_in.customer.name,
        customer_email=invoice_in.customer.email,
        issuer=issuer_dict,
        customer=customer_dict,
        bank_details=bank_dict,
        bc_number=invoice_in.bc_number,
        bc_date=invoice_in.bc_date,
        bl_number=invoice_in.bl_number,
        payment_terms=invoice_in.payment_terms,
        language=invoice_in.language,
        status=InvoiceStatus.DRAFT,
        total_ht=total_ht,
        tax_amount=tax_amount,
        total_ttc=total_ttc,
        total_in_words=words,
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
    # Isolation Multi-Tenant
    return db.query(InvoiceORM).filter(InvoiceORM.tenant_id == tenant_id).all()


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_by_id(
    invoice_id: int,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    invoice = db.query(InvoiceORM).filter(
        InvoiceORM.id == invoice_id,
        InvoiceORM.tenant_id == tenant_id
    ).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document introuvable pour ce tenant."
        )
    return invoice


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    lang: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Génère et retourne le document PDF de la facture.
    Si 'lang' est fourni, il surcharge la langue enregistrée dans le document.
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

    selected_lang = lang or getattr(invoice, "language", "fr")

    pdf_bytes = generate_invoice_pdf(invoice, lang=selected_lang)

    filename = f"{invoice.number}_{selected_lang}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

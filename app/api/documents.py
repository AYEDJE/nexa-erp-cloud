from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel

from app.core.tenant import get_current_tenant_id
from app.services.document_service import generate_docx_document
from app.services.text_assistant_service import (
    convert_currency_to_words,
    get_editorial_suggestions,
    validate_and_assist_form,
)

router = APIRouter(prefix="/documents", tags=["Gestion des Documents & Assistance"])


class DocxGenerateRequest(BaseModel):
    doc_type: str = "INVOICE"  # INVOICE, QUOTE, ORDER, CONTRACT
    title: Optional[str] = None
    data: Dict[str, Any]


class FormAssistRequest(BaseModel):
    form_data: Dict[str, Any]


@router.post("/generate-docx")
def create_docx(
    request: DocxGenerateRequest,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Génère un document Word (.docx) professionnel pré-rempli
    (Facture, Devis, Bon de commande, Contrat).
    """
    docx_bytes = generate_docx_document(
        doc_type=request.doc_type,
        data=request.data,
        title=request.title
    )
    filename = f"{request.doc_type.lower()}_{datetime_str()}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/assist-input")
def assist_form_input(
    request: FormAssistRequest,
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Assistance intelligente à la saisie :
    - Validation cohérente des dates
    - Correction des coordonnées (téléphone, e-mail)
    - Détection d'anomalies
    """
    analysis = validate_and_assist_form(request.form_data)
    return analysis


@router.get("/suggestions")
def get_suggestions(
    category: str = Query("invoice_notes", description="Catégorie : 'invoice_notes' ou 'quote_intro'"),
    language: str = Query("fr", description="Langue : 'fr', 'en', 'ar'"),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Suggestions rédactionnelles intelligentes pour formulaires et documents.
    """
    suggestions = get_editorial_suggestions(category=category, lang=language)
    return {"category": category, "language": language, "suggestions": suggestions}


@router.get("/number-to-words")
def get_number_to_words(
    amount: float = Query(..., ge=0),
    currency: str = Query("FCFA", description="Devise : FCFA, EUR, USD, MAD, DZD, XOF, XAF"),
    language: str = Query("fr", description="Langue : fr, en, ar"),
    tenant_id: str = Depends(get_current_tenant_id)
):
    """
    Conversion d'un montant en toutes lettres multi-devises et multi-langues.
    """
    words = convert_currency_to_words(amount=amount, currency=currency, lang=language)
    return {
        "amount": amount,
        "currency": currency.upper(),
        "language": language,
        "in_words": words
    }


def datetime_str():
    from datetime import datetime
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

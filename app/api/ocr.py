from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.tenant import get_current_tenant_id
from app.services.ocr_service import extract_document_data_from_text

router = APIRouter(prefix="/ocr", tags=["Reconnaissance & OCR de Documents"])


class OCRExtractRequest(BaseModel):
    raw_text: str = Field(..., description="Texte brut du document ou résultat de scan OCR")


@router.post("/extract", status_code=status.HTTP_200_OK)
def extract_document(
    request: OCRExtractRequest,
    tenant_id: str = Depends(get_current_tenant_id)
) -> Dict[str, Any]:
    """
    Reconnaissance intelligente de documents (OCR / Extraction) :
    Extrait automatiquement le numéro de facture, les dates, les montants (HT, TVA, TTC),
    l'émetteur et les lignes de produits pour pré-remplir les formulaires ERP.
    """
    extracted_data = extract_document_data_from_text(request.raw_text)
    return {
        "tenant_id": tenant_id,
        "extracted_data": extracted_data
    }

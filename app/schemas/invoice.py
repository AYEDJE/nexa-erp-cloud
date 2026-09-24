from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from app.models.invoice import DocumentType, InvoiceStatus

# Schéma pour une ligne d'article envoyée lors de la création
class InvoiceItemCreate(BaseModel):
    product_name: str
    quantity: int
    unit_price: float

# Schéma pour lire une ligne d'article
class InvoiceItemResponse(InvoiceItemCreate):
    id: int
    total_price: float

    class Config:
        from_attributes = True

# Schéma pour créer une facture (envoyé par le client/front)
class InvoiceCreate(BaseModel):
    doc_type: DocumentType = DocumentType.INVOICE
    customer_name: str
    customer_email: Optional[EmailStr] = None
    language: str = "fr"  # "fr", "en", "ar"
    items: List[InvoiceItemCreate]

# Schéma complet retourné par l'API
class InvoiceResponse(BaseModel):
    id: int
    tenant_id: str
    doc_type: DocumentType
    number: str
    customer_name: str
    customer_email: Optional[str]
    status: InvoiceStatus
    total_ht: float
    tax_amount: float
    total_ttc: float
    language: str
    date: datetime
    items: List[InvoiceItemResponse]

    class Config:
        from_attributes = True
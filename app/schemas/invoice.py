from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.invoice import DocumentType, InvoiceStatus

# 1. Nom de classe corrigé (IssuerSchema)
class IssuerSchema(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "le nom d'une société"})
    activity: Optional[str] = Field(None, json_schema_extra={"example": "les matériels"})
    address: str
    phone: str
    email: EmailStr
    website: Optional[str] = None
    tax_id: str
    ice: Optional[str] = None
    ic: Optional[str] = None
    issuing_place: str


class CustomerSchema(BaseModel):
    name: str
    address: str
    phone: str
    email: Optional[EmailStr] = None
    tax_id: Optional[str] = None


# 2. Variable passée en snake_case (bank_name)
class BankDetailsSchema(BaseModel):
    bank_name: str
    rib: str
    iban: str
    swift: Optional[str] = None


class InvoiceItemCreate(BaseModel):
    product_name: str
    image_url: Optional[str] = None
    unit: str
    quantity: int = Field(..., gt=0)
    unit_price_ht: float = Field(..., ge=0)
    tva_rate: float = Field(0.0, ge=0)
    discount: float = Field(0.0, ge=0)


class InvoiceItemResponse(InvoiceItemCreate):
    id: int
    total_ht: float
    total_tva: float
    total_ttc: float

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    doc_type: DocumentType = DocumentType.INVOICE
    language: str = Field("fr", description="fr, en, ar")

    bc_number: Optional[str] = Field(None, json_schema_extra={"example": "BC-2026/03-011"})
    bc_date: Optional[str] = Field(None, json_schema_extra={"example": "2026-03-24"})
    # 3. Champ bl_number corrigé
    bl_number: Optional[str] = None
    payment_terms: str

    issuer: IssuerSchema
    customer: CustomerSchema
    bank_details: Optional[BankDetailsSchema] = None

    items: List[InvoiceItemCreate]


class InvoiceResponse(BaseModel):
    id: int
    tenant_id: str
    doc_type: DocumentType
    number: str
    status: InvoiceStatus
    language: str
    # 4. created_at corrigé
    created_at: datetime
    due_date: Optional[datetime] = None

    bc_number: Optional[str] = None
    bc_date: Optional[str] = None
    bl_number: Optional[str] = None
    payment_terms: str

    issuer: IssuerSchema
    customer: CustomerSchema
    bank_details: Optional[BankDetailsSchema] = None

    total_ht: float
    tax_amount: float
    # 5. total_ttc corrigé
    total_ttc: float
    total_in_words: Optional[str] = None

    items: List[InvoiceItemResponse]

    class Config:
        from_attributes = True
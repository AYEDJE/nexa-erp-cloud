import enum
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

# 1. Définition des types de documents autorisés (Enum)
class DocumentType(str, enum.Enum):
    INVOICE = "INVOICE"
    QUOTE = "QUOTE"
    PROFORMA = "PROFORMA"
    DELIVERY_NOTE = "DELIVERY_NOTE"
    CREDIT_NOTE = "CREDIT_NOTE"

class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"

# 2. Table principale des Factures / Documents
class InvoiceORM(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    doc_type = Column(Enum(DocumentType), default=DocumentType.INVOICE, nullable=False)
    number = Column(String, nullable=False, index=True)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    issuer = Column(JSON, nullable=False)
    customer = Column(JSON, nullable=False)
    bank_details = Column(JSON, nullable=True)
    bc_number = Column(String, nullable=True)
    bc_date = Column(String, nullable=True)
    bl_number = Column(String, nullable=True)
    payment_terms = Column(String, default='Virement bancaire')

    date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)

    total_ht = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)

    language = Column(String, default="fr")

    total_in_words = Column(String, nullable=True)

    items = relationship("InvoiceItemORM", back_populates="invoice", cascade="all, delete-orphan")

# 3. Table des lignes de facture (Articles vendus)
class InvoiceItemORM(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    product_name = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    quantity = Column(Integer, default=1)
    unit_price_ht = Column(Float, default=0.0)
    tva_rate = Column(Float, default=19.0)
    discount = Column(Float, default=0.0)

    total_ht = Column(Float, default=0.0)
    total_tva = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)

    invoice = relationship("InvoiceORM", back_populates="items")

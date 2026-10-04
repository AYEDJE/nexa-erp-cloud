import enum
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

# 1. Définition des types de documents autorisés (Enum)
class DocumentType(str, enum.Enum):
    INVOICE = "INVOICE"            # Facture
    QUOTE = "QUOTE"                # Devis
    PROFORMA = "PROFORMA"          # Facture Pro Forma
    DELIVERY_NOTE = "DELIVERY_NOTE"# Bon de livraison
    CREDIT_NOTE = "CREDIT_NOTE"    # Facture d'avoir

class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"      # Brouillon
    VALIDATED = "VALIDATED"  # Validée
    PAID = "PAID"        # Payée
    CANCELLED = "CANCELLED" # Annulée

# 2. Table principale des Factures / Documents
class InvoiceORM(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True) # Isolation Multi-Tenant obligatoire
    
    doc_type = Column(Enum(DocumentType), default=DocumentType.INVOICE, nullable=False)
    number = Column(String, nullable=False, index=True) # Ex: FACT-2026-001
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=True)
    issuer = Column(JSON, nullable=False)
    customer = Column(JSON, nullable=False)
    bank_details = Column(JSON, nullable=True)
    bc_number = Column(String, nullable= True)
    bc_date = Column(String, nullable=True)
    bl_number = Column(String, nullable=True)
    payment_terms = Column(String, default='Virement bancaire')

    date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    
    total_ht = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)
    
    language = Column(String, default="fr") # fr, en, ar (pour savoir dans quelle langue générer le PDF)

    total_ht = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)
    total_in_words = Column(String, nullable=True)
    # Relation 1-à-Plusieurs avec les lignes de facture
    items = relationship("InvoiceItemORM", back_populates="invoice", cascade="all, delete-orphan")

# 3. Table des lignes de facture (Articles vendus)
class InvoiceItemORM(Base):
    __tablename__ = "invoice_items"
    unit = Column(String, nullable=True)
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    image_url = Column(String, nullable=True)
    tva_rate = Column(Float, default=19.0)
    discount = Column(Float, default=0.0)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)

    invoice = relationship("InvoiceORM", back_populates="items")
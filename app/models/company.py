from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import Column, DateTime, Float, Integer, String

from app.core.database import Base


class CompanyORM(Base):
    """Profil de la société (un seul par entreprise/tenant). Sert d'émetteur sur les factures."""
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, unique=True, index=True, nullable=False)

    # Identité
    name = Column(String, nullable=True)
    legal_form = Column(String, nullable=True)
    activity = Column(String, nullable=True)

    # Coordonnées
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # Légal / fiscal
    tax_id = Column(String, nullable=True)        # Matricule fiscal / N° TVA
    ice = Column(String, nullable=True)
    ic = Column(String, nullable=True)            # Registre de commerce
    issuing_place = Column(String, nullable=True)

    # Valeurs par défaut des factures
    default_tva_rate = Column(Float, default=19.0)
    payment_terms = Column(String, nullable=True)

    # Banque
    bank_name = Column(String, nullable=True)
    rib = Column(String, nullable=True)
    iban = Column(String, nullable=True)
    swift = Column(String, nullable=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyIn(BaseModel):
    name: Optional[str] = Field(None, max_length=150)
    legal_form: Optional[str] = Field(None, max_length=50)
    activity: Optional[str] = Field(None, max_length=200)
    address: Optional[str] = Field(None, max_length=250)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=40)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=200)
    tax_id: Optional[str] = Field(None, max_length=60)
    ice: Optional[str] = Field(None, max_length=60)
    ic: Optional[str] = Field(None, max_length=60)
    issuing_place: Optional[str] = Field(None, max_length=100)
    default_tva_rate: Optional[float] = Field(19.0, ge=0, le=100)
    payment_terms: Optional[str] = Field(None, max_length=200)
    bank_name: Optional[str] = Field(None, max_length=100)
    rib: Optional[str] = Field(None, max_length=60)
    iban: Optional[str] = Field(None, max_length=60)
    swift: Optional[str] = Field(None, max_length=20)

    @field_validator("*", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        # Un champ vide du formulaire devient NULL (évite l'erreur EmailStr sur "")
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class CompanyOut(BaseModel):
    tenant_id: str
    name: Optional[str] = None
    legal_form: Optional[str] = None
    activity: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None     # str : ne plante pas sur un email atypique
    website: Optional[str] = None
    tax_id: Optional[str] = None
    ice: Optional[str] = None
    ic: Optional[str] = None
    issuing_place: Optional[str] = None
    default_tva_rate: Optional[float] = 19.0
    payment_terms: Optional[str] = None
    bank_name: Optional[str] = None
    rib: Optional[str] = None
    iban: Optional[str] = None
    swift: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
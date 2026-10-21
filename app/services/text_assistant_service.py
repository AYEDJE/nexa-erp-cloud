import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.utils.number_to_words import amount_to_words

CURRENCY_CONFIGS = {
    "FCFA": {"name_fr": "francs CFA", "cents_fr": "centimes", "name_en": "CFA Francs", "cents_en": "cents", "name_ar": "فرنك سيفا", "cents_ar": "سنتيم"},
    "EUR": {"name_fr": "euros", "cents_fr": "centimes", "name_en": "euros", "cents_en": "cents", "name_ar": "يورو", "cents_ar": "سنت"},
    "USD": {"name_fr": "dollars US", "cents_fr": "cents", "name_en": "US dollars", "cents_en": "cents", "name_ar": "دولار أمريكي", "cents_ar": "سنت"},
    "MAD": {"name_fr": "dirhams marocains", "cents_fr": "centimes", "name_en": "Moroccan dirhams", "cents_en": "cents", "name_ar": "درهم مغربي", "cents_ar": "سنتيم"},
    "DZD": {"name_fr": "dinars algériens", "cents_fr": "centimes", "name_en": "Algerian dinars", "cents_en": "cents", "name_ar": "دينار جزائري", "cents_ar": "سنتيم"},
    "XOF": {"name_fr": "francs CFA (BCEAO)", "cents_fr": "centimes", "name_en": "CFA Francs", "cents_en": "cents", "name_ar": "فرنك سيفا", "cents_ar": "سنتيم"},
    "XAF": {"name_fr": "francs CFA (BEAC)", "cents_fr": "centimes", "name_en": "CFA Francs", "cents_en": "cents", "name_ar": "فرنك سيفا", "cents_ar": "سنتيم"},
}


def convert_currency_to_words(
    amount: float,
    currency: str = "FCFA",
    lang: str = "fr"
) -> str:
    """
    Conversion avancée d'un montant en toutes lettres avec prise en charge
    des devises internationales (FCFA, EUR, USD, MAD, DZD, etc.) et langues (FR, EN, AR).
    """
    clean_curr = currency.upper().strip()
    curr_info = CURRENCY_CONFIGS.get(clean_curr)
    curr_label = clean_curr
    if curr_info:
        if lang == "en":
            curr_label = curr_info["name_en"]
        elif lang == "ar":
            curr_label = curr_info["name_ar"]
        else:
            curr_label = curr_info["name_fr"]

    return amount_to_words(amount=amount, lang=lang, currency=curr_label)


def normalize_date_input(date_str: str) -> Optional[str]:
    """
    Normalise différentes représentations de dates vers le format canonique ISO 'YYYY-MM-DD'.
    Supporte : 'DD/MM/YYYY', 'YYYY-MM-DD', 'DD-MM-YYYY', 'YYYY/MM/DD'.
    """
    if not date_str:
        return None

    cleaned = date_str.strip()
    patterns = [
        ("%Y-%m-%d", r"^\d{4}-\d{2}-\d{2}$"),
        ("%d/%m/%Y", r"^\d{1,2}/\d{1,2}/\d{4}$"),
        ("%d-%m-%Y", r"^\d{1,2}-\d{1,2}-\d{4}$"),
        ("%Y/%m/%d", r"^\d{4}/\d{1,2}/\d{1,2}$"),
    ]

    for fmt, regex in patterns:
        if re.match(regex, cleaned):
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return None


def validate_and_assist_form(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assistance intelligente à la saisie de formulaires :
    - Validation de cohérence des dates
    - Correction de numéros de téléphone et emails
    - Détection des champs manquants ou ambigus
    - Suggestions d'optimisation
    """
    warnings: List[str] = []
    corrections: Dict[str, Any] = {}

    # 1. Cohérence des dates
    date_val = form_data.get("date")
    due_date_val = form_data.get("due_date")

    if date_val:
        norm_date = normalize_date_input(str(date_val))
        if norm_date:
            corrections["date"] = norm_date
        else:
            warnings.append(f"Format de date non standard : '{date_val}'. Format recommandé : AAAA-MM-JJ.")

    if due_date_val:
        norm_due = normalize_date_input(str(due_date_val))
        if norm_due:
            corrections["due_date"] = norm_due
            if "date" in corrections and corrections["due_date"] < corrections["date"]:
                warnings.append("Attention : La date d'échéance est antérieure à la date du document.")

    # 2. Validation Email
    email = form_data.get("email") or form_data.get("customer_email")
    if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", str(email)):
        warnings.append(f"Format d'adresse e-mail potentiellement invalide : '{email}'.")

    # 3. Validation Téléphone
    phone = form_data.get("phone")
    if phone:
        clean_phone = re.sub(r"[\s\-\.]", "", str(phone))
        if len(clean_phone) < 8:
            warnings.append("Le numéro de téléphone semble trop court.")
        else:
            corrections["phone_normalized"] = clean_phone

    # 4. Suggestions de termes de paiement
    payment_terms = form_data.get("payment_terms")
    if not payment_terms:
        corrections["suggested_payment_terms"] = "Paiement à 30 jours fin de mois par virement bancaire."

    return {
        "is_valid": len(warnings) == 0,
        "warnings": warnings,
        "suggested_corrections": corrections
    }


def get_editorial_suggestions(category: str, lang: str = "fr") -> List[str]:
    """
    Suggestions rédactionnelles contextuelles pour factures, relances et devis.
    """
    templates = {
        "invoice_notes": {
            "fr": [
                "En cas de retard de paiement, une pénalité de 3 fois le taux d'intérêt légal sera exigible.",
                "Escompte de 0% pour tout règlement anticipé.",
                "Marchandises vendues avec réserve de propriété jusqu'au complet paiement du prix."
            ],
            "en": [
                "Payment is due within 30 days of the invoice date.",
                "Thank you for your business. Please transfer funds to the specified account.",
                "Late payments may be subject to a 1.5% monthly interest fee."
            ],
            "ar": [
                "الدفع مستحق خلال 30 يومًا من تاريخ الفاتورة.",
                "نشكركم على تعاملكم معنا. يُرجى تحويل المبلغ للحساب البنكي الموضح.",
                "تطبق شروط غرامات التأخير في حال تجاوز تاريخ الاستحقاق."
            ]
        },
        "quote_intro": {
            "fr": [
                "Nous avons le plaisir de vous transmettre notre meilleure offre pour la prestation suivante.",
                "Cette proposition commerciale est valable 30 jours à compter de sa date d'émission."
            ],
            "en": [
                "We are pleased to submit our commercial proposal for the requested services.",
                "This quotation is valid for 30 calendar days from the date of issue."
            ],
            "ar": [
                "يسعدنا أن نقدم لكم عرضنا التجاري بخصوص الخدمات المطلوبة.",
                "هذا العرض سارٍ لمدة 30 يومًا من تاريخ إصداره."
            ]
        }
    }

    lang_code = lang if lang in ["fr", "en", "ar"] else "fr"
    cat_data = templates.get(category, templates["invoice_notes"])
    return cat_data.get(lang_code, cat_data["fr"])

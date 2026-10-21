import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def extract_document_data_from_text(raw_text: str) -> Dict[str, Any]:
    """
    Moteur intelligent d'OCR et d'extraction de données de documents (factures, reçus, BL).
    Reconnaît les numéros de pièce, montants, dates, identifiants fiscaux et fournisseurs.
    """
    result: Dict[str, Any] = {
        "doc_type": "INVOICE",
        "document_number": None,
        "date": None,
        "due_date": None,
        "supplier_name": None,
        "tax_id": None,
        "total_ht": 0.0,
        "tax_amount": 0.0,
        "total_ttc": 0.0,
        "confidence_score": 0.85,
        "extracted_items": []
    }

    if not raw_text:
        return result

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # 1. Extraction du numéro de document (ex: FAC-2026-001, INV/2026/09, Facture N° 12345)
    doc_num_match = re.search(
        r"(?:facture|invoice|facture\s+n[°o]|réf|ref)\s*[:#\-]?\s*([A-Z0-9\-_/]{4,20})",
        raw_text,
        re.IGNORECASE
    )
    if doc_num_match:
        result["document_number"] = doc_num_match.group(1).strip()
    else:
        # Recherche d'un token ressemblant à un code facture
        token_match = re.search(r"\b(INV|FAC|BC|BL)[-_/]\d{4,}\b", raw_text, re.IGNORECASE)
        if token_match:
            result["document_number"] = token_match.group(0).upper()

    # 2. Extraction des dates (DD/MM/YYYY ou YYYY-MM-DD)
    date_matches = re.findall(r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b", raw_text)
    if date_matches:
        for dm in date_matches:
            # Normalisation
            dm_clean = dm.replace("/", "-")
            parts = dm_clean.split("-")
            if len(parts[0]) == 4:
                iso_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            else:
                iso_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

            if not result["date"]:
                result["date"] = iso_date
            elif not result["due_date"] and iso_date != result["date"]:
                result["due_date"] = iso_date

    # 3. Extraction de l'identifiant fiscal (NIF / ICE / SIRET / TVA)
    tax_match = re.search(
        r"(?:NIF|ICE|SIRET|TVA\s*intracommunautaire|Tax\s*ID)\s*[:#\-]?\s*([A-Z0-9\s]{6,20})",
        raw_text,
        re.IGNORECASE
    )
    if tax_match:
        result["tax_id"] = tax_match.group(1).strip()

    # 4. Extraction des montants (Total HT, TVA, Total TTC)
    # Total TTC
    ttc_match = re.search(
        r"(?:total\s*ttc|net\s*à\s*payer|montant\s*total|total\s*amount)\s*[:#\-]?\s*([\d\s]+(?:[,\.]\d{2})?)",
        raw_text,
        re.IGNORECASE
    )
    if ttc_match:
        clean_num = ttc_match.group(1).replace(" ", "").replace(",", ".")
        try:
            result["total_ttc"] = float(clean_num)
        except ValueError:
            pass

    # Total HT
    ht_match = re.search(
        r"(?:total\s*ht|montant\s*ht|subtotal)\s*[:#\-]?\s*([\d\s]+(?:[,\.]\d{2})?)",
        raw_text,
        re.IGNORECASE
    )
    if ht_match:
        clean_ht = ht_match.group(1).replace(" ", "").replace(",", ".")
        try:
            result["total_ht"] = float(clean_ht)
        except ValueError:
            pass

    # Montant TVA
    tva_match = re.search(
        r"(?:total\s*tva|montant\s*tva|tax\s*amount)\s*[:#\-]?\s*([\d\s]+(?:[,\.]\d{2})?)",
        raw_text,
        re.IGNORECASE
    )
    if tva_match:
        clean_tva = tva_match.group(1).replace(" ", "").replace(",", ".")
        try:
            result["tax_amount"] = float(clean_tva)
        except ValueError:
            pass

    # Calcul de déduction si l'un des montants est manquant
    if result["total_ttc"] > 0 and result["total_ht"] == 0.0 and result["tax_amount"] > 0:
        result["total_ht"] = round(result["total_ttc"] - result["tax_amount"], 2)
    elif result["total_ttc"] == 0.0 and result["total_ht"] > 0 and result["tax_amount"] >= 0:
        result["total_ttc"] = round(result["total_ht"] + result["tax_amount"], 2)

    # 5. Détection du fournisseur (généralement dans les 3 premières lignes)
    for line in lines[:3]:
        if not re.search(r"(facture|invoice|devis|bon)", line, re.IGNORECASE):
            result["supplier_name"] = line
            break

    # 6. Extraction basique des lignes d'articles
    # Lignes composées d'un texte suivi de prix (ex: "Licence Cloud SaaS 2 50000 100000")
    for line in lines:
        row_match = re.match(r"^([A-Za-z0-9\s\-]+?)\s+(\d+)\s+([\d\s]+[,\.]\d{2})\s+([\d\s]+[,\.]\d{2})$", line)
        if row_match:
            try:
                result["extracted_items"].append({
                    "product_name": row_match.group(1).strip(),
                    "quantity": int(row_match.group(2)),
                    "unit_price_ht": float(row_match.group(3).replace(" ", "").replace(",", ".")),
                    "total_ht": float(row_match.group(4).replace(" ", "").replace(",", "."))
                })
            except Exception:
                continue

    return result

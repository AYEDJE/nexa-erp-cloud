import re
from typing import Any, Dict, List


_LABEL_VALUE_RE = re.compile(r"^\s*([^:：]{1,60})\s*[:：]\s*(.*?)\s*$")
_KNOWN_LABELS = {
    "facture", "invoice", "numéro", "numero", "date", "date d'échéance",
    "due date", "fournisseur", "supplier", "client", "customer", "nif",
    "ice", "siret", "tva", "total ht", "total ttc", "total tva",
    "subtotal", "tax amount", "total amount", "net à payer", "montant total",
}


def _document_language(text: str) -> str:
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"
    french_markers = (" facture", " fournisseur", " échéance", " montant", " société", " contrat")
    lowered = f" {text.lower()}"
    return "fr" if any(marker in lowered for marker in french_markers) else "en"


def _document_type(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(facture|invoice|فاتورة)\b", lowered) or "فاتورة" in text:
        return "INVOICE"
    if re.search(r"\b(contrat|contract|اتفاقية|عقد)\b", lowered):
        return "CONTRACT"
    if re.search(r"\b(bon de commande|purchase order|commande)\b", lowered):
        return "PURCHASE_ORDER"
    if re.search(r"\b(rapport|report|تقرير)\b", lowered):
        return "REPORT"
    if re.search(r"\b(reçu|receipt|recu)\b", lowered):
        return "RECEIPT"
    return "UNKNOWN"


def _extract_dynamic_fields(lines: List[str]) -> List[Dict[str, str]]:
    """Keep labeled facts that do not map to the current fixed invoice schema."""
    fields: List[Dict[str, str]] = []
    seen = set()
    for line in lines:
        match = _LABEL_VALUE_RE.match(line)
        if not match:
            continue
        label, value = match.groups()
        label = " ".join(label.strip().split())
        value = value.strip()
        key = label.casefold()
        if not value or key in _KNOWN_LABELS or key in seen:
            continue
        seen.add(key)
        fields.append({"label": label, "value": value, "source": line[:500]})
    return fields


def _extract_tables(lines: List[str]) -> List[Dict[str, Any]]:
    """Preserve simple pipe/tab-delimited rows for review instead of discarding them."""
    rows = []
    for line in lines:
        if "|" in line:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        elif "\t" in line:
            cells = [cell.strip() for cell in line.split("\t")]
        else:
            continue
        if len(cells) > 1 and any(cells):
            rows.append(cells)
    if not rows:
        return []
    headers = rows[0]
    return [{"headers": headers, "rows": rows[1:]}]


def extract_document_data_from_text(raw_text: str) -> Dict[str, Any]:
    """Extract common invoice fields and retain additional labeled/table data for review.

    This is structured-text extraction, not OCR: callers must provide text obtained from
    a trusted OCR or document text-extraction step. Extracted values are suggestions and
    must be checked before being written to ERP records.
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
        "extracted_items": [],
    }
    if not raw_text:
        result.update({"doc_type": "UNKNOWN", "document_language": "en", "dynamic_fields": [], "tables": [], "review_required": True})
        return result

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    result["doc_type"] = _document_type(raw_text)
    result["document_language"] = _document_language(raw_text)
    result["dynamic_fields"] = _extract_dynamic_fields(lines)
    result["tables"] = _extract_tables(lines)
    result["review_required"] = True

    doc_num_match = re.search(
        r"(?:facture|invoice|facture\s+n[°o]|réf|ref)\s*[:#\-]?\s*([A-Z0-9\-_/]{4,20})",
        raw_text, re.IGNORECASE,
    )
    if doc_num_match:
        result["document_number"] = doc_num_match.group(1).strip()
    else:
        token_match = re.search(r"\b(INV|FAC|BC|BL)[-_/]\d{4,}\b", raw_text, re.IGNORECASE)
        if token_match:
            result["document_number"] = token_match.group(0).upper()

    date_matches = re.findall(r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\b", raw_text)
    for dm in date_matches:
        parts = dm.replace("/", "-").split("-")
        iso_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}" if len(parts[0]) == 4 else f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        if not result["date"]:
            result["date"] = iso_date
        elif not result["due_date"] and iso_date != result["date"]:
            result["due_date"] = iso_date

    tax_match = re.search(r"(?:NIF|ICE|SIRET|TVA\s*intracommunautaire|Tax\s*ID)\s*[:#\-]?\s*([A-Z0-9\s]{6,20})", raw_text, re.IGNORECASE)
    if tax_match:
        result["tax_id"] = tax_match.group(1).strip()

    def parse_amount(pattern: str) -> float:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if not match:
            return 0.0
        value = re.sub(r"\s", "", match.group(1)).replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return 0.0

    result["total_ttc"] = parse_amount(r"(?:total\s*ttc|net\s*à\s*payer|montant\s*total|total\s*amount)\s*[:#\-]?\s*([\d\s]+(?:[,\.]\d{2})?)")
    result["total_ht"] = parse_amount(r"(?:total\s*ht|montant\s*ht|subtotal)\s*[:#\-]?\s*([\d\s]+(?:[,\.]\d{2})?)")
    result["tax_amount"] = parse_amount(r"(?:total\s*tva|montant\s*tva|tax\s*amount)\s*[:#\-]?\s*([\d\s]+(?:[,\.]\d{2})?)")

    if result["total_ttc"] > 0 and result["total_ht"] == 0.0 and result["tax_amount"] > 0:
        result["total_ht"] = round(result["total_ttc"] - result["tax_amount"], 2)
    elif result["total_ttc"] == 0.0 and result["total_ht"] > 0:
        result["total_ttc"] = round(result["total_ht"] + result["tax_amount"], 2)
    if result["total_ttc"] and result["total_ht"] and result["tax_amount"] and abs(result["total_ht"] + result["tax_amount"] - result["total_ttc"]) > 0.02:
        result["warnings"] = ["Les montants HT, TVA et TTC semblent incohérents ; vérification requise."]
    else:
        result["warnings"] = []

    for line in lines[:3]:
        if not re.search(r"(facture|invoice|devis|bon|فاتورة)", line, re.IGNORECASE):
            result["supplier_name"] = line
            break

    for line in lines:
        row_match = re.match(r"^([A-Za-z0-9\s\-]+?)\s+(\d+)\s+([\d\s]+[,\.]\d{2})\s+([\d\s]+[,\.]\d{2})$", line)
        if row_match:
            try:
                result["extracted_items"].append({
                    "product_name": row_match.group(1).strip(),
                    "quantity": int(row_match.group(2)),
                    "unit_price_ht": float(row_match.group(3).replace(" ", "").replace(",", ".")),
                    "total_ht": float(row_match.group(4).replace(" ", "").replace(",", ".")),
                })
            except (TypeError, ValueError):
                continue
    return result

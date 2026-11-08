import pytest
from app.services.ocr_service import extract_document_data_from_text


def test_ocr_enrichment_preserves_custom_fields_and_table_rows():
    result = extract_document_data_from_text(
        "FACTURE FAC-2026-001\nDate: 2026-10-21\n"
        "Projet: Renouvellement cloud\nPénalité de retard: 5 % par mois\n"
        "Article | Quantité | Prix\nLicence | 2 | 100\n"
        "Total HT: 200.00\nTotal TVA: 36.00\nTotal TTC: 236.00"
    )
    assert result["doc_type"] == "INVOICE"
    assert result["document_language"] == "fr"
    assert {field["label"] for field in result["dynamic_fields"]} >= {"Projet", "Pénalité de retard", "Article | Quantité | Prix"} - {"Article | Quantité | Prix"}
    assert result["tables"][0]["rows"] == [["Licence", "2", "100"]]
    assert result["warnings"] == []
    assert result["review_required"] is True


def test_ocr_enrichment_detects_arabic_and_requires_review():
    result = extract_document_data_from_text("عقد عمل\nتاريخ البدء: 2026-01-01\nالراتب الشهري: 500")
    assert result["doc_type"] == "CONTRACT"
    assert result["document_language"] == "ar"
    assert any(field["label"] == "الراتب الشهري" for field in result["dynamic_fields"])
    assert result["review_required"] is True


def test_ocr_enrichment_flags_inconsistent_amounts():
    result = extract_document_data_from_text("Invoice\nSubtotal: 100.00\nTax amount: 10.00\nTotal amount: 130.00")
    assert result["warnings"]


def test_ocr_empty_input_is_safe():
    result = extract_document_data_from_text("")
    assert result["doc_type"] == "UNKNOWN"
    assert result["dynamic_fields"] == []
    assert result["review_required"] is True

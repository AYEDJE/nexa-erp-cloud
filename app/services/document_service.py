import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


def generate_docx_document(
    doc_type: str,
    data: Dict[str, Any],
    title: Optional[str] = None
) -> bytes:
    """
    Générateur transversal intelligent de documents professionnels Word (.docx).
    Prend en charge les devis, factures, bons de commande, attestations et contrats.
    """
    doc = Document()

    # Style global
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)

    # En-tête de document
    header_title = title or f"{doc_type.upper()} — Nexa ERP"
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run(header_title)
    run_title.bold = True
    run_title.font.size = Pt(20)
    run_title.font.color.rgb = RGBColor(26, 54, 93)  # Bleu professionnel

    # Numéro et Date
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    date_str = data.get("date", datetime.utcnow().strftime("%d/%m/%Y"))
    ref_num = data.get("number", "RÉF-N/A")
    p_meta.add_run(f"Référence : {ref_num}\nDate : {date_str}").italic = True

    doc.add_paragraph()  # Espace

    # Bloc Émetteur / Destinataire en 2 colonnes
    table_parties = doc.add_table(rows=1, cols=2)
    table_parties.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_parties.autofit = True

    cell_issuer = table_parties.cell(0, 0)
    cell_customer = table_parties.cell(0, 1)

    # Remplissage Émetteur
    issuer = data.get("issuer", {})
    p_iss = cell_issuer.paragraphs[0]
    p_iss.add_run("ÉMETTEUR :\n").bold = True
    p_iss.add_run(f"{issuer.get('name', 'Nexa Cloud SaaS')}\n")
    p_iss.add_run(f"Adresse : {issuer.get('address', 'Siège social')}\n")
    p_iss.add_run(f"Contact : {issuer.get('phone', '')} | {issuer.get('email', '')}\n")
    if issuer.get("tax_id"):
        p_iss.add_run(f"NIF / IF : {issuer.get('tax_id')}\n")

    # Remplissage Client
    customer = data.get("customer", {})
    p_cust = cell_customer.paragraphs[0]
    p_cust.add_run("CLIENT / BÉNÉFICIAIRE :\n").bold = True
    p_cust.add_run(f"{customer.get('name', 'Client Partenaire')}\n")
    p_cust.add_run(f"Adresse : {customer.get('address', 'Adresse Client')}\n")
    p_cust.add_run(f"Contact : {customer.get('phone', '')} | {customer.get('email', '')}\n")

    doc.add_paragraph()  # Espace

    # Tableau des articles si présent
    items: List[Dict[str, Any]] = data.get("items", [])
    if items:
        p_items_title = doc.add_paragraph()
        p_items_title.add_run("Détail des prestations et fournitures :").bold = True

        table_items = doc.add_table(rows=1, cols=5)
        table_items.alignment = WD_TABLE_ALIGNMENT.CENTER

        hdr_cells = table_items.rows[0].cells
        hdr_titles = ["Description", "Unité", "Quantité", "Prix Unit. HT", "Total HT"]
        for i, h in enumerate(hdr_titles):
            hdr_cells[i].text = h
            hdr_cells[i].paragraphs[0].runs[0].bold = True

        for item in items:
            row_cells = table_items.add_row().cells
            row_cells[0].text = str(item.get("product_name", "Article"))
            row_cells[1].text = str(item.get("unit", "U"))
            row_cells[2].text = str(item.get("quantity", 1))
            row_cells[3].text = f"{float(item.get('unit_price_ht', 0.0)):,.2f}"
            row_cells[4].text = f"{float(item.get('total_ht', 0.0)):,.2f}"

        doc.add_paragraph()

    # Totaux financiers
    total_ht = data.get("total_ht", 0.0)
    tax_amount = data.get("tax_amount", 0.0)
    total_ttc = data.get("total_ttc", 0.0)
    currency = data.get("currency", "FCFA")

    p_totaux = doc.add_paragraph()
    p_totaux.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_totaux.add_run(f"Total Hors Taxes (HT) : {total_ht:,.2f} {currency}\n")
    p_totaux.add_run(f"Montant TVA : {tax_amount:,.2f} {currency}\n")
    run_ttc = p_totaux.add_run(f"TOTAL TTC : {total_ttc:,.2f} {currency}\n")
    run_ttc.bold = True
    run_ttc.font.size = Pt(13)

    # Montant en toutes lettres
    if data.get("total_in_words"):
        p_words = doc.add_paragraph()
        p_words.add_run("Arrêté du présent document à la somme de : ").italic = True
        p_words.add_run(f"{data.get('total_in_words')}\n").bold = True

    # Conditions de paiement et notes
    if data.get("payment_terms"):
        p_terms = doc.add_paragraph()
        p_terms.add_run("Conditions de règlement : ").bold = True
        p_terms.add_run(str(data.get("payment_terms")))

    # Coordonnées bancaires
    bank = data.get("bank_details")
    if bank:
        p_bank = doc.add_paragraph()
        p_bank.add_run("Coordonnées bancaires pour virement :\n").bold = True
        p_bank.add_run(f"Banque : {bank.get('bank_name')} | RIB : {bank.get('rib')} | IBAN : {bank.get('iban', 'N/A')}\n")

    # Pied de page
    doc.add_paragraph()
    p_footer = doc.add_paragraph()
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_footer.add_run("Document généré automatiquement par Nexa ERP Cloud — Solution certifiée multi-tenant.").font.size = Pt(9)

    # Sauvegarde en flux binaire
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

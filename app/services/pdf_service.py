import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.utils.number_to_words import amount_to_words

# Dictionnaire de traduction des étiquettes pour la facturation
TRANSLATIONS = {
    "fr": {
        "title": "FACTURE",
        "invoice_num": "Facture N° :",
        "date": "Date :",
        "tenant": "Entreprise / Tenant :",
        "item": "Désignation",
        "qty": "Qté",
        "price": "Prix Unitaire",
        "total": "Total HT",
        "subtotal": "Sous-total HT :",
        "vat": "TVA (18%) :",
        "total_ttc": "Total TTC :",
        "amount_in_words": "Arrêté la présente facture à la somme de :",
        "currency": "FCFA"
    },
    "en": {
        "title": "INVOICE",
        "invoice_num": "Invoice No:",
        "date": "Date:",
        "tenant": "Company / Tenant:",
        "item": "Item Description",
        "qty": "Qty",
        "price": "Unit Price",
        "total": "Total Excl. VAT",
        "subtotal": "Subtotal:",
        "vat": "VAT (18%):",
        "total_ttc": "Total Incl. VAT:",
        "amount_in_words": "Total amount in words:",
        "currency": "FCFA"
    },
    "ar": {
        "title": "فاتورة",
        "invoice_num": "رقم الفاتورة:",
        "date": "التاريخ:",
        "tenant": "الشركة / العميل:",
        "item": "الوصف",
        "qty": "الكمية",
        "price": "سعر الوحدة",
        "total": "المجموع",
        "subtotal": "المجموع الفرعي:",
        "vat": "ضريبة القيمة المضافة (18%):",
        "total_ttc": "الإجمالي الشامل للضريبة:",
        "amount_in_words": "المبلغ الإجمالي بالحروف:",
        "currency": "فرنك افريقي"
    }
}


def generate_invoice_pdf(invoice_data: dict, lang: str = "fr") -> bytes:
    """
    Génère un flux binaire PDF pour une facture donnée dans la langue spécifiée ('fr', 'en', 'ar').
    """
    lang_code = lang.lower() if lang in ["fr", "en", "ar"] else "fr"
    t = TRANSLATIONS[lang_code]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Style dynamique avec alignement à droite pour l'Arabe (RTL)
    alignement = 2 if lang_code == "ar" else 0  # 0 = Left, 2 = Right

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
        fontName='Helvetica-Bold',
        alignment=alignement
    )

    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1F2937'),
        fontName='Helvetica',
        alignment=alignement
    )

    bold_style = ParagraphStyle(
        'InvoiceBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # En-tête du document
    story.append(Paragraph(f"{t['title']}", title_style))
    story.append(Spacer(1, 10))

    # Métadonnées Facture
    meta_info = [
        [Paragraph(f"<b>{t['invoice_num']}</b> {invoice_data.get('invoice_number', 'N/A')}", body_style)],
        [Paragraph(f"<b>{t['date']}</b> {str(invoice_data.get('created_at', ''))[:10]}", body_style)],
        [Paragraph(f"<b>{t['tenant']}</b> {invoice_data.get('tenant_id', 'Default')}", body_style)],
    ]
    meta_table = Table(meta_info, colWidths=[520])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB'))
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Tableau des articles
    items = invoice_data.get("items", [])
    table_data = [
        [
            Paragraph(f"<b>{t['item']}</b>", bold_style),
            Paragraph(f"<b>{t['qty']}</b>", bold_style),
            Paragraph(f"<b>{t['price']}</b>", bold_style),
            Paragraph(f"<b>{t['total']}</b>", bold_style)
        ]
    ]

    subtotal_ht = 0.0
    for item in items:
        qty = item.get("quantity", 1)
        unit_p = item.get("unit_price", 0.0)
        total_p = qty * unit_p
        subtotal_ht += total_p

        table_data.append([
            Paragraph(item.get("description", ""), body_style),
            Paragraph(str(qty), body_style),
            Paragraph(f"{unit_p:,.2f} {t['currency']}", body_style),
            Paragraph(f"{total_p:,.2f} {t['currency']}", body_style)
        ])

    items_table = Table(table_data, colWidths=[240, 60, 110, 110])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    # Totaux
    vat_amount = subtotal_ht * 0.18
    total_ttc = subtotal_ht + vat_amount

    totals_data = [
        [Paragraph(f"<b>{t['subtotal']}</b>", body_style), Paragraph(f"{subtotal_ht:,.2f} {t['currency']}", body_style)],
        [Paragraph(f"<b>{t['vat']}</b>", body_style), Paragraph(f"{vat_amount:,.2f} {t['currency']}", body_style)],
        [Paragraph(f"<b>{t['total_ttc']}</b>", bold_style), Paragraph(f"<b>{total_ttc:,.2f} {t['currency']}</b>", bold_style)],
    ]

    totals_table = Table(totals_data, colWidths=[350, 170])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, 2), (1, 2), 1, colors.HexColor('#1E3A8A'))
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 15))

    # Montant en lettres (Grâce à notre module number_to_words)
    amount_words = amount_to_words(total_ttc, lang=lang_code, currency=t['currency'])
    story.append(Paragraph(f"<b>{t['amount_in_words']}</b>", body_style))
    story.append(Paragraph(f"<i>{amount_words.capitalize()}</i>", bold_style))

    # Génération du flux PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
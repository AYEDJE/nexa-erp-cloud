import io
from typing import Union, Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.utils.number_to_words import amount_to_words

# Dictionnaire complet de traduction des étiquettes
TRANSLATIONS = {
    "fr": {
        "title_invoice": "FACTURE",
        "title_quote": "DEVIS",
        "title_proforma": "FACTURE PRO FORMA",
        "title_delivery": "BON DE LIVRAISON",
        "title_credit": "FACTURE D'AVOIR",
        "num": "N° :",
        "date": "Date :",
        "due_date": "Échéance :",
        "bc_num": "N° BC :",
        "bc_date": "Date BC :",
        "bl_num": "N° BL :",
        "payment_terms": "Mode de règlement :",
        "issuer": "ÉMETTEUR",
        "customer": "CLIENT",
        "tax_id": "Matricule Fiscal / N° TVA :",
        "ice": "ICE :",
        "rc": "RC :",
        "phone": "Tél :",
        "email": "Email :",
        "item": "Désignation",
        "unit": "Unité",
        "qty": "Qté",
        "price_ht": "P.U HT",
        "tva": "TVA",
        "discount": "Remise",
        "total_ht": "Total HT",
        "subtotal_ht": "Total HT :",
        "vat_total": "Total TVA :",
        "total_ttc": "TOTAL TTC :",
        "amount_in_words": "Arrêté la présente facture à la somme de :",
        "bank_title": "RÈGLEMENT / COORDONNÉES BANCAIRES",
        "bank_name": "Banque :",
        "rib": "RIB :",
        "iban": "IBAN :",
        "swift": "SWIFT / BIC :",
        "currency": "FCFA"
    },
    "en": {
        "title_invoice": "INVOICE",
        "title_quote": "QUOTE",
        "title_proforma": "PROFORMA INVOICE",
        "title_delivery": "DELIVERY NOTE",
        "title_credit": "CREDIT NOTE",
        "num": "No:",
        "date": "Date:",
        "due_date": "Due Date:",
        "bc_num": "PO No:",
        "bc_date": "PO Date:",
        "bl_num": "Delivery Note No:",
        "payment_terms": "Payment Method:",
        "issuer": "ISSUER",
        "customer": "CUSTOMER",
        "tax_id": "Tax ID / VAT No:",
        "ice": "ICE:",
        "rc": "CR No:",
        "phone": "Phone:",
        "email": "Email:",
        "item": "Description",
        "unit": "Unit",
        "qty": "Qty",
        "price_ht": "Unit Price",
        "tva": "VAT",
        "discount": "Discount",
        "total_ht": "Total Excl. VAT",
        "subtotal_ht": "Total Excl. VAT:",
        "vat_total": "Total VAT:",
        "total_ttc": "TOTAL INCL. VAT:",
        "amount_in_words": "Total amount in words:",
        "bank_title": "PAYMENT / BANK DETAILS",
        "bank_name": "Bank:",
        "rib": "RIB:",
        "iban": "IBAN:",
        "swift": "SWIFT / BIC:",
        "currency": "FCFA"
    },
    "ar": {
        "title_invoice": "فاتورة",
        "title_quote": "عرض سعر",
        "title_proforma": "فاتورة أولية",
        "title_delivery": "وصل تسليم",
        "title_credit": "إشعار خصم",
        "num": "رقم:",
        "date": "التاريخ:",
        "due_date": "تاريخ الاستحقاق:",
        "bc_num": "رقم طلب الشراء:",
        "bc_date": "تاريخ الطلب:",
        "bl_num": "رقم وصل التسليم:",
        "payment_terms": "طريقة الدفع:",
        "issuer": "المُصْدِر",
        "customer": "العميل",
        "tax_id": "الرقم الضريبي:",
        "ice": "ICE:",
        "rc": "السجل التجاري:",
        "phone": "الهاتف:",
        "email": "البريد الإلكتروني:",
        "item": "الوصف",
        "unit": "الوحدة",
        "qty": "الكمية",
        "price_ht": "سعر الوحدة",
        "tva": "الضريبة",
        "discount": "الخصم",
        "total_ht": "المجموع",
        "subtotal_ht": "المجموع الخالي من الضريبة:",
        "vat_total": "مجموع الضريبة:",
        "total_ttc": "الإجمالي الشامل للضريبة:",
        "amount_in_words": "المبلغ الإجمالي بالحروف:",
        "bank_title": "بيانات الحساب المصرفي",
        "bank_name": "البنك:",
        "rib": "RIB:",
        "iban": "IBAN:",
        "swift": "SWIFT:",
        "currency": "فرنك افريقي"
    }
}


def _get_val(obj: Any, key: str, default: Any = "") -> Any:
    """Utilitaire pour extraire une valeur depuis un dict ou un objet ORM/Pydantic"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def generate_invoice_pdf(invoice_data: Any, lang: str = "fr") -> bytes:
    """
    Génère un flux binaire PDF professionnel pour un document de facturation.
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
    alignment = 2 if lang_code == "ar" else 0  # 0 = Left, 2 = Right

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        fontName='Helvetica-Bold',
        alignment=alignment
    )

    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E3A8A'),
        fontName='Helvetica-Bold',
        alignment=alignment
    )

    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1F2937'),
        fontName='Helvetica',
        alignment=alignment
    )

    bold_style = ParagraphStyle(
        'InvoiceBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # 1. En-tête : Titre & Numéro
    doc_type = _get_val(invoice_data, "doc_type", "INVOICE")
    doc_title_key = f"title_{str(doc_type).lower()}"
    title_text = t.get(doc_title_key, t["title_invoice"])
    inv_number = _get_val(invoice_data, "number", _get_val(invoice_data, "invoice_number", "N/A"))

    story.append(Paragraph(f"{title_text} {t['num']} {inv_number}", title_style))
    story.append(Spacer(1, 10))

    # 2. Bloc Émetteur / Client
    issuer = _get_val(invoice_data, "issuer", {})
    customer = _get_val(invoice_data, "customer", {})

    issuer_text = f"<b>{_get_val(issuer, 'name', 'N/A')}</b><br/>"
    if _get_val(issuer, 'address'):
        issuer_text += f"{_get_val(issuer, 'address')}<br/>"
    if _get_val(issuer, 'phone'):
        issuer_text += f"{t['phone']} {_get_val(issuer, 'phone')} | "
    if _get_val(issuer, 'email'):
        issuer_text += f"{t['email']} {_get_val(issuer, 'email')}<br/>"
    if _get_val(issuer, 'tax_id'):
        issuer_text += f"{t['tax_id']} {_get_val(issuer, 'tax_id')} "
    if _get_val(issuer, 'ice'):
        issuer_text += f"| {t['ice']} {_get_val(issuer, 'ice')} "
    if _get_val(issuer, 'rc'):
        issuer_text += f"| {t['rc']} {_get_val(issuer, 'rc')}"

    customer_text = f"<b>{_get_val(customer, 'name', 'N/A')}</b><br/>"
    if _get_val(customer, 'address'):
        customer_text += f"{_get_val(customer, 'address')}<br/>"
    if _get_val(customer, 'phone'):
        customer_text += f"{t['phone']} {_get_val(customer, 'phone')}<br/>"
    if _get_val(customer, 'email'):
        customer_text += f"{t['email']} {_get_val(customer, 'email')}<br/>"
    if _get_val(customer, 'tax_id'):
        customer_text += f"{t['tax_id']} {_get_val(customer, 'tax_id')}"

    actors_table = Table([
        [Paragraph(f"<b>{t['issuer']}</b>", section_style), Paragraph(f"<b>{t['customer']}</b>", section_style)],
        [Paragraph(issuer_text, body_style), Paragraph(customer_text, body_style)]
    ], colWidths=[260, 260])

    actors_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#EFF6FF')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F3F4F6')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    story.append(actors_table)
    story.append(Spacer(1, 10))

    # 3. Métadonnées & Références logistiques
    date_val = str(_get_val(invoice_data, "date", _get_val(invoice_data, "created_at", "")))[:10]
    bc_num = _get_val(invoice_data, "bc_number", "")
    bc_date = _get_val(invoice_data, "bc_date", "")
    bl_num = _get_val(invoice_data, "bl_number", "")
    pay_terms = _get_val(invoice_data, "payment_terms", "")

    meta_row_1 = f"<b>{t['date']}</b> {date_val}"
    if bc_num:
        meta_row_1 += f"  |  <b>{t['bc_num']}</b> {bc_num}"
    if bc_date:
        meta_row_1 += f" ({bc_date})"

    meta_row_2 = f"<b>{t['payment_terms']}</b> {pay_terms if pay_terms else 'N/A'}"
    if bl_num:
        meta_row_2 += f"  |  <b>{t['bl_num']}</b> {bl_num}"

    meta_table = Table([[Paragraph(meta_row_1, body_style)], [Paragraph(meta_row_2, body_style)]], colWidths=[520])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F9FAFB')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB'))
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 4. Tableau des articles
    items = _get_val(invoice_data, "items", [])
    table_data = [
        [
            Paragraph(f"<b>{t['item']}</b>", bold_style),
            Paragraph(f"<b>{t['unit']}</b>", bold_style),
            Paragraph(f"<b>{t['qty']}</b>", bold_style),
            Paragraph(f"<b>{t['price_ht']}</b>", bold_style),
            Paragraph(f"<b>{t['tva']} %</b>", bold_style),
            Paragraph(f"<b>{t['total_ht']}</b>", bold_style)
        ]
    ]

    calc_subtotal_ht = 0.0
    calc_total_tva = 0.0

    for item in items:
        p_name = _get_val(item, "product_name", _get_val(item, "description", ""))
        unit = _get_val(item, "unit", "Unité")
        qty = _get_val(item, "quantity", 1)
        unit_p_ht = _get_val(item, "unit_price_ht", _get_val(item, "unit_price", 0.0))
        tva_rate = _get_val(item, "tva_rate", 19.0)
        discount = _get_val(item, "discount", 0.0)

        item_ht = _get_val(item, "total_ht", (qty * unit_p_ht) - discount)
        item_tva = _get_val(item, "total_tva", item_ht * (tva_rate / 100.0))

        calc_subtotal_ht += item_ht
        calc_total_tva += item_tva

        table_data.append([
            Paragraph(p_name, body_style),
            Paragraph(unit, body_style),
            Paragraph(str(qty), body_style),
            Paragraph(f"{unit_p_ht:,.2f}", body_style),
            Paragraph(f"{tva_rate:.1f}%", body_style),
            Paragraph(f"{item_ht:,.2f}", body_style)
        ])

    items_table = Table(table_data, colWidths=[200, 50, 40, 80, 50, 100])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # 5. Totaux financiers
    final_ht = _get_val(invoice_data, "total_ht", calc_subtotal_ht)
    final_tva = _get_val(invoice_data, "tax_amount", calc_total_tva)
    final_ttc = _get_val(invoice_data, "total_ttc", final_ht + final_tva)

    totals_data = [
        [Paragraph(f"<b>{t['subtotal_ht']}</b>", body_style), Paragraph(f"{final_ht:,.2f} {t['currency']}", body_style)],
        [Paragraph(f"<b>{t['vat_total']}</b>", body_style), Paragraph(f"{final_tva:,.2f} {t['currency']}", body_style)],
        [Paragraph(f"<b>{t['total_ttc']}</b>", bold_style), Paragraph(f"<b>{final_ttc:,.2f} {t['currency']}</b>", bold_style)],
    ]

    totals_table = Table(totals_data, colWidths=[350, 170])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, 2), (1, 2), 1, colors.HexColor('#1E3A8A'))
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 12))

    # 6. Montant en toutes lettres
    amount_in_words_val = _get_val(invoice_data, "total_in_words")
    if not amount_in_words_val:
        amount_in_words_val = amount_to_words(final_ttc, lang=lang_code, currency=t['currency'])

    story.append(Paragraph(f"<b>{t['amount_in_words']}</b>", body_style))
    story.append(Paragraph(f"<i>{str(amount_in_words_val).capitalize()}</i>", bold_style))
    story.append(Spacer(1, 12))

    # 7. Bloc Coordonnées Bancaires
    bank = _get_val(invoice_data, "bank_details", {})
    if bank:
        bank_text = f"<b>{t['bank_name']}</b> {_get_val(bank, 'bank_name', 'N/A')} | "
        bank_text += f"<b>{t['rib']}</b> {_get_val(bank, 'rib', 'N/A')}<br/>"
        if _get_val(bank, 'iban'):
            bank_text += f"<b>{t['iban']}</b> {_get_val(bank, 'iban')} | "
        if _get_val(bank, 'swift'):
            bank_text += f"<b>{t['swift']}</b> {_get_val(bank, 'swift')}"

        bank_table = Table([
            [Paragraph(f"<b>{t['bank_title']}</b>", section_style)],
            [Paragraph(bank_text, body_style)]
        ], colWidths=[520])

        bank_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EFF6FF')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFDBFE'))
        ]))
        story.append(bank_table)

    # Generation du flux PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
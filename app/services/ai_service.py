from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from app.models.invoice import InvoiceORM


def process_ai_query(
    prompt: str,
    db: Session,
    tenant_id: str,
    language: str = "fr"
) -> Dict[str, Any]:
    """
    Analyse contextuelle RAG : Extrait les métriques réelles de la BDD pour le tenant
    et génère une réponse analytique adaptée avec des recommandations.
    """
    # 1. Extraction des données contextuelles du Tenant depuis la BDD
    total_invoices = db.query(InvoiceORM).filter(InvoiceORM.tenant_id == tenant_id).count()
    
    # Total du chiffre d'affaires HT et TTC
    totals = db.query(
        func.coalesce(func.sum(InvoiceORM.total_ht), 0.0).label("sum_ht"),
        func.coalesce(func.sum(InvoiceORM.total_ttc), 0.0).label("sum_ttc")
    ).filter(InvoiceORM.tenant_id == tenant_id).first()

    sum_ht = float(totals.sum_ht) if totals else 0.0
    sum_ttc = float(totals.sum_ttc) if totals else 0.0
    avg_invoice = (sum_ttc / total_invoices) if total_invoices > 0 else 0.0

    # 2. Construction de la synthèse des métriques
    metrics = {
        "tenant_id": tenant_id,
        "total_invoices": total_invoices,
        "total_revenue_ht": round(sum_ht, 2),
        "total_revenue_ttc": round(sum_ttc, 2),
        "average_invoice_value": round(avg_invoice, 2),
        "currency": "FCFA"
    }

    # 3. Logique d'analyse de l'IA selon la langue retenue
    lang_code = language.lower() if language in ["fr", "en", "ar"] else "fr"

    if lang_code == "en":
        answer = (
            f"Based on your company's data ({tenant_id}), you have generated a total of "
            f"{total_invoices} invoice(s) for a overall turnover of {sum_ttc:,.2f} FCFA. "
            f"The average invoice amount is {avg_invoice:,.2f} FCFA."
        )
        actions = [
            "Export financial summary as PDF",
            "Review pending invoice payments",
            "Generate monthly performance graph"
        ]
    elif lang_code == "ar":
        answer = (
            f"بناءً على بيانات شركتك ({tenant_id})، قمتم بإصدار إجمالي "
            f"{total_invoices} فاتورة بـ رقم أعمال كلي قدره {sum_ttc:,.2f} فرنك أفريقي. "
            f"متوسط قيمة الفاتورة هو {avg_invoice:,.2f} فرنك أفريقي."
        )
        actions = [
            "تصدير الملخص المالي كـ PDF",
            "مراجعة الفواتير غير المدفوعة",
            "إنشاء الرسم البياني للأداء الشهر"
        ]
    else:  # Français par défaut
        answer = (
            f"En analysant les données de votre entreprise ({tenant_id}), vous avez émis un total de "
            f"{total_invoices} facture(s) pour un chiffre d'affaires global de {sum_ttc:,.2f} FCFA TTC. "
            f"Le panier moyen par facture s'élève à {avg_invoice:,.2f} FCFA."
        )
        actions = [
            "Exporter la synthèse financière au format PDF",
            "Relancer les factures en attente de règlement",
            "Analyser la répartition par catégorie de produits"
        ]

    return {
        "answer": answer,
        "metrics_summary": metrics,
        "suggested_actions": actions
    }
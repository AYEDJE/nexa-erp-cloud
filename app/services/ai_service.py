from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import AI_API_BASE_URL, AI_API_KEY, AI_MODEL, AI_PROVIDER, AI_TIMEOUT_SECONDS
from app.models.invoice import InvoiceORM


def _build_metrics(db: Session, tenant_id: str) -> Dict[str, Any]:
    total_invoices = db.query(InvoiceORM).filter(InvoiceORM.tenant_id == tenant_id).count()

    totals = db.query(
        func.coalesce(func.sum(InvoiceORM.total_ht), 0.0).label("sum_ht"),
        func.coalesce(func.sum(InvoiceORM.total_ttc), 0.0).label("sum_ttc")
    ).filter(InvoiceORM.tenant_id == tenant_id).first()

    sum_ht = float(totals.sum_ht) if totals else 0.0
    sum_ttc = float(totals.sum_ttc) if totals else 0.0
    avg_invoice = (sum_ttc / total_invoices) if total_invoices > 0 else 0.0

    return {
        "tenant_id": tenant_id,
        "total_invoices": total_invoices,
        "total_revenue_ht": round(sum_ht, 2),
        "total_revenue_ttc": round(sum_ttc, 2),
        "average_invoice_value": round(avg_invoice, 2),
        "currency": "FCFA",
    }


def _lang_code(language: Optional[str]) -> str:
    code = (language or "fr").lower()
    return code if code in {"fr", "en", "ar"} else "fr"


def _fallback_response(metrics: Dict[str, Any], language: Optional[str], prompt: str) -> Dict[str, Any]:
    lang_code = _lang_code(language)
    total_invoices = metrics.get("total_invoices", 0)
    sum_ttc = float(metrics.get("total_revenue_ttc", 0.0) or 0.0)
    avg_invoice = float(metrics.get("average_invoice_value", 0.0) or 0.0)
    tenant_id = metrics.get("tenant_id", "tenant")

    if lang_code == "en":
        answer = (
            f"Based on the current data for {tenant_id}, you issued {total_invoices} invoice(s) "
            f"with a total turnover of {sum_ttc:,.2f} FCFA and an average invoice value of {avg_invoice:,.2f} FCFA. "
            f"Your request was: '{prompt}'."
        )
        actions = [
            "Export the financial summary as PDF",
            "Review pending invoices",
            "Analyze sales by category",
        ]
    elif lang_code == "ar":
        answer = (
            f"استناداً إلى بيانات {tenant_id}، أصدرت {total_invoices} فاتورة بإجمالي مبيعات قدره {sum_ttc:,.2f} فرنك أفريقي "
            f"ومتوسط قيمة الفاتورة {avg_invoice:,.2f} فرنك أفريقي. طلبك كان: '{prompt}'."
        )
        actions = [
            "تصدير الملخص المالي بصيغة PDF",
            "مراجعة الفواتير المعلقة",
            "تحليل المبيعات حسب الفئة",
        ]
    else:
        answer = (
            f"En analysant les données actuelles de l'entreprise {tenant_id}, vous avez émis {total_invoices} facture(s) "
            f"pour un chiffre d'affaires total de {sum_ttc:,.2f} FCFA et un panier moyen de {avg_invoice:,.2f} FCFA. "
            f"Votre demande était : '{prompt}'."
        )
        actions = [
            "Exporter le résumé financier en PDF",
            "Relancer les factures en attente",
            "Analyser les ventes par catégorie",
        ]

    return {
        "answer": answer,
        "metrics_summary": metrics,
        "suggested_actions": actions,
    }


def _call_openai(prompt: str, language: Optional[str], metrics: Dict[str, Any]) -> Optional[str]:
    if AI_PROVIDER != "openai" or not AI_API_KEY:
        return None

    lang_code = _lang_code(language)
    system_prompt = (
        "Tu es un assistant financier expert pour un ERP SaaS B2B. "
        "Réponds de manière claire, utile et concise. "
        "Utilise uniquement les données de contexte fournies. "
        "Si les données sont absentes, dis-le explicitement."
    )

    user_prompt = (
        f"Langue de réponse attendue : {lang_code}\n\n"
        f"Demande utilisateur : {prompt}\n\n"
        f"Données financières du tenant : {json.dumps(metrics, ensure_ascii=False)}"
    )

    try:
        response = httpx.post(
            f"{AI_API_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=AI_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:
            return None

        payload = response.json()
        message = payload.get("choices", [{}])[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        return content.strip()
    except Exception:
        return None


def process_ai_query(
    prompt: str,
    db: Session,
    tenant_id: str,
    language: str = "fr",
) -> Dict[str, Any]:
    """
    Analyse contextuelle RAG : exécute d'abord les métriques réelles du tenant,
    puis appelle OpenAI si configuré, sinon rétablit un mode de secours robuste.
    """
    metrics = _build_metrics(db, tenant_id)

    ai_answer = _call_openai(prompt, language, metrics)
    if ai_answer:
        return {
            "answer": ai_answer,
            "metrics_summary": metrics,
            "suggested_actions": [
                "Exporter la synthèse financière",
                "Relancer les factures impayées",
                "Analyser les performances par catégorie",
            ],
        }

    return _fallback_response(metrics, language, prompt)
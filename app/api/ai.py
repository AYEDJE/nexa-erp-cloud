from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tenant import get_tenant_id
from app.schemas.ai import AIQueryRequest, AIQueryResponse
from app.services.ai_service import process_ai_query

router = APIRouter(prefix="/ai", tags=["Assistant IA & Analytics"])


@router.post("/query", response_model=AIQueryResponse, status_code=status.HTTP_200_OK)
def query_ai_assistant(
    request: AIQueryRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id)
):
    """
    Interroge l'assistant IA contextuel (RAG).
    L'analyse financière et les métriques sont calculées en temps réel
    et isolées exclusivement pour le tenant connecté via l'en-tête X-Tenant-ID.
    """
    result = process_ai_query(
        prompt=request.prompt,
        db=db,
        tenant_id=tenant_id,
        language=request.language or "fr"
    )

    return AIQueryResponse(
        answer=result["answer"],
        metrics_summary=result["metrics_summary"],
        suggested_actions=result["suggested_actions"]
    )
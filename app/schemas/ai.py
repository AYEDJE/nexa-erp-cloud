
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AIChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class AIQueryRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question adressée à l'assistant IA"
    )

    language: Optional[str] = Field(
        default="fr",
        description="Langue : fr, en ou ar"
    )

    history: List[AIChatMessage] = Field(
        default_factory=list,
        max_length=12,
        description="Historique des échanges précédents"
    )


class AIQueryResponse(BaseModel):
    answer: str

    metrics_summary: Dict[str, Any] = Field(
        default_factory=dict
    )

    suggested_actions: List[str] = Field(
        default_factory=list
    )

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class AIQueryRequest(BaseModel):
    prompt: str = Field(..., description="La question ou la requête adressée à l'assistant IA", example="Analyse le chiffre d'affaires total de ce mois.")
    language: Optional[str] = Field("fr", description="Langue de réponse souhaitée ('fr', 'en', 'ar')", example="fr")


class AIQueryResponse(BaseModel):
    answer: str = Field(..., description="La réponse textuelle générée par l'IA")
    metrics_summary: Dict[str, Any] = Field(default_factory=dict, description="Métriques synthétiques calculées à partir de la BDD du tenant")
    suggested_actions: List[str] = Field(default_factory=list, description="Actions ou recommandations suggérées")
# app/services/hf_service.py
"""Hugging Face inference helper for Nexa ERP.

The backend can switch between OpenAI/Gemini and Hugging Face via the
environment variable ``AI_PROVIDER``. When ``AI_PROVIDER`` is set to
``huggingface`` the code in ``ai_service.py`` imports ``infer_hf`` from this
module and calls it directly.

We use the ``transformers`` ``pipeline`` API with the ``text-generation``
task (DeepSeek‑V4.1‑Flash is a decoder‑only model). The pipeline is cached
as a singleton so the model is loaded only once per process.
"""
import logging
from typing import Any, Optional

import os
import torch
from fastapi import HTTPException
from transformers import pipeline, Pipeline

from app.core.config import HF_MODEL, HF_TOKEN, HF_DEVICE

logger = logging.getLogger(__name__)

def _create_pipeline() -> Pipeline:
    """Initialise le pipeline Hugging Face.

    * ``HF_MODEL``  – nom du modèle HF (ex. ``deepseek-ai/DeepSeek-V4.1-Flash``).
    * ``HF_TOKEN``  – token d’accès privé (facultatif, utilisé si le repo
      est privé).
    * ``HF_DEVICE`` – ``cpu`` ou ``cuda`` ; on vérifie la disponibilité du
      GPU avant de choisir le device.
    """
    try:
        auth = HF_TOKEN if HF_TOKEN else None
        device = 0 if HF_DEVICE == "cuda" and torch.cuda.is_available() else -1
        # ``text-generation`` convient à DeepSeek‑Flash.
        return pipeline(
            "text-generation",
            model=HF_MODEL,
            token=auth,
            device=device,
            temperature=0.7,
            max_new_tokens=256,
        )
    except Exception as exc:
        logger.error("Impossible d'initialiser le pipeline Hugging Face : %s", exc)
        raise HTTPException(status_code=503,
                            detail="Erreur d'initialisation du modèle Hugging Face") from exc

# Cache global – lazily créé
_hf_pipeline: Optional[Pipeline] = None

def get_hf_pipeline() -> Pipeline:
    """Retourne le pipeline singleton, le crée s’il n’existe pas encore."""
    global _hf_pipeline
    if _hf_pipeline is None:
        _hf_pipeline = _create_pipeline()
    return _hf_pipeline

def infer_hf(prompt: str, **kwargs: Any) -> str:
    """Génère du texte à partir du *prompt* avec le modèle Hugging Face.

    ``kwargs`` permet de sur‑charger les paramètres du pipeline (par ex.
    ``temperature`` ou ``max_new_tokens``) sans modifier le pipeline global.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise HTTPException(status_code=400, detail="Le prompt ne peut pas être vide.")

    pipeline_obj = get_hf_pipeline()
    try:
        result = pipeline_obj(prompt, **kwargs)
        # ``pipeline`` renvoie une liste de dicts, on récupère le texte généré.
        generated = result[0].get("generated_text") if isinstance(result, list) else None
        if isinstance(generated, str) and generated.strip():
            return generated.strip()
        raise HTTPException(status_code=502,
                            detail="Le modèle Hugging Face n'a retourné aucun texte.")
    except Exception as exc:
        logger.error("Erreur d'inférence Hugging Face : %s", exc)
        raise HTTPException(status_code=500,
                            detail="Erreur d'inférence avec Hugging Face") from exc
"""
Integração com a API do Banco Central do Brasil.

Busca a Selic Meta em tempo real. Fallback em caso de indisponibilidade
para não derrubar o app durante a apresentação.
"""

from typing import Optional

import requests
import streamlit as st

from config.settings import (
    API_TIMEOUT_SECONDS,
    BCB_SELIC_URL,
    CACHE_TTL_SELIC,
    SELIC_FALLBACK,
)
from services.logger import get_logger

logger = get_logger(__name__)


@st.cache_data(ttl=CACHE_TTL_SELIC, show_spinner=False)
def buscar_selic() -> float:
    """Busca a taxa Selic Meta mais recente na API do Banco Central.

    Returns:
        Taxa Selic em formato decimal (ex: 0.1375 = 13.75% a.a.).
        Em caso de falha, retorna SELIC_FALLBACK sem quebrar o app.
    """
    try:
        resposta = requests.get(BCB_SELIC_URL, timeout=API_TIMEOUT_SECONDS)
        resposta.raise_for_status()
        payload = resposta.json()

        if not payload:
            logger.warning("API BCB retornou payload vazio — usando fallback")
            return SELIC_FALLBACK

        valor = float(payload[0]["valor"]) / 100
        logger.info("Selic atualizada via API BCB: %.4f", valor)
        return valor

    except requests.RequestException as exc:
        logger.warning("Falha ao consultar API BCB (%s) — usando fallback %.4f",
                       exc, SELIC_FALLBACK)
        return SELIC_FALLBACK

    except (ValueError, KeyError, IndexError) as exc:
        logger.warning("Formato inesperado da API BCB (%s) — usando fallback",
                       exc)
        return SELIC_FALLBACK


def selic_origem_str(selic: float) -> Optional[str]:
    """Retorna rótulo indicando se a Selic veio da API ou do fallback."""
    if abs(selic - SELIC_FALLBACK) < 1e-9:
        return "fallback"
    return "BCB (ao vivo)"

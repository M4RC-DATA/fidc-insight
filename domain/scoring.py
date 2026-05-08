"""
Motor de classificação de score → rating.

Lógica pura de negócio sem dependência de Streamlit ou BigQuery.
Totalmente testável de forma unitária.
"""

from dataclasses import dataclass
from typing import Iterable

from config.business_rules import CLASSIFICACOES


@dataclass(frozen=True)
class Classificacao:
    """Resultado da classificação de um score.

    Attributes:
        rating: Nota de crédito (A+, A, B, C, D).
        premio_anual: Spread de risco cobrado sobre a Selic (ex: 0.15 = 15% a.a.).
        pd_anual: Probabilidade de Default anual (ex: 0.005 = 0.5%).
    """
    rating: str
    premio_anual: float
    pd_anual: float


def classificar_score(score: float) -> Classificacao:
    """Converte um score numérico em rating + parâmetros de precificação.

    Args:
        score: Pontuação na escala 0-1000.

    Returns:
        Classificação com rating, prêmio e PD correspondentes.
        Scores fora da escala caem em rating D (mais conservador).
    """
    for vmin, vmax, rating, premio, pd_rate in CLASSIFICACOES:
        if vmin <= score <= vmax:
            return Classificacao(rating=rating, premio_anual=premio, pd_anual=pd_rate)

    # Fallback defensivo: score inválido → tratar como pior rating
    return Classificacao(rating="D", premio_anual=0.32, pd_anual=0.120)


def distribuir_componentes(
    peso_qualidade: float,
    peso_liquidez: float,
    peso_inadimplencia: float,
    peso_regional: float,
    v_qualidade: float,
    v_liquidez: float,
    v_inadimplencia: float,
    v_regional: float,
) -> dict:
    """Calcula a contribuição em pontos de cada componente do score.

    Útil para explicar na UI "quanto cada dimensão contribuiu".

    Returns:
        Dict com 'qualidade', 'liquidez', 'inadimplencia', 'regional' em pontos
        na escala 0-1000 (soma aproximada = score final).
    """
    return {
        "qualidade": v_qualidade * peso_qualidade * 1000,
        "liquidez": v_liquidez * peso_liquidez * 1000,
        "inadimplencia": v_inadimplencia * peso_inadimplencia * 1000,
        "regional": v_regional * peso_regional * 1000,
    }


def percentil_na_carteira(score_alvo: float, scores_carteira: Iterable[float]) -> float:
    """Calcula em que percentil da carteira um score se encontra.

    Returns:
        Valor entre 0 e 100. Ex: 75.0 significa melhor que 75% da carteira.
    """
    scores = list(scores_carteira)
    if not scores:
        return 0.0
    melhores_que = sum(1 for s in scores if s < score_alvo)
    return round((melhores_que / len(scores)) * 100, 1)

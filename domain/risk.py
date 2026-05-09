"""
Motor de risco: enquadramento parametrizável + early warning system.

Calcula:
- Limites de concentração por sacado e por UF (regras parametrizáveis,
  conforme política/regulamento do fundo)
- Probabilidade de contágio (rede de inadimplência) — EWS
- Classificação de zona de risco (verde/amarelo/vermelho)

Os limites são parametrizados em ``config/business_rules.py`` e devem
refletir o regulamento de cada fundo. Não constituem aconselhamento
regulatório nem substituem a leitura formal das normas aplicáveis.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import pandas as pd

from config.business_rules import (
    EWS_DIVISOR_ATRASO_DIAS,
    EWS_LIMITE_BAIXO,
    EWS_LIMITE_MODERADO,
    EWS_PESO_ATRASO,
    EWS_PESO_INADIMPLENCIA,
    LIMITE_POR_SACADO,
    LIMITE_POR_UF,
    ZONA_ALERTA_UF,
)


class NivelRisco(str, Enum):
    BAIXO = "BAIXO"
    MODERADO = "MODERADO"
    ALTO = "ALTO"


StatusCompliance = Literal["aprovado", "alerta", "bloqueio"]


# =============================================================================
# Concentração (enquadramento parametrizável conforme política do fundo)
# =============================================================================
@dataclass(frozen=True)
class ResultadoConcentracao:
    status: StatusCompliance
    percentual_atual: float      # Percentual após adicionar a nova operação
    limite: float                # Limite parametrizado (política do fundo)
    mensagem: str                # Mensagem humanizada para exibir na UI


def avaliar_concentracao_sacado(
    df_carteira: pd.DataFrame,
    cnpj: str,
    valor_novo: float,
) -> ResultadoConcentracao:
    """Verifica se a nova operação viola o limite de concentração por sacado.

    O limite é parametrizado em ``config.business_rules.LIMITE_POR_SACADO`` e
    deve refletir o regulamento/política do fundo (ex.: 10% do PL).
    """
    exposicao_atual = df_carteira[df_carteira["id_cnpj"] == cnpj]["vlr_nominal_total"].sum()
    pl_projetado = df_carteira["vlr_nominal_total"].sum() + valor_novo
    percentual = ((exposicao_atual + valor_novo) / pl_projetado) if pl_projetado > 0 else 0

    if percentual <= LIMITE_POR_SACADO:
        return ResultadoConcentracao(
            status="aprovado",
            percentual_atual=percentual,
            limite=LIMITE_POR_SACADO,
            mensagem=f"Aprovado: {percentual*100:.1f}% (limite {LIMITE_POR_SACADO*100:.0f}%)",
        )
    return ResultadoConcentracao(
        status="bloqueio",
        percentual_atual=percentual,
        limite=LIMITE_POR_SACADO,
        mensagem=f"BLOQUEIO: Limite de sacado excedido — atingirá {percentual*100:.1f}%",
    )


def avaliar_concentracao_uf(
    df_carteira: pd.DataFrame,
    uf: str,
    valor_novo: float,
) -> ResultadoConcentracao:
    """Verifica o limite de concentração estadual.

    Zonas:
        aprovado : percentual ≤ LIMITE - ZONA_ALERTA   (margem confortável)
        alerta   : LIMITE - ZONA_ALERTA < percentual ≤ LIMITE  (aproximando)
        bloqueio : percentual > LIMITE  (limite excedido)
    """
    exposicao_uf = df_carteira[df_carteira["uf"] == uf]["vlr_nominal_total"].sum()
    pl_projetado = df_carteira["vlr_nominal_total"].sum() + valor_novo
    percentual = ((exposicao_uf + valor_novo) / pl_projetado) if pl_projetado > 0 else 0

    if percentual > LIMITE_POR_UF:
        return ResultadoConcentracao(
            status="bloqueio",
            percentual_atual=percentual,
            limite=LIMITE_POR_UF,
            mensagem=f"BLOQUEIO: Limite estadual de {uf} excedido — {percentual*100:.1f}%",
        )
    if percentual > LIMITE_POR_UF - ZONA_ALERTA_UF:
        return ResultadoConcentracao(
            status="alerta",
            percentual_atual=percentual,
            limite=LIMITE_POR_UF,
            mensagem=f"Atenção: {uf} próxima ao limite — {percentual*100:.1f}% (limite {LIMITE_POR_UF*100:.0f}%)",
        )
    return ResultadoConcentracao(
        status="aprovado",
        percentual_atual=percentual,
        limite=LIMITE_POR_UF,
        mensagem=f"Aprovado: {uf} em {percentual*100:.1f}% (limite {LIMITE_POR_UF*100:.0f}%)",
    )


# =============================================================================
# Early Warning System (contágio)
# =============================================================================
def calcular_probabilidade_contagio(
    media_atraso_dias: float,
    share_inadimplencia: float,
) -> float:
    """Estima a probabilidade de contágio de inadimplência na rede do sacado.

    Fórmula (heurística Núclea):
        P = min( (atraso/15) × 0.4 + inad_share × 0.6 , 1.0 )

    Valores mais altos indicam que um default desse sacado tem maior
    chance de impactar sacados conectados (relações comerciais recorrentes).
    """
    componente_atraso = (media_atraso_dias / EWS_DIVISOR_ATRASO_DIAS) * EWS_PESO_ATRASO
    componente_inad = share_inadimplencia * EWS_PESO_INADIMPLENCIA
    return min(componente_atraso + componente_inad, 1.0)


def classificar_nivel_contagio(probabilidade: float) -> NivelRisco:
    """Classifica o nível de risco de contágio em três faixas."""
    if probabilidade < EWS_LIMITE_BAIXO:
        return NivelRisco.BAIXO
    if probabilidade < EWS_LIMITE_MODERADO:
        return NivelRisco.MODERADO
    return NivelRisco.ALTO


# =============================================================================
# Índice Herfindahl-Hirschman (concentração da carteira)
# =============================================================================
def hhi_por_uf(df_carteira: pd.DataFrame, coluna_valor: str = "vlr_nominal_total") -> float:
    """Calcula o HHI de concentração por UF da carteira.

    HHI = Σ (participação_i)²
    Interpretação:
      < 0.15: baixa concentração
      0.15-0.25: concentração moderada
      > 0.25: alta concentração

    Args:
        df_carteira: DataFrame com dados da carteira.
        coluna_valor: Nome da coluna de volume (padrão: vlr_nominal_total).
    """
    if coluna_valor not in df_carteira.columns:
        return 0.0
    total = df_carteira[coluna_valor].sum()
    if total <= 0:
        return 0.0
    shares = df_carteira.groupby("uf")[coluna_valor].sum() / total
    return round((shares ** 2).sum(), 4)
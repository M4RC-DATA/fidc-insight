"""
Regras de negócio do motor de crédito FIDC.

Contém todos os parâmetros financeiros parametrizáveis do fundo:
- Pesos das dimensões do score
- Fator regional de risco por UF
- Tabela de classificação de rating → taxa → PD
- Limites internos de concentração (parametrizáveis conforme política/regulamento)
- Parâmetros de Loss Given Default

Todos os valores aqui são premissas internas, parametrizáveis e auditáveis.
Devem ser revisados periodicamente pelo comitê de risco do fundo e ajustados
ao regulamento vigente. Qualquer alteração impacta diretamente o parecer.
"""

from typing import Dict, List, Tuple

# =============================================================================
# Pesos das dimensões do score (soma deve ser 1.0)
# =============================================================================
PESOS: Dict[str, float] = {
    "qualidade": 0.35,       # Score Núclea quantidade + materialidade
    "liquidez": 0.25,        # Índice de liquidez 1m e 3m
    "inadimplencia": 0.30,   # Atraso médio + share inadimplência
    "regional": 0.10,        # Fator regional da UF do sacado
}

# =============================================================================
# Fator regional de risco
# Valores > 1.0 indicam UF com maior risco de crédito histórico.
# Base: análise de inadimplência por UF (Dataverse/Núclea, 2024).
# =============================================================================
FATOR_REGIONAL: Dict[str, float] = {
    "RO": 1.30, "PR": 1.25, "MT": 1.22, "RS": 1.20, "SC": 1.20,
    "SP": 1.15, "DF": 1.15, "PI": 1.12, "SE": 1.10, "GO": 1.10,
    "BA": 1.10, "PE": 1.08, "CE": 1.08, "RN": 1.08, "MA": 1.12,
    "PA": 1.15, "AM": 1.18, "AL": 1.10, "PB": 1.10, "ES": 1.05,
    "MG": 1.05, "RJ": 1.08, "MS": 1.08, "TO": 1.12, "AP": 1.20,
    "RR": 1.22, "AC": 1.20,
}
FATOR_REGIONAL_DEFAULT: float = 1.10

# =============================================================================
# Classificação de rating
# Tuplas: (score_min, score_max, rating, prêmio_anual, PD_anual)
#   - prêmio_anual: spread de risco cobrado sobre a Selic
#   - PD_anual: Probabilidade de Default em 12 meses
# =============================================================================
CLASSIFICACOES: List[Tuple[int, int, str, float, float]] = [
    (900, 1000, "A+", 0.15, 0.005),
    (800,  899, "A",  0.17, 0.015),
    (700,  799, "B",  0.20, 0.030),
    (600,  699, "C",  0.25, 0.060),
    (  0,  599, "D",  0.32, 0.120),
]

# Ordem canônica de ratings (melhor → pior)
ORDEM_RATINGS: List[str] = ["A+", "A", "B", "C", "D"]

# Cores do rating (paleta corporativa premium)
CORES_RATING: Dict[str, str] = {
    "A+": "#16A34A",  # verde forte
    "A":  "#65A30D",  # verde oliva
    "B":  "#CA8A04",  # dourado
    "C":  "#EA580C",  # laranja
    "D":  "#DC2626",  # vermelho
}

# =============================================================================
# Limites internos parametrizáveis de concentração
# (devem refletir o regulamento e a política interna do fundo)
# =============================================================================
LIMITE_POR_SACADO: float = 0.10   # Máx 10% do PL por sacado (parametrizável)
LIMITE_POR_UF: float = 0.25       # Máx 25% do PL por estado (parametrizável)
ZONA_ALERTA_UF: float = 0.05      # Margem de alerta antes do limite

# =============================================================================
# Parâmetros de Perda Esperada (ECL / IFRS 9)
# =============================================================================
LGD_PADRAO: float = 0.50  # Loss Given Default: 50% (benchmark FIDCs brasileiros)

# =============================================================================
# Parâmetros de normalização do componente de atraso no score
# =============================================================================
# Teto absoluto de atraso para a normalização do componente v_atraso_inv.
# Acima desse valor o componente satura em 0 (pior possível).
# Uso de teto fixo evita instabilidade cross-run: se o pior sacado hoje tem
# 30 dias e amanhã entra um com 90, o score de todos os outros não deve mudar.
ATRASO_CAP_DIAS: float = 247.0
# Teto para normalização do componente de atraso no score.
# Calibrado nos dados reais da base_auxiliar_fiap (4.612 sacados):
#   mediana = 178 dias, p90 = 247 dias, max = 365 dias.
# Cap de 60 dias (anterior) zeraria 91% da carteira no componente —
# tornando a dimensão de inadimplência inútil como discriminador.
# Com p90: os 10% piores pagadores recebem score 0; os demais são
# diferenciados proporcionalmente. Revisar se a base de produção
# apresentar distribuição diferente.

# Divisor para conversão de prazo (dias → anos). Mercado de crédito BR usa 365.
PRAZO_DIVISOR_ANOS: float = 365.0

# =============================================================================
# Parâmetros do modelo de contágio (Early Warning System)
# =============================================================================
EWS_PESO_ATRASO: float = 0.4
EWS_PESO_INADIMPLENCIA: float = 0.6
EWS_DIVISOR_ATRASO_DIAS: float = 15.0  # Normaliza atraso para escala 0-1

EWS_LIMITE_BAIXO: float = 0.3
EWS_LIMITE_MODERADO: float = 0.6

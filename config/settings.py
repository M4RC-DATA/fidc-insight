"""
Configurações técnicas do projeto (BigQuery, APIs externas).

Centraliza todas as constantes de infraestrutura em um único ponto.
Permite fácil customização por ambiente via variáveis de ambiente.
"""

import os
from pathlib import Path

# =============================================================================
# Paths do projeto
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

# =============================================================================
# BigQuery
# =============================================================================
BQ_PROJECT_ID = os.getenv("BQ_PROJECT_ID", "dataversenuclea")
BQ_DATASET = os.getenv("BQ_DATASET", "fidc_dataset")
BQ_TABLE_CARTEIRA = os.getenv("BQ_TABLE_CARTEIRA", "tb_score_consolidado")
BQ_TABLE_HISTORICO = os.getenv("BQ_TABLE_HISTORICO", "tb_historico_precificacoes")

# TTL (time-to-live) do cache em segundos
CACHE_TTL_CARTEIRA = int(os.getenv("CACHE_TTL_CARTEIRA", "1800"))  # 30 min
CACHE_TTL_SELIC = int(os.getenv("CACHE_TTL_SELIC", "3600"))        # 1 hora

# =============================================================================
# APIs externas
# =============================================================================
BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
SELIC_FALLBACK = 0.1375  # Taxa Selic padrão se API BCB estiver indisponível
API_TIMEOUT_SECONDS = 10

# =============================================================================
# Interface
# =============================================================================
APP_TITLE = "FIDC Insight"
APP_SUBTITLE = "Data Verse · Grupo de Data Science — FIAP"
APP_ICON = "🏦"
DEFAULT_PAGE = "macro"  # macro | individual | filtros

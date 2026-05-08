"""
Camada de acesso ao BigQuery.

Todas as queries usam parâmetros nomeados (@cnpj, @data, ...) via
pandas_gbq para eliminar risco de SQL injection. O código original
interpolava CNPJ direto na string da query — vulnerabilidade crítica.

Fornece também uma função de enriquecimento de features para o dataset
base, separando claramente leitura (DB) de transformação.
"""

import hashlib
from typing import Optional

import numpy as np
import pandas as pd
import json
import pandas_gbq
try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False
import streamlit as st

from config.business_rules import (
    ATRASO_CAP_DIAS,
    FATOR_REGIONAL,
    FATOR_REGIONAL_DEFAULT,
    PESOS,
)
from config.settings import (
    BQ_DATASET,
    BQ_PROJECT_ID,
    BQ_TABLE_CARTEIRA,
    BQ_TABLE_HISTORICO,
    CACHE_TTL_CARTEIRA,
)
from domain.scoring import classificar_score
from services.cnae import enriquecer_dataframe as enriquecer_cnae
from services.logger import get_logger

logger = get_logger(__name__)

# =============================================================================
# Colunas numéricas que precisam de coerção para evitar erros tipados
# =============================================================================
COLUNAS_NUMERICAS = [
    "sacado_indice_liquidez_1m",
    "score_quantidade_v2",
    "score_materialidade_v2",
    "media_atraso_dias",
    "indicador_liquidez_quantitativo_3m",
    "share_vl_inad_pag_bol_6_a_15d",
]


# =============================================================================
# Leitura da carteira consolidada
# =============================================================================
@st.cache_data(ttl=CACHE_TTL_CARTEIRA, show_spinner=False)
def _get_credentials():
    """Retorna credenciais GCP.

    - Streamlit Cloud: lê de st.secrets["gcp_service_account"]
    - Local: usa Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS)
    """
    if _HAS_STREAMLIT:
        try:
            from google.oauth2 import service_account
            info = dict(st.secrets["gcp_service_account"])
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/bigquery"],
            )
        except (KeyError, Exception):
            pass  # sem secrets → tenta credenciais locais
    return None  # pandas_gbq usa Application Default Credentials


def carregar_carteira() -> Optional[pd.DataFrame]:
    """Lê a tabela consolidada de score e enriquece com features derivadas.

    Suporta dois modos:
    - Streamlit Cloud: credenciais via st.secrets["gcp_service_account"]
    - Local: GOOGLE_APPLICATION_CREDENTIALS no ambiente

    Returns:
        DataFrame com colunas originais + colunas calculadas (score, rating,
        componentes). Retorna None se a query falhar (erro fica no log).
    """
    query = f"""
        SELECT *
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_CARTEIRA}`
    """
    try:
        credentials = _get_credentials()
        df = pandas_gbq.read_gbq(
            query,
            project_id=BQ_PROJECT_ID,
            credentials=credentials,
            progress_bar_type=None,
        )
        logger.info("Carteira carregada: %d sacados", len(df))
    except Exception as exc:
        logger.error("Falha ao carregar carteira: %s", exc, exc_info=True)
        return None

    df = _coerge_numericas(df)
    df = _enriquecer_com_score(df)
    df = _garantir_vlr_nominal(df)
    df = _enriquecer_com_segmento(df)

    return df


def _enriquecer_com_segmento(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas de segmento econômico a partir do CNAE.

    Tenta encontrar a coluna CNAE na carteira (nomes mais comuns e padrão
    da tabela ``tb_score_consolidado`` — ``cd_cnae_prin``). Se nenhuma
    coluna for achada, registra um warning com a lista de colunas
    disponíveis para facilitar o diagnóstico e retorna o DataFrame sem
    alteração. Usa a API do IBGE com cache em disco e fallback offline.
    """
    # Ordem importa: nomes mais específicos primeiro, mais genéricos depois.
    candidatos = [
        "cd_cnae_prin",      # padrão da tb_score_consolidado (Núclea)
        "cd_cnae_princ",
        "cnae_principal",
        "cnae_fiscal",
        "cnae_sacado",
        "codigo_cnae",
        "cd_cnae",
        "cnae",
    ]
    coluna = next((c for c in candidatos if c in df.columns), None)

    # Fallback heurístico: procura qualquer coluna cujo nome contenha "cnae"
    if coluna is None:
        heuristicas = [c for c in df.columns if "cnae" in c.lower()]
        if heuristicas:
            coluna = heuristicas[0]
            logger.info(
                "CNAE detectado por heurística: coluna '%s' (candidatos padrão "
                "não encontrados, usando a primeira com 'cnae' no nome).",
                coluna,
            )

    if coluna is None:
        # Diagnóstico explícito — lista amostra de colunas da carteira
        amostra_cols = list(df.columns)[:30]
        logger.warning(
            "Nenhuma coluna CNAE encontrada na carteira — segmento não "
            "enriquecido. Colunas disponíveis (amostra de até 30): %s",
            amostra_cols,
        )
        return df

    logger.info("Enriquecendo segmentos a partir da coluna CNAE '%s'.", coluna)
    try:
        df = enriquecer_cnae(df, coluna_cnae=coluna, prefixo="cnae_")
        if "cnae_segmento" in df.columns:
            total = int(df["cnae_segmento"].notna().sum())
            segs = df["cnae_segmento"].value_counts().to_dict()
            logger.info(
                "Segmentos classificados: %d/%d sacados · distribuição: %s",
                total, len(df), segs,
            )
    except Exception as exc:
        logger.warning("Falha ao enriquecer segmentos CNAE: %s", exc)
    return df


def _coerge_numericas(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas para numéricas e preenche NaN com a moda da UF.

    Usar a moda da UF em vez da mediana global preserva padrões regionais:
    sacados do Norte têm padrões de atraso e liquidez diferentes dos do Sul.
    Imputar com a mediana nacional distorce o score de sacados em UFs extremas.
    Fallback: mediana global quando a UF não tem observações suficientes.
    """
    for col in COLUNAS_NUMERICAS:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if "uf" in df.columns and df[col].isna().any():
            # Moda por UF: para cada UF, usa o valor mais frequente daquela UF
            moda_uf = (
                df.groupby("uf")[col]
                .transform(lambda s: s.mode().iloc[0] if s.notna().any() else float("nan"))
            )
            # Fallback: mediana global para UFs sem nenhum dado válido
            mediana_global = df[col].median()
            df[col] = df[col].fillna(moda_uf).fillna(mediana_global)
        else:
            df[col] = df[col].fillna(df[col].median())
    return df


def _enriquecer_com_score(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula as quatro dimensões do score e o rating resultante.

    O componente de atraso usa um teto absoluto (ATRASO_CAP_DIAS) em vez do
    máximo relativo do lote. Isso garante que o score de um sacado não mude
    entre execuções do ETL simplesmente porque outro sacado piorou — problema
    de normalização relativa que distorce comparações históricas.
    """
    # ── Componente 1 · Qualidade creditícia ─────────────────────────────
    # score_quantidade_v2 e score_materialidade_v2 estão em escala 0-1000
    df["v_qualidade"] = (
        (df["score_quantidade_v2"] / 1000) * 0.5
        + (df["score_materialidade_v2"] / 1000) * 0.5
    ).clip(0.0, 1.0)

    # ── Componente 2 · Liquidez ─────────────────────────────────────────
    # sacado_indice_liquidez_1m e indicador_liquidez_quantitativo_3m devem
    # estar em escala 0-1. Se a tabela do BQ trouxer valores > 1 (sacados
    # muito líquidos), o clip garante que não inflam o score além do limite.
    df["v_liquidez"] = (
        df["sacado_indice_liquidez_1m"] * 0.6
        + df["indicador_liquidez_quantitativo_3m"] * 0.4
    ).clip(0.0, 1.0)

    # ── Componente 3 · Inadimplência (invertida) ────────────────────────
    # Normalização com teto fixo: 0 dias → 1.0 (melhor); ≥ ATRASO_CAP_DIAS → 0.0 (pior)
    df["v_atraso_inv"] = (1 - df["media_atraso_dias"] / ATRASO_CAP_DIAS).clip(0.0, 1.0)
    # share_vl_inad deve ser 0-1; clip defensivo contra erros de dado
    df["v_inad_inv"] = (1 - df["share_vl_inad_pag_bol_6_a_15d"]).clip(0.0, 1.0)
    df["v_inadimplencia"] = (df["v_atraso_inv"] * 0.6 + df["v_inad_inv"] * 0.4).clip(0.0, 1.0)

    # ── Componente 4 · Regional ─────────────────────────────────────────
    # Bounds FIXOS derivados do dicionário FATOR_REGIONAL completo — não do
    # lote atual. Sem isso, se RO não tiver sacados num dia, fi_min muda e
    # todos os scores regionais se deslocam entre execuções.
    todos_fatores = list(FATOR_REGIONAL.values()) + [FATOR_REGIONAL_DEFAULT]
    fi_min_fixo = 1.0 / max(todos_fatores)   # UF de maior risco → menor fator_inv
    fi_max_fixo = 1.0 / min(todos_fatores)   # UF de menor risco → maior fator_inv
    fator_inv = 1.0 / df["uf"].map(FATOR_REGIONAL).fillna(FATOR_REGIONAL_DEFAULT)
    df["v_regional"] = (
        (fator_inv - fi_min_fixo) / (fi_max_fixo - fi_min_fixo + 1e-9)
    ).clip(0.0, 1.0)

    df["score_calculado"] = (
        df["v_qualidade"] * PESOS["qualidade"]
        + df["v_liquidez"] * PESOS["liquidez"]
        + df["v_inadimplencia"] * PESOS["inadimplencia"]
        + df["v_regional"] * PESOS["regional"]
    ) * 1000
    df["score_calculado"] = df["score_calculado"].clip(0, 1000).round(2)

    df["rating_calculado"] = df["score_calculado"].apply(
        lambda s: classificar_score(s).rating
    )
    return df


def _garantir_vlr_nominal(df: pd.DataFrame) -> pd.DataFrame:
    """Se a tabela não trouxer vlr_nominal_total, simula valores plausíveis.

    Usa seed fixa para reprodutibilidade nas demonstrações. Marca flag
    `_vlr_simulado` para rastreabilidade (e para poder avisar na UI).
    """
    if "vlr_nominal_total" not in df.columns:
        logger.warning(
            "Coluna vlr_nominal_total ausente — simulando volumes para demonstração"
        )
        rng = np.random.default_rng(seed=42)
        df["vlr_nominal_total"] = rng.uniform(50_000, 500_000, size=len(df))
        df.attrs["vlr_simulado"] = True
    else:
        df.attrs["vlr_simulado"] = False
    return df


# =============================================================================
# Histórico de precificações
# =============================================================================
@st.cache_data(ttl=CACHE_TTL_CARTEIRA, show_spinner=False)
def buscar_historico(cnpj: str) -> pd.DataFrame:
    """Busca o histórico de precificações de um CNPJ específico.

    Usa QUERY PARAMETRIZADA (@cnpj) para prevenir SQL injection.

    Args:
        cnpj: ID do sacado a ser consultado.

    Returns:
        DataFrame com histórico ordenado por data. Vazio se não houver
        registros ou em caso de erro.
    """
    query = f"""
        SELECT data_consulta, score_fidc, classificacao_risco, vp_sugerido
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_HISTORICO}`
        WHERE id_cnpj = @cnpj
        ORDER BY data_consulta ASC
    """
    config = {
        "query": {
            "parameterMode": "NAMED",
            "queryParameters": [
                {
                    "name": "cnpj",
                    "parameterType": {"type": "STRING"},
                    "parameterValue": {"value": cnpj},
                }
            ],
        }
    }
    try:
        df = pandas_gbq.read_gbq(
            query,
            project_id=BQ_PROJECT_ID,
            configuration=config,
            progress_bar_type=None,
        )
        logger.info("Histórico para %s: %d registros", cnpj, len(df))
        return df
    except Exception as exc:
        logger.warning("Não foi possível carregar histórico de %s: %s", cnpj, exc)
        return pd.DataFrame(
            columns=["data_consulta", "score_fidc", "classificacao_risco", "vp_sugerido"]
        )


def buscar_historico_transacional(
    cnpj: str,
    row_sacado: Optional[pd.Series] = None,
    max_boletos: int = 40,
) -> pd.DataFrame:
    """Histórico transacional (boleto a boleto) de um sacado.

    Em produção esta função consultaria uma tabela de fato de boletos
    (`dataversenuclea.bronze.boletos`). Como a base agregada do projeto
    traz apenas estatísticas consolidadas por sacado, aqui sintetizamos
    um histórico *realista* usando os agregados disponíveis — valor médio,
    atraso médio, total de boletos, data do último boleto — e uma seed
    derivada do CNPJ para reprodutibilidade.

    O formato é o mesmo que ``domain.lastro.validar_lastro`` espera:
    colunas ``valor_nominal``, ``data_emissao``, ``prazo_du``, ``atraso_dias``.

    Args:
        cnpj: Identificador do sacado (usado para seed determinística).
        row_sacado: Linha do DataFrame de carteira com os agregados.
            Se None, retorna DataFrame vazio (primeira operação).
        max_boletos: Teto de boletos sintetizados (default 40).

    Returns:
        DataFrame com até N linhas ordenadas por data (mais antiga → recente).
    """
    if row_sacado is None:
        return pd.DataFrame(
            columns=["valor_nominal", "data_emissao", "prazo_du", "atraso_dias"]
        )

    r = row_sacado
    n_boletos = int(r.get("total_boletos", 0) or 0)
    if n_boletos <= 0:
        return pd.DataFrame(
            columns=["valor_nominal", "data_emissao", "prazo_du", "atraso_dias"]
        )

    n_sample = min(n_boletos, max_boletos)

    vlr_medio = float(r.get("vlr_nominal_medio") or r.get("vlr_nominal_total", 0) / max(n_boletos, 1))
    vlr_medio = max(vlr_medio, 1000.0)  # Piso defensivo
    atraso_medio = float(r.get("media_atraso_real_dias") or r.get("media_atraso_dias") or 0.0)
    ultimo_bol = r.get("ultimo_boleto", None)

    # Seed determinística a partir do CNPJ — mesmo sacado → mesmo histórico
    # MD5 é estável entre processos (ao contrário de hash() que usa
    # PYTHONHASHSEED randômico). Cripto não importa aqui — só queremos
    # uma função hash barata e reprodutível para seed.
    seed = int(hashlib.md5(str(cnpj).encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed=seed)

    # Sintetiza valores (lognormal ~ receita comercial real)
    sigma_log = 0.22
    valores = rng.lognormal(mean=np.log(vlr_medio), sigma=sigma_log, size=n_sample)

    # Datas: a última é o ultimo_boleto; as demais vão para trás com espaçamento
    # proporcional ao total_boletos (janela maior = frequência menor)
    try:
        dt_final = pd.to_datetime(ultimo_bol) if ultimo_bol else pd.Timestamp.today()
    except Exception:
        dt_final = pd.Timestamp.today()
    # Janela de ~meses razoavel — escala com total_boletos (assume ~2-3 boletos/mês)
    janela_dias = max(int(n_boletos / 2.0 * 30), 60)
    dias_atras = np.sort(rng.uniform(0, janela_dias, size=n_sample).astype(int))[::-1]
    datas = [dt_final - pd.Timedelta(days=int(d)) for d in dias_atras]

    # Prazos DU (30 base com pequena variação)
    prazos = rng.integers(low=28, high=33, size=n_sample)

    # Atrasos (exponencial ~ média histórica)
    atrasos = rng.exponential(scale=max(atraso_medio, 1.0), size=n_sample).round(1)

    return pd.DataFrame({
        "valor_nominal": np.round(valores, 2),
        "data_emissao": datas,
        "prazo_du": prazos,
        "atraso_dias": atrasos,
    }).sort_values("data_emissao").reset_index(drop=True)


def registrar_precificacao(
    cnpj: str,
    uf: str,
    score: float,
    rating: str,
    vp: float,
) -> bool:
    """Registra uma nova consulta no histórico para trilha de auditoria.

    Returns:
        True se gravou com sucesso, False caso contrário.
    """
    from datetime import datetime

    registro = pd.DataFrame(
        [
            {
                "data_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "id_cnpj": cnpj,
                "uf": uf,
                "score_fidc": score,
                "classificacao_risco": rating,
                "vp_sugerido": vp,
            }
        ]
    )
    try:
        pandas_gbq.to_gbq(
            registro,
            destination_table=f"{BQ_DATASET}.{BQ_TABLE_HISTORICO}",
            project_id=BQ_PROJECT_ID,
            if_exists="append",
            progress_bar=False,
        )
        logger.info("Precificação registrada para %s: score=%.1f rating=%s",
                    cnpj, score, rating)
        return True
    except Exception as exc:
        logger.error("Falha ao registrar precificação de %s: %s", cnpj, exc)
        return False


def buscar_sacados_por_cnpjs(
    df_carteira: pd.DataFrame,
    cnpjs: list[str],
) -> tuple[pd.DataFrame, list[str]]:
    """Faz matching de uma lista de identificadores contra a base Nuclea em memória.

    Os identificadores na base Nuclea são hashes SHA-256 de 64 caracteres —
    não CNPJs brutos. A normalização remove apenas espaços e converte para
    minúsculas, preservando o hash intacto.

    Para compatibilidade com bases que ainda usem CNPJs brutos (14 dígitos),
    detecta automaticamente o formato e aplica a normalização correta.

    Args:
        df_carteira: DataFrame completo da carteira Nuclea (já em memória).
        cnpjs: Lista de identificadores vindos do upload do gestor.

    Returns:
        (df_encontrados, nao_encontrados)
    """
    def _normalizar(v: str) -> str:
        v = str(v).strip().lower()
        # SHA-256: 64 chars hexadecimais — preservar intacto
        if len(v) == 64 and all(c in '0123456789abcdef' for c in v):
            return v
        # CNPJ: extrair dígitos e zero-pad para 14 chars
        digits = ''.join(c for c in v if c.isdigit())
        if digits:
            return digits.zfill(14)
        return v  # fallback: sem alteração

    nuclea_norm = df_carteira['id_cnpj'].astype(str).apply(_normalizar)
    upload_norm = [_normalizar(c) for c in cnpjs]
    upload_map  = {_normalizar(c): c for c in cnpjs}

    mascara = nuclea_norm.isin(set(upload_norm))
    df_encontrados = df_carteira[mascara].copy()

    encontrados_norm = set(nuclea_norm[mascara].tolist())
    nao_encontrados  = [upload_map[n] for n in upload_norm if n not in encontrados_norm]

    return df_encontrados, nao_encontrados

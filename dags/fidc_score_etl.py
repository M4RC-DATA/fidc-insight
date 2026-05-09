"""
============================================================================
DAG · FIDC Insight · ETL diário da carteira consolidada
============================================================================

Pipeline executado 1× por dia (schedule="@daily") sobre a tabela
``dataversenuclea.fidc_dataset.tb_score_consolidado``.

Fluxo de 5 tasks encadeadas:

    extract_from_bq  →  validate_quality  →  enrich_score  →  save_snapshot  →  log_summary

Cada task persiste seu resultado em parquet em ``/opt/airflow/data/``,
permitindo retomada individual em caso de falha (idempotência).

Requisitos
----------
1. Pacotes (instalados via dockerfile a partir de requirements.txt):
   - apache-airflow-providers-google
   - pandas-gbq
   - pyarrow

2. Credenciais GCP (Service Account JSON) montadas em:
   /opt/airflow/credentials/gcp-sa.json

   A variável de ambiente ``GOOGLE_APPLICATION_CREDENTIALS`` aponta para
   esse arquivo — configurada no ``docker-compose.yml``.

Uso manual
----------
Para disparar sob demanda (sem esperar o schedule), clique em
"▶ Trigger DAG" no botão "Actions" da UI do Airflow.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# ============================================================================
# Configuração — única fonte da verdade: config/business_rules.py
# ============================================================================
# Garantimos que o pacote do app esteja no sys.path para que o Airflow
# consiga importar as regras de negócio. Tentamos vários caminhos comuns
# (montagem em /opt/airflow ou execução local) sem quebrar caso nenhum
# funcione: nesse caso, fazemos fallback para constantes locais.
_CANDIDATE_ROOTS = [
    Path("/opt/airflow"),                         # padrão docker-compose
    Path("/opt/airflow/dags").parent,             # idem (variação)
    Path(__file__).resolve().parent.parent,       # execução fora do Docker
]
for _root in _CANDIDATE_ROOTS:
    if (_root / "config" / "business_rules.py").exists():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break

try:
    # Fonte única — qualquer mudança de pesos/fatores aqui se reflete no app
    from config.business_rules import (
        ATRASO_CAP_DIAS,
        FATOR_REGIONAL,
        FATOR_REGIONAL_DEFAULT,
        INAD_PESO_ATRASO,
        INAD_PESO_SHARE,
        LIQ_PESO_1M,
        LIQ_PESO_3M,
        PESOS,
    )
except ImportError:
    # Fallback defensivo: mantém o DAG operável mesmo se o módulo não
    # estiver disponível (p.ex. ambiente Airflow isolado). Os valores
    # devem ser mantidos sincronizados com config/business_rules.py.
    PESOS = {
        "qualidade":     0.35,
        "liquidez":      0.25,
        "inadimplencia": 0.30,
        "regional":      0.10,
    }
    FATOR_REGIONAL = {
        "RO": 1.30, "PR": 1.25, "MT": 1.22, "RS": 1.20, "SC": 1.20,
        "SP": 1.15, "DF": 1.15, "PI": 1.12, "SE": 1.10, "GO": 1.10,
        "BA": 1.10, "PE": 1.08, "CE": 1.08, "RN": 1.08, "MA": 1.12,
        "PA": 1.15, "AM": 1.18, "AL": 1.10, "PB": 1.10, "ES": 1.05,
        "MG": 1.05, "RJ": 1.08, "MS": 1.08, "TO": 1.12, "AP": 1.20,
        "RR": 1.22, "AC": 1.20,
    }
    FATOR_REGIONAL_DEFAULT = 1.10
    ATRASO_CAP_DIAS = 247.0
    INAD_PESO_ATRASO = 0.60
    INAD_PESO_SHARE  = 0.40
    LIQ_PESO_1M = 0.60
    LIQ_PESO_3M = 0.40

BQ_PROJECT_ID = "dataversenuclea"
BQ_DATASET = "fidc_dataset"
BQ_TABLE_CARTEIRA = "tb_score_consolidado"

# Paths persistidos no volume ./data montado via docker-compose
DATA_DIR = Path("/opt/airflow/data")
TMP_DIR = DATA_DIR / "tmp"
SNAPSHOT_DIR = DATA_DIR / "snapshots"


# ============================================================================
# Tasks
# ============================================================================
def extract_from_bq(**ctx) -> None:
    """Lê a carteira bruta do BigQuery e grava em staging (raw.parquet)."""
    import pandas_gbq

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    query = f"""
        SELECT *
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_CARTEIRA}`
    """
    df = pandas_gbq.read_gbq(
        query,
        project_id=BQ_PROJECT_ID,
        progress_bar_type=None,
    )
    out = TMP_DIR / "raw.parquet"
    df.to_parquet(out, index=False)
    print(f"[extract] {len(df):,} linhas · {len(df.columns)} colunas → {out}")


def validate_quality(**ctx) -> None:
    """Sanity checks: colunas obrigatórias, nulls, base não vazia."""
    import pandas as pd

    raw = pd.read_parquet(TMP_DIR / "raw.parquet")

    obrigatorias = [
        "id_cnpj", "uf",
        "score_quantidade_v2", "score_materialidade_v2",
        "media_atraso_dias", "share_vl_inad_pag_bol_6_a_15d",
    ]
    faltantes = [c for c in obrigatorias if c not in raw.columns]
    if faltantes:
        raise ValueError(f"Colunas obrigatórias ausentes: {faltantes}")

    if len(raw) == 0:
        raise ValueError("Base vazia — extração falhou silenciosamente?")

    if raw["id_cnpj"].isna().any():
        n = int(raw["id_cnpj"].isna().sum())
        raise ValueError(f"{n} CNPJs nulos na base — integridade comprometida")

    print(
        f"[validate] {len(raw):,} linhas · {len(raw.columns)} colunas · "
        f"UFs={raw['uf'].nunique()} · OK"
    )


def enrich_score(**ctx) -> None:
    """Calcula as 4 dimensões e o score 0–1.000. Grava enriched.parquet."""
    import pandas as pd

    df = pd.read_parquet(TMP_DIR / "raw.parquet").copy()

    # Coerção numérica com imputação por moda da UF.
    # Moda por UF preserva padrões regionais: imputar pela mediana global
    # distorce o score de sacados em estados com comportamentos atípicos.
    # Fallback: mediana global para UFs sem observações válidas.
    cols_num = [
        "sacado_indice_liquidez_1m", "score_quantidade_v2",
        "score_materialidade_v2", "media_atraso_dias",
        "indicador_liquidez_quantitativo_3m",
        "share_vl_inad_pag_bol_6_a_15d",
    ]
    # Colunas contínuas → mediana por UF (preserva padrão regional e é
    # estatisticamente mais estável que moda para variáveis contínuas).
    # Fallback: mediana global para UFs sem observações suficientes.
    for col in cols_num:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if "uf" in df.columns and df[col].isna().any():
            mediana_uf = df.groupby("uf")[col].transform(
                lambda s: s.median() if s.notna().any() else float("nan")
            )
            mediana_global = df[col].median()
            df[col] = df[col].fillna(mediana_uf).fillna(mediana_global)
        else:
            df[col] = df[col].fillna(df[col].median())

    # ── Componente 1 · Qualidade creditícia
    # score_quantidade_v2 e score_materialidade_v2 estão em escala 0-1000
    df["v_qualidade"] = (
        (df["score_quantidade_v2"] / 1000) * 0.5
        + (df["score_materialidade_v2"] / 1000) * 0.5
    ).clip(0.0, 1.0)

    # ── Componente 2 · Liquidez
    # Clip defensivo: se o índice vier > 1 do BQ, não infla o score.
    df["v_liquidez"] = (
        df["sacado_indice_liquidez_1m"] * LIQ_PESO_1M
        + df["indicador_liquidez_quantitativo_3m"] * LIQ_PESO_3M
    ).clip(0.0, 1.0)
    # Alerta: se a maioria dos valores estiver saturada em 1.0, verificar
    # se os índices vieram fora da escala esperada [0, 1] do BigQuery
    pct_saturado = (df["v_liquidez"] >= 0.999).mean()
    if pct_saturado > 0.5:
        print(f"[ALERTA] v_liquidez saturado em {pct_saturado:.0%} dos sacados — "
              f"verificar escala dos índices no BigQuery")

    # ── Componente 3 · Inadimplência (invertida)
    # Normalização com teto fixo: 0 dias → 1.0; ≥ ATRASO_CAP_DIAS → 0.0
    # Uso de teto absoluto garante estabilidade cross-run do score.
    df["v_atraso_inv"] = (1 - df["media_atraso_dias"] / ATRASO_CAP_DIAS).clip(0.0, 1.0)
    df["v_inad_inv"] = (1 - df["share_vl_inad_pag_bol_6_a_15d"]).clip(0.0, 1.0)
    df["v_inadimplencia"] = (
        df["v_atraso_inv"] * INAD_PESO_ATRASO + df["v_inad_inv"] * INAD_PESO_SHARE
    ).clip(0.0, 1.0)

    # ── Componente 4 · Fator regional (bounds FIXOS do dicionário completo)
    # Sem bounds fixos, se uma UF extrema não tiver sacados num dia os scores
    # regionais de todos os outros sacados se deslocam entre execuções.
    todos_fatores = list(FATOR_REGIONAL.values()) + [FATOR_REGIONAL_DEFAULT]
    fi_min_fixo = 1.0 / max(todos_fatores)   # UF mais arriscada → menor fator_inv
    fi_max_fixo = 1.0 / min(todos_fatores)   # UF menos arriscada → maior fator_inv
    fator_inv = 1.0 / df["uf"].map(FATOR_REGIONAL).fillna(FATOR_REGIONAL_DEFAULT)
    df["v_regional"] = (
        (fator_inv - fi_min_fixo) / (fi_max_fixo - fi_min_fixo + 1e-9)
    ).clip(0.0, 1.0)

    # ── Score final
    df["score_calculado"] = (
        df["v_qualidade"]        * PESOS["qualidade"]
        + df["v_liquidez"]       * PESOS["liquidez"]
        + df["v_inadimplencia"]  * PESOS["inadimplencia"]
        + df["v_regional"]       * PESOS["regional"]
    ) * 1000
    df["score_calculado"] = df["score_calculado"].clip(0, 1000).round(2)

    # Sanity final — score precisa estar em [0, 1000]
    if not df["score_calculado"].between(0, 1000).all():
        n_fora = int((~df["score_calculado"].between(0, 1000)).sum())
        raise ValueError(f"{n_fora} scores fora do intervalo [0, 1000]")

    out = TMP_DIR / "enriched.parquet"
    df.to_parquet(out, index=False)
    print(
        f"[enrich] {len(df):,} linhas enriquecidas · "
        f"μ={df['score_calculado'].mean():.1f} · "
        f"σ={df['score_calculado'].std():.1f}"
    )


def save_snapshot(**ctx) -> None:
    """Salva snapshot datado em snapshots/carteira_YYYY-MM-DD.parquet."""
    import pandas as pd

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(TMP_DIR / "enriched.parquet")
    ds = ctx["ds"]  # YYYY-MM-DD da execução atual
    out = SNAPSHOT_DIR / f"carteira_{ds}.parquet"
    df.to_parquet(out, index=False)
    tamanho_kb = out.stat().st_size / 1024
    print(f"[snapshot] {out} · {len(df):,} linhas · {tamanho_kb:.1f} KB")


def log_summary(**ctx) -> None:
    """Resumo executivo nos logs (usado para audit trail e apresentação)."""
    import pandas as pd

    df = pd.read_parquet(TMP_DIR / "enriched.parquet")

    print("\n" + "=" * 70)
    print(f"[summary] PIPELINE FIDC · run_date={ctx['ds']}")
    print("=" * 70)
    print(f"  Total sacados           : {len(df):,}")
    print(f"  UFs representadas       : {df['uf'].nunique()}")
    print(f"  Score médio             : {df['score_calculado'].mean():.1f} / 1000")
    print(f"  Score mediano           : {df['score_calculado'].median():.1f}")
    print(f"  Score mínimo · máximo   : {df['score_calculado'].min():.1f} · "
          f"{df['score_calculado'].max():.1f}")

    # Distribuição de ratings (reusa a faixa do app)
    def rating(s: float) -> str:
        if s >= 900:  return "A+"
        if s >= 800:  return "A"
        if s >= 700:  return "B"
        if s >= 600:  return "C"
        return "D"

    df["rating"] = df["score_calculado"].apply(rating)
    print("\n  Distribuição de ratings:")
    for r, n in df["rating"].value_counts().sort_index().items():
        pct = n / len(df) * 100
        print(f"    {r:<3} {n:>6,} sacados  ({pct:5.1f}%)")
    print("=" * 70)

    # Validação de distribuição — score médio fora de [250, 850] indica
    # possível problema no cálculo (dados fora de escala, imputação falha, etc.)
    score_medio = df["score_calculado"].mean()
    if not (250 <= score_medio <= 850):
        print(f"[ALERTA] Score médio ({score_medio:.1f}) fora do intervalo esperado "
              f"[250, 850] — revisar pipeline de enriquecimento.")


# ============================================================================
# Definição da DAG
# ============================================================================
default_args = {
    "owner": "dataverse",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="fidc_score_etl",
    description="ETL diário · carteira FIDC consolidada do BigQuery",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",  # todo dia às 00:00 UTC
    catchup=False,      # não executa retroativamente
    default_args=default_args,
    tags=["fidc", "bigquery", "etl", "dataverse"],
    doc_md=__doc__,
) as dag:

    extract = PythonOperator(
        task_id="extract_from_bq",
        python_callable=extract_from_bq,
        doc_md="Lê `tb_score_consolidado` do BigQuery e grava em staging.",
    )

    validate = PythonOperator(
        task_id="validate_quality",
        python_callable=validate_quality,
        doc_md="Sanity checks: schema, nulls, base não vazia.",
    )

    enrich = PythonOperator(
        task_id="enrich_score",
        python_callable=enrich_score,
        doc_md="Calcula 4 componentes + score 0–1.000 (idêntico ao app).",
    )

    snapshot = PythonOperator(
        task_id="save_snapshot",
        python_callable=save_snapshot,
        doc_md="Persiste parquet datado em `/opt/airflow/data/snapshots/`.",
    )

    summary = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
        doc_md="Resumo executivo nos logs (distribuição de ratings, médias).",
    )

    extract >> validate >> enrich >> snapshot >> summary
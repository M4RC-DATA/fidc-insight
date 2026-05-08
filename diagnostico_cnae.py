"""
Diagnóstico · CNAE não está aparecendo nas views.

Execute este script na raiz do projeto para descobrir:
  1. Quais colunas a carteira consolidada realmente tem.
  2. Se existe alguma coluna com CNAE (por qualquer nome).
  3. Se os valores estão populados ou vazios.
  4. Se o enriquecimento de segmento roda com a base atual.

USO:
    python diagnostico_cnae.py

A saída mostra exatamente o que está acontecendo.
"""

from __future__ import annotations

import sys

import pandas as pd
import pandas_gbq

from config.settings import BQ_DATASET, BQ_PROJECT_ID, BQ_TABLE_CARTEIRA


def main() -> None:
    print("=" * 72)
    print("DIAGNÓSTICO CNAE · FIDC Insight")
    print("=" * 72)
    print(f"Projeto : {BQ_PROJECT_ID}")
    print(f"Dataset : {BQ_DATASET}")
    print(f"Tabela  : {BQ_TABLE_CARTEIRA}")
    print()

    # ------------------------------------------------------------------
    # 1. Carrega apenas 10 linhas (rápido) e lista TODAS as colunas
    # ------------------------------------------------------------------
    query = f"""
        SELECT *
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_CARTEIRA}`
        LIMIT 10
    """
    print("→ Rodando query LIMIT 10 para listar colunas...")
    try:
        df = pandas_gbq.read_gbq(
            query, project_id=BQ_PROJECT_ID, progress_bar_type=None,
        )
    except Exception as exc:
        print(f"❌ FALHA na query: {exc}")
        sys.exit(1)

    print(f"✅ {len(df)} linhas recebidas · {len(df.columns)} colunas")
    print()

    # ------------------------------------------------------------------
    # 2. TODAS as colunas (numeradas)
    # ------------------------------------------------------------------
    print("─" * 72)
    print("COLUNAS DA CARTEIRA (todas)")
    print("─" * 72)
    for i, c in enumerate(df.columns, 1):
        print(f"  {i:3d}. {c}")
    print()

    # ------------------------------------------------------------------
    # 3. Colunas suspeitas (contêm 'cnae' no nome, maiúsculo/minúsculo)
    # ------------------------------------------------------------------
    suspeitas = [c for c in df.columns if "cnae" in c.lower()]
    print("─" * 72)
    print("COLUNAS COM 'cnae' NO NOME")
    print("─" * 72)
    if suspeitas:
        for c in suspeitas:
            n_nao_null = int(df[c].notna().sum())
            amostra = df[c].dropna().astype(str).head(5).tolist()
            print(f"  ✔ '{c}' — {n_nao_null}/{len(df)} não-nulos")
            print(f"      amostra: {amostra}")
    else:
        print("  ❌ Nenhuma coluna com 'cnae' no nome encontrada.")
        print("  Verifique entre as colunas acima qual tem o código CNAE.")
    print()

    # ------------------------------------------------------------------
    # 4. Testa o enriquecimento
    # ------------------------------------------------------------------
    print("─" * 72)
    print("TESTE DE ENRIQUECIMENTO (services.database._enriquecer_com_segmento)")
    print("─" * 72)
    from services.database import _enriquecer_com_segmento
    df_enr = _enriquecer_com_segmento(df.copy())
    if "cnae_segmento" in df_enr.columns:
        n_ok = int(df_enr["cnae_segmento"].notna().sum())
        print(f"  ✅ Enriquecimento rodou · {n_ok}/{len(df_enr)} sacados classificados")
        if n_ok > 0:
            segs = df_enr["cnae_segmento"].value_counts().to_dict()
            print(f"  Distribuição: {segs}")
    else:
        print("  ❌ Enriquecimento NÃO rodou (coluna cnae_segmento não criada)")
        print("  → Ajuste a lista de candidatos em services/database.py")
    print()

    print("=" * 72)
    print("FIM DO DIAGNÓSTICO")
    print("=" * 72)
    print()
    print("Se alguma coluna acima parece ser o CNAE mas não está na lista de")
    print("candidatos, adicione o nome em services/database.py "
          "(função _enriquecer_com_segmento).")
    print()
    print("Dica: após mudar o código, aperte 'R' (rerun) no Streamlit ou")
    print("reinicie o app para limpar o cache de @st.cache_data (TTL 30 min).")


if __name__ == "__main__":
    main()

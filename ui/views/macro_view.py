"""
View · Visão Geral · FIDC Insight.

Responde: como está a carteira carregada?
Simples: briefing + 4 KPIs + 1 gráfico + alertas.
Detalhes ficam em expanders.
"""

from datetime import datetime
import pandas as pd
import streamlit as st

from domain.risk import hhi_por_uf
from ui.charts import barras_uf, donut_ratings, histograma_scores
from ui.components import render_callout, render_kpi_row, section_divider
from utils.formatters import formatar_moeda, formatar_numero, formatar_percentual


def _score_ponderado(df: pd.DataFrame) -> float:
    p = df["vlr_nominal_total"].clip(lower=0)
    return float((p * df["score_calculado"]).sum() / p.sum()) if p.sum() > 0 else float(df["score_calculado"].mean())


def render(df: pd.DataFrame) -> None:

    # Cálculos
    pl        = df["vlr_nominal_total"].sum()
    n         = len(df)
    score_m   = _score_ponderado(df)
    pct_a     = df["rating_calculado"].isin(["A+","A"]).mean() * 100
    pct_d     = (df["score_calculado"] < 600).mean() * 100
    hhi       = hhi_por_uf(df)
    rating_dom= df["rating_calculado"].mode().iloc[0] if n else "—"
    top_uf    = df.groupby("uf")["vlr_nominal_total"].sum().idxmax() if n else "—"
    pct_top   = (df.groupby("uf")["vlr_nominal_total"].sum().max() / pl * 100) if pl > 0 else 0

    # Briefing — uma frase
    alertas = []
    if hhi > 0.25:     alertas.append(f"🔴 Concentração geográfica crítica (HHI {hhi:.3f})")
    elif hhi > 0.15:   alertas.append(f"🟡 Concentração geográfica moderada — {top_uf} com {pct_top:.1f}% do PL")
    if pct_d > 25:     alertas.append(f"🔴 {pct_d:.1f}% da carteira em rating D")
    elif pct_d > 15:   alertas.append(f"🟡 {pct_d:.1f}% em rating D — monitorar")
    if pct_a < 40:     alertas.append(f"🟡 Apenas {pct_a:.1f}% em grau de investimento")

    if not alertas:
        render_callout(f"✅ Carteira saudável — score médio {score_m:.0f} pts, {pct_a:.0f}% em grau de investimento, HHI {hhi:.3f}.", tipo="destaque")
    elif any("🔴" in a for a in alertas):
        render_callout("🚨 " + " · ".join(alertas), tipo="critico")
    else:
        render_callout("⚠️ " + " · ".join(alertas), tipo="alerta")

    # 4 KPIs
    render_kpi_row([
        {"label": "PL Total",            "value": formatar_moeda(pl, casas=0),
         "sub": f"{formatar_numero(n)} sacados", "variant": "accent"},
        {"label": "Score Nuclea Médio",  "value": f"{score_m:.0f}",
         "sub": "ponderado por volume", "variant": "premium"},
        {"label": "Grau de Investimento","value": f"{pct_a:.1f}%",
         "sub": "sacados A+/A", "variant": "pos" if pct_a >= 60 else "cau"},
        {"label": "HHI Geográfico",      "value": f"{hhi:.3f}",
         "sub": "< 0,15 diversificado",
         "variant": "pos" if hhi < 0.15 else "cau" if hhi < 0.25 else "neg"},
    ])

    section_divider()

    # Gráfico principal
    col1, col2 = st.columns([4, 6], gap="medium")
    with col1:
        st.markdown(f"Mix de Risco · rating dominante {rating_dom}")
        st.plotly_chart(donut_ratings(df), use_container_width=True, config={"displayModeBar": False}, key="macro_donut")
    with col2:
        st.markdown("Distribuição de Score Nuclea")
        st.plotly_chart(histograma_scores(df), use_container_width=True, config={"displayModeBar": False}, key="macro_hist")

    # Detalhes em expander
    with st.expander("▶ Ver concentração geográfica"):
        st.plotly_chart(barras_uf(df), use_container_width=True, config={"displayModeBar": False}, key="macro_uf")

    with st.expander("▶ Ver todos os sacados"):
        cols = [c for c in ["id_cnpj","uf","rating_calculado","score_calculado","vlr_nominal_total"] if c in df.columns]
        df_show = df[cols].copy()
        if "id_cnpj" in df_show.columns:
            from utils.formatters import id_curto
            df_show["id_cnpj"] = df_show["id_cnpj"].apply(id_curto)
        st.dataframe(df_show.rename(columns={
            "id_cnpj":"Sacado","uf":"UF","rating_calculado":"Rating",
            "score_calculado":"Score Nuclea","vlr_nominal_total":"Volume (R$)"
        }), use_container_width=True, hide_index=True, height=350)

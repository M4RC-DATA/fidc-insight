"""
View · Benchmark · Base de Referência Núclea.

Não é uma cópia do Cockpit. Esta view é de comparação: posiciona a
carteira do gestor frente à base de referência Núclea (universo de sacados
disponíveis no Dataverse).

Responde:
  1. Como minha carteira se compara à base de referência?
  2. Score médio da minha carteira vs score médio da base?
  3. Inadimplência/atraso da minha carteira vs universo?
  4. Distribuição de rating: minha carteira vs referência?
  5. Concentração e qualidade — quais as principais diferenças?

Importante:
  - Esta NÃO é uma visão consolidada do mercado FIDC.
  - É a base de referência da Núclea (universo de sacados monitorados).
  - Quando não houver carteira carregada, exibe apenas a referência.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui.charts import donut_ratings, histograma_scores
from ui.components import (
    render_callout,
    render_card_head,
    render_kpi_row,
    render_page_header,
    render_section_header,
    section_divider,
)
from utils.formatters import formatar_numero


# ---------------------------------------------------------------------------
# Cálculos de benchmark
# ---------------------------------------------------------------------------

def _score_medio_ponderado(df: pd.DataFrame) -> float:
    """Score médio ponderado pelo volume (mesmo método do Cockpit)."""
    if df.empty or "score_calculado" not in df.columns:
        return 0.0
    if "vlr_nominal_total" in df.columns:
        pesos = df["vlr_nominal_total"].clip(lower=0)
        if pesos.sum() > 0:
            return float((pesos * df["score_calculado"]).sum() / pesos.sum())
    return float(df["score_calculado"].mean())


def _pct_grau_investimento(df: pd.DataFrame) -> float:
    """% de sacados em rating A+ ou A."""
    if df.empty or "rating_calculado" not in df.columns:
        return 0.0
    return float(df["rating_calculado"].isin(["A+", "A"]).mean() * 100)


def _media_atraso(df: pd.DataFrame) -> float:
    """Média de atraso em dias (preferindo o atraso real, fallback no estimado)."""
    if df.empty:
        return 0.0
    if "media_atraso_real_dias" in df.columns and df["media_atraso_real_dias"].notna().any():
        return float(df["media_atraso_real_dias"].mean())
    if "media_atraso_dias" in df.columns:
        return float(df["media_atraso_dias"].mean())
    return 0.0


def _delta_label(carteira: float, referencia: float, casas: int = 1, sufixo: str = "") -> str:
    """Formata um delta carteira − referência, com sinal e ícone informativo.

    O ícone (▲/▼) é apenas direcional; a interpretação bom/ruim depende da
    métrica (mais score é bom, mais atraso é ruim).
    """
    delta = carteira - referencia
    sinal = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
    return f"{sinal} {abs(delta):.{casas}f}{sufixo} vs referência"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(df_nuclea: pd.DataFrame) -> None:
    """Renderiza o benchmark da carteira do gestor vs base Núclea.

    Quando há ``df_carteira_upload`` em ``st.session_state``, compara as duas
    bases lado a lado. Quando não há, exibe apenas a referência com aviso.
    """

    df_carteira = st.session_state.get("df_carteira_upload")
    tem_carteira = df_carteira is not None and not df_carteira.empty

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    render_page_header(
        kicker="Análise Comparativa",
        titulo="Benchmark — sua carteira vs base do projeto",
        subtitulo=(
            "Comparativo entre a carteira carregada e o universo de sacados "
            "monitorados pela Núclea (Dataverse). Não representa o mercado "
            "FIDC consolidado."
        ),
    )

    render_callout(
        "Compara sua carteira carregada com todos os sacados da base do projeto. "
        "Útil para entender se o portfólio está acima ou abaixo do universo disponível.",
        tipo="info",
    )

    if not tem_carteira:
        render_callout(
            "Nenhuma carteira carregada. Você está vendo apenas a base de referência. "
            "Para comparar, faça o upload de uma carteira em Upload de Carteira.",
            tipo="alerta",
        )

    section_divider()

    # ------------------------------------------------------------------
    # 1. Métricas da referência (sempre exibidas)
    # ------------------------------------------------------------------
    score_ref = _score_medio_ponderado(df_nuclea)
    pct_a_ref = _pct_grau_investimento(df_nuclea)
    atraso_ref = _media_atraso(df_nuclea)
    qtd_ref = len(df_nuclea)

    render_section_header(
        titulo="Base de Referência Núclea",
        subtitulo="Universo monitorado · base de comparação para sua carteira.",
    )

    render_kpi_row(
        [
            {
                "label": "Sacados na base",
                "value": formatar_numero(qtd_ref),
                "sub": "universo de referência",
                "variant": "ink",
            },
            {
                "label": "Score médio · referência",
                "value": f"{score_ref:.0f}",
                "sub": "ponderado por volume",
                "variant": "premium",
            },
            {
                "label": "Grau de investimento",
                "value": f"{pct_a_ref:.1f}%",
                "sub": "sacados em A+/A",
                "variant": "pos" if pct_a_ref >= 60 else "cau",
            },
            {
                "label": "Atraso médio",
                "value": f"{atraso_ref:.1f} dias",
                "sub": "média da base",
                "variant": "cau" if atraso_ref > 30 else "ink",
            },
        ],
        cols=4,
    )

    # ------------------------------------------------------------------
    # 2. Comparativo (apenas quando há carteira carregada)
    # ------------------------------------------------------------------
    if tem_carteira:
        section_divider()

        score_cart = _score_medio_ponderado(df_carteira)
        pct_a_cart = _pct_grau_investimento(df_carteira)
        atraso_cart = _media_atraso(df_carteira)
        qtd_cart = len(df_carteira)

        render_section_header(
            titulo="Sua carteira vs referência",
            subtitulo="Diferenças nas métricas-chave de qualidade e risco.",
        )

        # Variant escolhido por mérito relativo:
        #   score e %A → maior é melhor → pos se carteira > ref
        #   atraso     → menor é melhor → pos se carteira < ref
        v_score = "pos" if score_cart >= score_ref else "neg"
        v_pct_a = "pos" if pct_a_cart >= pct_a_ref else "neg"
        v_atraso = "pos" if atraso_cart <= atraso_ref else "neg"

        render_kpi_row(
            [
                {
                    "label": "Sacados · carteira",
                    "value": formatar_numero(qtd_cart),
                    "sub": f"{(qtd_cart / qtd_ref * 100) if qtd_ref else 0:.2f}% da base",
                    "variant": "accent",
                },
                {
                    "label": "Score médio · carteira",
                    "value": f"{score_cart:.0f}",
                    "sub": _delta_label(score_cart, score_ref, casas=0, sufixo=" pts"),
                    "variant": v_score,
                },
                {
                    "label": "Grau de invest. · carteira",
                    "value": f"{pct_a_cart:.1f}%",
                    "sub": _delta_label(pct_a_cart, pct_a_ref, casas=1, sufixo=" p.p."),
                    "variant": v_pct_a,
                },
                {
                    "label": "Atraso médio · carteira",
                    "value": f"{atraso_cart:.1f} dias",
                    "sub": _delta_label(atraso_cart, atraso_ref, casas=1, sufixo=" dias"),
                    "variant": v_atraso,
                },
            ],
            cols=4,
        )

        # Leitura textual do comparativo — uma frase decisória.
        leitura = _interpretar_benchmark(
            score_cart, score_ref, pct_a_cart, pct_a_ref, atraso_cart, atraso_ref
        )
        render_callout(leitura, tipo="info")

        section_divider()

        # ------------------------------------------------------------------
        # 3. Distribuição de rating — carteira vs referência
        # ------------------------------------------------------------------
        render_section_header(
            titulo="Distribuição de rating",
            subtitulo="Mix de risco · carteira (esquerda) vs referência (direita).",
        )

        col_cart, col_ref = st.columns(2, gap="medium")

        with col_cart:
            render_card_head(
                kicker="Sua carteira",
                titulo=f"{qtd_cart} sacados",
                subtitulo=f"{pct_a_cart:.0f}% em grau de investimento",
            )
            st.plotly_chart(
                donut_ratings(df_carteira),
                use_container_width=True,
                config={"displayModeBar": False},
                key="nucleabase_chart_1",
            )

        with col_ref:
            render_card_head(
                kicker="Referência Núclea",
                titulo=f"{formatar_numero(qtd_ref)} sacados",
                subtitulo=f"{pct_a_ref:.0f}% em grau de investimento",
            )
            st.plotly_chart(
                donut_ratings(df_nuclea),
                use_container_width=True,
                config={"displayModeBar": False},
                key="nucleabase_chart_2",
            )

        section_divider()

        # ------------------------------------------------------------------
        # 4. Distribuição de scores — carteira vs referência
        # ------------------------------------------------------------------
        render_section_header(
            titulo="Distribuição de scores",
            subtitulo="Como sua carteira está espalhada na escala 0–1.000 vs referência.",
        )

        col_h_cart, col_h_ref = st.columns(2, gap="medium")
        with col_h_cart:
            render_card_head(kicker="Sua carteira", titulo="Histograma de scores")
            st.plotly_chart(
                histograma_scores(df_carteira),
                use_container_width=True,
                config={"displayModeBar": False},
                key="nucleabase_chart_3",
            )
        with col_h_ref:
            render_card_head(kicker="Referência Núclea", titulo="Histograma de scores")
            st.plotly_chart(
                histograma_scores(df_nuclea),
                use_container_width=True,
                config={"displayModeBar": False},
                key="nucleabase_chart_4",
            )

        section_divider()

        # ------------------------------------------------------------------
        # 5. Diferenças de concentração geográfica — top UFs
        # ------------------------------------------------------------------
        if "uf" in df_carteira.columns and "uf" in df_nuclea.columns:
            render_section_header(
                titulo="Concentração geográfica",
                subtitulo="Participação relativa por UF — carteira vs referência (top deltas).",
            )

            df_cmp_uf = _comparar_uf(df_carteira, df_nuclea)
            if not df_cmp_uf.empty:
                st.dataframe(
                    df_cmp_uf,
                    use_container_width=True,
                    hide_index=True,
                )
                render_callout(
                    "UFs com forte sobre-exposição da carteira (delta positivo elevado) "
                    "concentram risco regional. Avalie no Cockpit os limites internos "
                    "parametrizados (política do fundo).",
                    tipo="tip",
                )

    else:
        # Sem carteira: ainda assim mostra ratings e histograma da referência
        section_divider()
        render_section_header(
            titulo="Visão da Base de Referência",
            subtitulo="Mix de rating e distribuição de scores do universo Núclea.",
        )

        col_d, col_h = st.columns(2, gap="medium")
        with col_d:
            render_card_head(kicker="Mix de rating", titulo="Referência Núclea")
            st.plotly_chart(
                donut_ratings(df_nuclea),
                use_container_width=True,
                config={"displayModeBar": False},
                key="nucleabase_chart_5",
            )
        with col_h:
            render_card_head(kicker="Distribuição", titulo="Histograma de scores")
            st.plotly_chart(
                histograma_scores(df_nuclea),
                use_container_width=True,
                config={"displayModeBar": False},
                key="nucleabase_chart_6",
            )


# ---------------------------------------------------------------------------
# Helpers de leitura textual
# ---------------------------------------------------------------------------

def _interpretar_benchmark(
    score_cart: float,
    score_ref: float,
    pct_a_cart: float,
    pct_a_ref: float,
    atraso_cart: float,
    atraso_ref: float,
) -> str:
    """Constrói uma frase decisória sobre o posicionamento da carteira."""
    pontos: list[str] = []

    if score_cart > score_ref + 5:
        pontos.append(
            f"score médio <b>acima</b> da referência (+{score_cart - score_ref:.0f} pts)"
        )
    elif score_cart < score_ref - 5:
        pontos.append(
            f"score médio <b>abaixo</b> da referência ({score_cart - score_ref:.0f} pts)"
        )

    if pct_a_cart > pct_a_ref + 1:
        pontos.append(f"mais grau de investimento (+{pct_a_cart - pct_a_ref:.1f} p.p.)")
    elif pct_a_cart < pct_a_ref - 1:
        pontos.append(f"menos grau de investimento ({pct_a_cart - pct_a_ref:.1f} p.p.)")

    if atraso_cart < atraso_ref - 1:
        pontos.append(
            f"atraso médio menor que a referência ({atraso_cart - atraso_ref:.1f} dias)"
        )
    elif atraso_cart > atraso_ref + 1:
        pontos.append(
            f"atraso médio maior que a referência (+{atraso_cart - atraso_ref:.1f} dias)"
        )

    if not pontos:
        return (
            "<b>Sua carteira está alinhada à base de referência</b> nas três métricas-chave "
            "(score, grau de investimento e atraso médio). Nenhum desvio relevante."
        )

    return "<b>Posicionamento relativo:</b> " + "; ".join(pontos) + "."


def _comparar_uf(df_carteira: pd.DataFrame, df_referencia: pd.DataFrame) -> pd.DataFrame:
    """Tabela comparativa de participação por UF entre carteira e referência.

    Retorna as 10 UFs com maior delta absoluto (sobre ou sub-exposição relativa).
    """
    if "uf" not in df_carteira.columns or "uf" not in df_referencia.columns:
        return pd.DataFrame()

    if (
        "vlr_nominal_total" in df_carteira.columns
        and df_carteira["vlr_nominal_total"].sum() > 0
    ):
        s_cart = (
            df_carteira.groupby("uf")["vlr_nominal_total"].sum()
            / df_carteira["vlr_nominal_total"].sum()
        )
    else:
        s_cart = df_carteira["uf"].value_counts(normalize=True)

    if (
        "vlr_nominal_total" in df_referencia.columns
        and df_referencia["vlr_nominal_total"].sum() > 0
    ):
        s_ref = (
            df_referencia.groupby("uf")["vlr_nominal_total"].sum()
            / df_referencia["vlr_nominal_total"].sum()
        )
    else:
        s_ref = df_referencia["uf"].value_counts(normalize=True)

    df = pd.concat(
        [s_cart.rename("Carteira"), s_ref.rename("Referência")],
        axis=1,
    ).fillna(0.0)

    df["Delta (p.p.)"] = (df["Carteira"] - df["Referência"]) * 100
    df["Carteira"] = df["Carteira"].apply(lambda x: f"{x*100:.1f}%")
    df["Referência"] = df["Referência"].apply(lambda x: f"{x*100:.1f}%")
    df["Delta (p.p.)"] = df["Delta (p.p.)"].apply(lambda x: f"{x:+.1f}")
    df = df.reset_index().rename(columns={"uf": "UF"})

    # Ordena por delta absoluto (maior diferença primeiro)
    df["_abs"] = df["Delta (p.p.)"].str.replace("+", "").astype(float).abs()
    df = df.sort_values("_abs", ascending=False).head(10).drop(columns="_abs")

    return df

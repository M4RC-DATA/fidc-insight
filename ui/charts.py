"""
Gráficos Plotly · tema Executive Dashboard (v3).

Paleta fintech azul + dourado premium. Fontes maiores que o usual para
leitura em projetor. Grid hairline, sem gradientes decorativos (o peso
visual vem dos cards em volta).
"""

from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import theme as t
from config.business_rules import ORDEM_RATINGS


# =============================================================================
# Paleta canônica dos ratings — v3
# =============================================================================
RATING_COLORS = {
    "A+": t.PREMIUM,      # Dourado premium
    "A":  t.POSITIVE,     # Verde institucional
    "B":  t.ACCENT,       # Azul fintech
    "C":  t.CAUTION,      # Laranja
    "D":  t.NEGATIVE,     # Vermelho
}


# =============================================================================
# Velocímetro de score
# =============================================================================
def velocimetro_score(score: float, titulo: str = "Score Nuclea") -> go.Figure:
    """Gauge editorial — número grande, arco com faixas semânticas, marca azul."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={
                "text": (
                    f"<span style='font-size:12px;color:{t.MUTED};"
                    f"letter-spacing:0.14em;font-weight:600'>{titulo.upper()}</span>"
                ),
                "font": {"family": t.FONT_FAMILY},
            },
            number={
                "font": {
                    "size": 56,
                    "color": t.INK,
                    "family": t.FONT_FAMILY_MONO,
                },
                "valueformat": ".0f",
            },
            gauge={
                "axis": {
                    "range": [0, 1000],
                    "tickcolor": t.BORDER,
                    "tickwidth": 1,
                    "tickfont": {"color": t.MUTED, "size": 11, "family": t.FONT_FAMILY_MONO},
                    "nticks": 6,
                },
                "bar": {"color": t.ACCENT, "thickness": 0.25},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": t.GAUGE_STEPS,
                "threshold": {
                    "line": {"color": t.PREMIUM, "width": 4},
                    "thickness": 0.85,
                    "value": score,
                },
            },
        )
    )
    # Altura fixada em 340 para alinhar com a coluna de Breakdown do Parecer
    # (render_kv_rows com 8 linhas). Mesma altura em velocimetro e termometro.
    fig.update_layout(
        height=340,
        margin=dict(l=24, r=24, t=56, b=24),
        paper_bgcolor=t.BG_CARD,
        font=dict(family=t.FONT_FAMILY),
    )
    return fig


# =============================================================================
# Donut de distribuição de ratings
# =============================================================================
def donut_ratings(df: pd.DataFrame, coluna_rating: str = "rating_calculado") -> go.Figure:
    """Donut com buraco grande e total no centro em mono."""
    contagem = df[coluna_rating].value_counts().reset_index()
    contagem.columns = ["Rating", "Quantidade"]
    contagem["Rating"] = pd.Categorical(
        contagem["Rating"], categories=ORDEM_RATINGS, ordered=True
    )
    contagem = contagem.sort_values("Rating")

    fig = px.pie(
        contagem,
        values="Quantidade",
        names="Rating",
        hole=0.70,
        color="Rating",
        color_discrete_map=RATING_COLORS,
    )
    fig.update_traces(
        textposition="outside",
        textinfo="label+percent",
        textfont=dict(size=12, family=t.FONT_FAMILY, color=t.INK),
        marker=dict(line=dict(color=t.BG_CARD, width=3)),
        hovertemplate="<b>%{label}</b><br>%{value} sacados<br>%{percent}<extra></extra>",
        automargin=True,
    )
    total = int(contagem["Quantidade"].sum())
    fig.update_layout(
        height=360,
        margin=dict(l=30, r=30, t=30, b=30),
        paper_bgcolor=t.BG_CARD,
        font=dict(family=t.FONT_FAMILY, color=t.INK),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY),
        ),
        annotations=[
            dict(
                text=(
                    f"<span style='font-family:{t.FONT_FAMILY_MONO};"
                    f"font-size:30px;color:{t.INK};font-weight:600'>{total:,}</span>"
                    f"<br><span style='font-size:11px;color:{t.MUTED};"
                    f"letter-spacing:0.14em;text-transform:uppercase;font-weight:600'>SACADOS</span>"
                ).replace(",", "."),
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(family=t.FONT_FAMILY),
            )
        ],
    )
    return fig


# =============================================================================
# Barras horizontais por UF
# =============================================================================
def barras_uf(
    df: pd.DataFrame,
    coluna_uf: str = "uf",
    coluna_valor: str = "vlr_nominal_total",
    top_n: int = 10,
) -> go.Figure:
    """Barras horizontais azuis com valor em mono à direita."""
    df_uf = (
        df.groupby(coluna_uf)[coluna_valor]
        .sum()
        .reset_index()
        .sort_values(coluna_valor, ascending=True)
        .tail(top_n)
    )

    fig = go.Figure(
        go.Bar(
            x=df_uf[coluna_valor],
            y=df_uf[coluna_uf],
            orientation="h",
            marker=dict(color=t.ACCENT, line=dict(width=0)),
            text=[f"R$ {v/1_000_000:.1f}M".replace(".", ",") for v in df_uf[coluna_valor]],
            textposition="outside",
            textfont=dict(size=12, color=t.INK, family=t.FONT_FAMILY_MONO),
            hovertemplate="<b>%{y}</b><br>R$ %{x:,.0f}<extra></extra>",
            width=0.58,
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=360,
        margin=dict(l=16, r=120, t=14, b=30),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        font=dict(family=t.FONT_FAMILY, color=t.INK),
        xaxis=dict(
            gridcolor=t.BORDER_SOFT,
            showline=False,
            zeroline=False,
            tickfont=dict(size=11, color=t.MUTED, family=t.FONT_FAMILY_MONO),
            showticklabels=False,
            automargin=True,
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=13, color=t.INK, family=t.FONT_FAMILY_MONO),
            automargin=True,
        ),
        bargap=0.32,
    )
    return fig


# =============================================================================
# Linha histórica de score
# =============================================================================
def linha_historico(df: pd.DataFrame) -> Optional[go.Figure]:
    """Linha azul com fill suave."""
    if df.empty:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["data_consulta"],
            y=df["score_fidc"],
            mode="lines+markers",
            line=dict(color=t.ACCENT, width=2.2, shape="spline", smoothing=0.6),
            marker=dict(
                size=8,
                color=t.BG_CARD,
                line=dict(color=t.ACCENT, width=2),
            ),
            hovertemplate="<b>%{x}</b><br>Score %{y:.0f}<extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(37, 99, 235, 0.08)",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=44, r=24, t=20, b=34),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        font=dict(family=t.FONT_FAMILY, color=t.INK),
        xaxis=dict(
            gridcolor=t.BORDER_SOFT,
            showline=False,
            tickfont=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY_MONO),
        ),
        yaxis=dict(
            gridcolor=t.BORDER_SOFT,
            range=[0, 1000],
            showline=False,
            tickfont=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY_MONO),
        ),
        showlegend=False,
    )
    return fig


# =============================================================================
# Histograma de scores
# =============================================================================
def histograma_scores(df: pd.DataFrame, coluna: str = "score_calculado") -> go.Figure:
    """Histograma azul com linha tracejada premium na mediana."""
    fig = go.Figure(
        go.Histogram(
            x=df[coluna],
            nbinsx=30,
            marker=dict(color=t.ACCENT, line=dict(width=0)),
            hovertemplate="Faixa %{x}<br>%{y} sacados<extra></extra>",
            opacity=0.88,
        )
    )
    mediana = float(df[coluna].median())
    fig.add_vline(
        x=mediana,
        line=dict(color=t.PREMIUM, width=2, dash="dash"),
        annotation_text=f"  mediana {mediana:.0f}  ",
        annotation_position="top right",
        annotation_font=dict(size=11, color=t.PREMIUM_DARK, family=t.FONT_FAMILY_MONO),
        annotation_bgcolor="rgba(255,255,255,0.92)",
    )
    fig.update_layout(
        height=280,
        margin=dict(l=56, r=56, t=40, b=40),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        font=dict(family=t.FONT_FAMILY),
        xaxis=dict(
            gridcolor=t.BORDER_SOFT,
            range=[0, 1000],
            showline=False,
            tickfont=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY_MONO),
            automargin=True,
        ),
        yaxis=dict(
            gridcolor=t.BORDER_SOFT,
            showline=False,
            tickfont=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY_MONO),
            automargin=True,
        ),
        bargap=0.05,
    )
    return fig


# =============================================================================
# MICRO-DISTRIBUIÇÕES — usadas embutidas nos cards de filtro
# =============================================================================
def mini_histograma(
    valores: pd.Series,
    ativos_lo: Optional[float] = None,
    ativos_hi: Optional[float] = None,
    bins: int = 36,
    height: int = 70,
    color_in: Optional[str] = None,
    color_out: Optional[str] = None,
) -> go.Figure:
    """Histograma ultra-compacto para embutir acima de sliders.

    Barras dentro da faixa [ativos_lo, ativos_hi] em ACCENT; fora em cinza claro.
    Sem eixos, sem margens, apenas forma. Deixa o slider abaixo ser o controle.
    """
    color_in = color_in or t.ACCENT
    color_out = color_out or t.MUTED_SOFT

    v = valores.dropna().to_numpy()
    if len(v) == 0:
        fig = go.Figure()
        fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0),
                          paper_bgcolor=t.BG_CARD, plot_bgcolor=t.BG_CARD,
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig

    # Calcula os bins manualmente para poder colorir dentro vs fora
    hist, edges = np.histogram(v, bins=bins)
    centros = (edges[:-1] + edges[1:]) / 2
    larguras = np.diff(edges)

    lo = ativos_lo if ativos_lo is not None else float(v.min())
    hi = ativos_hi if ativos_hi is not None else float(v.max())

    cores = [
        color_in if lo <= c <= hi else color_out
        for c in centros
    ]

    fig = go.Figure(
        go.Bar(
            x=centros,
            y=hist,
            width=larguras,
            marker=dict(color=cores, line=dict(width=0)),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=2, b=2),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        showlegend=False,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        bargap=0.08,
    )
    return fig


def mini_barras_rating(df: pd.DataFrame, ativos: list) -> go.Figure:
    """Barras verticais coloridas com contagem por rating.

    Ratings em ``ativos`` ficam em cor cheia; os demais em cinza claro.
    Altura fixa ~120px — ideal para topo do card.
    """
    contagem = df["rating_calculado"].value_counts().to_dict()
    ratings = list(ORDEM_RATINGS)
    valores = [contagem.get(r, 0) for r in ratings]
    cores = [
        RATING_COLORS[r] if r in ativos else t.MUTED_SOFT
        for r in ratings
    ]

    fig = go.Figure(
        go.Bar(
            x=ratings,
            y=valores,
            marker=dict(color=cores, line=dict(width=0)),
            text=[f"{v:,}".replace(",", ".") for v in valores],
            textposition="outside",
            textfont=dict(size=11, color=t.INK, family=t.FONT_FAMILY_MONO),
            hoverinfo="skip",
            width=0.62,
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=132,
        margin=dict(l=4, r=4, t=24, b=4),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=12, color=t.SLATE, family=t.FONT_FAMILY_MONO),
            fixedrange=True,
        ),
        yaxis=dict(visible=False, fixedrange=True),
        bargap=0.28,
    )
    return fig


def mini_barras_uf(df: pd.DataFrame, ativos: list, top_n: int = 8) -> go.Figure:
    """Barras horizontais Top-N UFs do df. UFs ativas em ACCENT, demais em cinza."""
    agg = (
        df.groupby("uf").size().reset_index(name="qtd")
        .sort_values("qtd", ascending=True).tail(top_n)
    )
    cores = [
        t.ACCENT if uf in ativos else t.MUTED_SOFT
        for uf in agg["uf"]
    ]
    fig = go.Figure(
        go.Bar(
            x=agg["qtd"],
            y=agg["uf"],
            orientation="h",
            marker=dict(color=cores, line=dict(width=0)),
            text=[f"{v}" for v in agg["qtd"]],
            textposition="outside",
            textfont=dict(size=10, color=t.SLATE, family=t.FONT_FAMILY_MONO),
            hoverinfo="skip",
            width=0.62,
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=180,
        margin=dict(l=4, r=44, t=6, b=6),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        showlegend=False,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=11, color=t.INK, family=t.FONT_FAMILY_MONO),
            fixedrange=True,
            automargin=True,
        ),
        bargap=0.28,
    )
    return fig


# =============================================================================
# LASTRO — Termômetro de Autenticidade + Scatter Histórico
# =============================================================================
# Mapa de cores do selo semafórico
_SELO_CORES = {
    "VERDE":    {"bar": t.POSITIVE,  "text": t.POSITIVE,  "soft": t.POSITIVE_SOFT},
    "AMARELO":  {"bar": t.CAUTION,   "text": t.CAUTION,   "soft": t.CAUTION_SOFT},
    "VERMELHO": {"bar": t.NEGATIVE,  "text": t.NEGATIVE,  "soft": t.NEGATIVE_SOFT},
}


def termometro_lastro(icl: float, selo: str, titulo: str = "ICL") -> go.Figure:
    """Gauge de Autenticidade do Lastro (0–100%).

    Pensado para sentar lado a lado com o ``velocimetro_score`` — mesmas
    dimensões e peso visual. Usa cores semafóricas do selo
    (VERDE/AMARELO/VERMELHO).

    Args:
        icl: Índice de Confiança do Lastro (0–100).
        selo: String "VERDE" | "AMARELO" | "VERMELHO".
        titulo: Rótulo acima do gauge.

    Returns:
        ``go.Figure`` com altura 340px (idêntica ao velocímetro de score
        e alinhada com a coluna de Breakdown do Parecer).
    """
    cores = _SELO_CORES.get(selo, _SELO_CORES["AMARELO"])

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=icl,
            number={
                "font": {"size": 56, "color": t.INK, "family": t.FONT_FAMILY_MONO},
                "valueformat": ".0f",
                "suffix": "%",
            },
            title={
                "text": (
                    f"<span style='font-size:12px;color:{t.MUTED};"
                    f"letter-spacing:0.14em;font-weight:600'>{titulo.upper()}</span>"
                ),
                "font": {"family": t.FONT_FAMILY},
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickcolor": t.BORDER,
                    "tickwidth": 1,
                    "tickfont": {
                        "color": t.MUTED, "size": 11,
                        "family": t.FONT_FAMILY_MONO,
                    },
                    "nticks": 6,
                },
                "bar": {"color": cores["bar"], "thickness": 0.25},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40],   "color": t.NEGATIVE_SOFT},
                    {"range": [40, 70],  "color": t.CAUTION_SOFT},
                    {"range": [70, 100], "color": t.POSITIVE_SOFT},
                ],
                "threshold": {
                    "line": {"color": cores["bar"], "width": 4},
                    "thickness": 0.85,
                    "value": icl,
                },
            },
        )
    )
    fig.update_layout(
        height=340,
        margin=dict(l=24, r=24, t=56, b=24),
        paper_bgcolor=t.BG_CARD,
        font=dict(family=t.FONT_FAMILY),
    )
    return fig


def scatter_lastro_historico(
    df_historico: pd.DataFrame,
    valor_proposto: float,
    z_score_valor: float,
    selo: str,
    media_historica: float,
    desvio_historico: float,
) -> go.Figure:
    """Scatter temporal do histórico Cedente × Sacado com a operação proposta.

    - Pontos em azul = histórico normalizado.
    - Linhas tracejadas = média ± 2σ (faixa aceitável).
    - Estrela grande = a operação proposta, colorida conforme o selo.
    - Texto do Z-score na ponta.

    Aceita df com qualquer combinação das colunas-alias (valor_nominal/data_emissao).
    """
    from domain.lastro import normalizar_historico

    hist = normalizar_historico(df_historico)

    fig = go.Figure()

    # Caso sem histórico → apenas a operação proposta + legenda explicativa
    if len(hist) == 0 or hist["data"].notna().sum() == 0:
        hoje = pd.Timestamp.today()
        fig.add_trace(go.Scatter(
            x=[hoje], y=[valor_proposto],
            mode="markers+text",
            marker=dict(
                color=_SELO_CORES.get(selo, _SELO_CORES["AMARELO"])["bar"],
                size=22, symbol="star",
                line=dict(color=t.BG_CARD, width=2),
            ),
            text=["Proposta"],
            textposition="top center",
            textfont=dict(size=11, family=t.FONT_FAMILY_MONO, color=t.INK),
            hovertemplate=(
                "<b>Operação proposta</b><br>"
                f"R$ {valor_proposto:,.0f}".replace(",", ".") +
                "<extra></extra>"
            ),
            name="Proposta",
        ))
        fig.add_annotation(
            x=hoje, y=valor_proposto,
            xshift=80, showarrow=False,
            text="<i>Sem histórico · primeira op.</i>",
            font=dict(size=11, color=t.MUTED, family=t.FONT_FAMILY),
        )
    else:
        datas = hist["data"].dropna()
        valores = hist.loc[datas.index, "valor"]

        # Faixa ±2σ
        if desvio_historico > 0:
            banda_sup = media_historica + 2 * desvio_historico
            banda_inf = max(media_historica - 2 * desvio_historico, 0)
            eixo_x = [datas.min(), pd.Timestamp.today()]
            fig.add_trace(go.Scatter(
                x=eixo_x, y=[banda_sup, banda_sup],
                mode="lines",
                line=dict(color=t.CAUTION_LINE, dash="dot", width=1),
                hoverinfo="skip", showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=eixo_x, y=[banda_inf, banda_inf],
                mode="lines",
                line=dict(color=t.CAUTION_LINE, dash="dot", width=1),
                hoverinfo="skip", showlegend=False,
                fill="tonexty",
                fillcolor="rgba(227,116,0,0.06)",
            ))
            # Linha da média
            fig.add_trace(go.Scatter(
                x=eixo_x, y=[media_historica, media_historica],
                mode="lines",
                line=dict(color=t.SLATE, dash="dash", width=1.2),
                name=f"μ  R$ {media_historica:,.0f}".replace(",", "."),
                hoverinfo="skip",
            ))

        # Histórico
        fig.add_trace(go.Scatter(
            x=datas, y=valores,
            mode="markers",
            marker=dict(
                color=t.ACCENT, size=8, opacity=0.75,
                line=dict(color=t.BG_CARD, width=1.5),
            ),
            name="Histórico",
            hovertemplate=(
                "<b>Operação histórica</b><br>"
                "Data: %{x|%d/%m/%Y}<br>"
                "R$ %{y:,.0f}<extra></extra>"
            ),
        ))

        # Operação proposta — destaque em estrela. Texto do Z-score fica
        # ACIMA do marcador para não ser cortado pela margem direita do
        # plot (a estrela fica na data=hoje, na borda direita do eixo X).
        hoje = pd.Timestamp.today()
        cor_selo = _SELO_CORES.get(selo, _SELO_CORES["AMARELO"])["bar"]
        fig.add_trace(go.Scatter(
            x=[hoje], y=[valor_proposto],
            mode="markers+text",
            marker=dict(
                color=cor_selo, size=24, symbol="star",
                line=dict(color=t.BG_CARD, width=2.5),
            ),
            text=[f"Z = {z_score_valor:+.1f}σ"],
            textposition="top center",
            textfont=dict(size=12, family=t.FONT_FAMILY_MONO, color=cor_selo),
            name="Operação proposta",
            cliponaxis=False,
            hovertemplate=(
                "<b>OPERAÇÃO PROPOSTA</b><br>"
                f"R$ {valor_proposto:,.0f}".replace(",", ".") +
                f"<br>Z-score: {z_score_valor:+.2f}σ<br>"
                f"Selo: {selo}<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=340,
        margin=dict(l=12, r=40, t=52, b=36),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1.0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY),
        ),
        xaxis=dict(
            gridcolor=t.BORDER_SOFT, linecolor=t.BORDER,
            tickfont=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY_MONO),
            tickformat="%b/%y",
        ),
        yaxis=dict(
            gridcolor=t.BORDER_SOFT, linecolor=t.BORDER,
            tickfont=dict(size=11, color=t.SLATE, family=t.FONT_FAMILY_MONO),
            tickprefix="R$ ", tickformat=",.0f",
            title=dict(
                text="Valor nominal",
                font=dict(size=11, color=t.MUTED, family=t.FONT_FAMILY),
            ),
        ),
    )
    return fig


def barras_componentes_icl(componentes: dict) -> go.Figure:
    """Mini-barras horizontais com os 4 componentes do ICL (0–100)."""
    labels_map = {
        "volume":      "Volume (Z)",
        "recorrencia": "Recorrência",
        "frequencia":  "Frequência",
        "prazo":       "Prazo",
    }
    ordem = ["volume", "recorrencia", "frequencia", "prazo"]
    labels = [labels_map[k] for k in ordem]
    valores = [componentes.get(k, 0.0) for k in ordem]
    cores = [
        t.POSITIVE if v >= 70 else (t.CAUTION if v >= 40 else t.NEGATIVE)
        for v in valores
    ]

    fig = go.Figure(go.Bar(
        x=valores, y=labels, orientation="h",
        marker=dict(color=cores, line=dict(width=0)),
        text=[f"{v:.0f}" for v in valores],
        textposition="outside",
        textfont=dict(size=12, color=t.INK, family=t.FONT_FAMILY_MONO),
        hoverinfo="skip",
        width=0.58,
        cliponaxis=False,
    ))
    fig.update_layout(
        height=230,
        margin=dict(l=12, r=56, t=12, b=22),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        showlegend=False,
        xaxis=dict(
            range=[0, 115], visible=False, fixedrange=True,
        ),
        yaxis=dict(
            showgrid=False, showline=False,
            tickfont=dict(size=12, color=t.INK, family=t.FONT_FAMILY),
            fixedrange=True,
            automargin=True,
        ),
        bargap=0.28,
    )
    return fig


# =============================================================================
# SEGMENTO ECONÔMICO (CNAE) — barras horizontais coloridas por segmento
# =============================================================================
def barras_segmento(
    df: pd.DataFrame,
    coluna_segmento: str = "cnae_segmento",
    coluna_cor: str = "cnae_cor",
    coluna_valor: str = "vlr_nominal_total",
    top_n: int = 12,
    modo: str = "volume",  # "volume" | "sacados"
) -> go.Figure:
    """Barras horizontais por segmento econômico (CNAE), já enriquecido.

    Cada segmento ganha sua cor canônica (``config.cnae_rules``) — isso
    cria consistência visual entre a Visão Macro, o Explorador e o Parecer.

    Args:
        df: DataFrame já enriquecido por ``services.cnae.enriquecer_dataframe``.
        modo: ``"volume"`` soma R$ por segmento; ``"sacados"`` conta sacados.
        top_n: limita aos N maiores segmentos (demais somados em "Outros").

    Returns:
        ``go.Figure`` com barras horizontais (maior em cima).
    """
    if coluna_segmento not in df.columns or df.empty:
        fig = go.Figure()
        fig.update_layout(
            height=300, paper_bgcolor=t.BG_CARD, plot_bgcolor=t.BG_CARD,
            annotations=[dict(
                text="Sem dados de segmento disponíveis.",
                xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                font=dict(size=13, color=t.MUTED, family=t.FONT_FAMILY),
            )],
            xaxis=dict(visible=False), yaxis=dict(visible=False),
        )
        return fig

    # Agrega por segmento (preservando a cor)
    if modo == "volume" and coluna_valor in df.columns:
        agg = (
            df.groupby(coluna_segmento, dropna=False)
            .agg(valor=(coluna_valor, "sum"),
                 sacados=(coluna_segmento, "size"),
                 cor=(coluna_cor, "first"))
            .reset_index()
            .rename(columns={coluna_segmento: "segmento"})
            .sort_values("valor", ascending=False)
        )
        metric_col = "valor"
        hover_label = "Volume"
    else:
        agg = (
            df.groupby(coluna_segmento, dropna=False)
            .agg(sacados=(coluna_segmento, "size"),
                 valor=(coluna_valor, "sum") if coluna_valor in df.columns else (coluna_segmento, "size"),
                 cor=(coluna_cor, "first"))
            .reset_index()
            .rename(columns={coluna_segmento: "segmento"})
            .sort_values("sacados", ascending=False)
        )
        metric_col = "sacados"
        hover_label = "Sacados"

    # Top N + "Outros" agregado
    if len(agg) > top_n:
        principais = agg.head(top_n).copy()
        outros = agg.iloc[top_n:]
        linha_outros = pd.DataFrame([{
            "segmento": f"Outros ({len(outros)} segmentos)",
            "valor": outros["valor"].sum(),
            "sacados": outros["sacados"].sum(),
            "cor": t.MUTED_SOFT,
        }])
        agg = pd.concat([principais, linha_outros], ignore_index=True)

    # Ordem crescente para o Plotly renderizar o maior em cima
    agg = agg.sort_values(metric_col, ascending=True).reset_index(drop=True)

    total = agg[metric_col].sum()
    shares = (agg[metric_col] / total * 100) if total > 0 else agg[metric_col] * 0

    if modo == "volume":
        texto = [f"R$ {v/1_000_000:.1f}M".replace(".", ",") for v in agg["valor"]]
        hover_fmt = "<b>%{y}</b><br>Volume: R$ %{x:,.0f}<br>%{customdata[0]} sacados · %{customdata[1]:.1f}%<extra></extra>"
    else:
        texto = [f"{int(v):,}".replace(",", ".") for v in agg["sacados"]]
        hover_fmt = "<b>%{y}</b><br>Sacados: %{x}<br>%{customdata[1]:.1f}% da carteira<extra></extra>"

    customdata = list(zip(agg["sacados"].astype(int), shares.round(2)))

    fig = go.Figure(
        go.Bar(
            x=agg[metric_col],
            y=agg["segmento"],
            orientation="h",
            marker=dict(color=agg["cor"].tolist(), line=dict(width=0)),
            text=texto,
            textposition="outside",
            textfont=dict(size=12, color=t.INK, family=t.FONT_FAMILY_MONO),
            customdata=customdata,
            hovertemplate=hover_fmt,
            width=0.62,
            cliponaxis=False,
            constraintext="none",
        )
    )

    altura = max(280, 36 * len(agg) + 80)  # cresce com N
    # Estende o range do eixo X para garantir espaço para o texto externo.
    # Com "R$ 1234.5M" em mono precisamos de ~15% de folga à direita.
    max_val = float(agg[metric_col].max()) if len(agg) else 0
    x_max = max_val * 1.18 if max_val > 0 else 1

    fig.update_layout(
        height=altura,
        margin=dict(l=16, r=140, t=14, b=32),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        font=dict(family=t.FONT_FAMILY, color=t.INK),
        xaxis=dict(
            gridcolor=t.BORDER_SOFT,
            showline=False,
            zeroline=False,
            tickfont=dict(size=11, color=t.MUTED, family=t.FONT_FAMILY_MONO),
            showticklabels=False,
            automargin=True,
            range=[0, x_max],
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(size=12, color=t.INK, family=t.FONT_FAMILY),
            automargin=True,
        ),
        bargap=0.30,
        uniformtext=dict(mode="hide", minsize=10),
    )
    return fig


# =============================================================================
# MINI-BARRAS de segmento — embutidas no card de filtros do Explorador
# =============================================================================
def mini_barras_segmento(
    df: pd.DataFrame,
    ativos: list,
    coluna_segmento: str = "cnae_segmento",
    coluna_cor: str = "cnae_cor",
) -> go.Figure:
    """Mini-barras verticais por segmento (compacto, sem eixos).

    Segmentos ativos ficam na cor do segmento; os demais ficam em cinza claro.
    Análogo a ``mini_barras_rating`` / ``mini_barras_uf``.
    """
    if coluna_segmento not in df.columns or df.empty:
        fig = go.Figure()
        fig.update_layout(height=90, margin=dict(l=0, r=0, t=0, b=0),
                          paper_bgcolor=t.BG_CARD, plot_bgcolor=t.BG_CARD,
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig

    agg = (
        df.groupby(coluna_segmento, dropna=False)
        .agg(qtd=(coluna_segmento, "size"), cor=(coluna_cor, "first"))
        .reset_index()
        .rename(columns={coluna_segmento: "segmento"})
        .sort_values("qtd", ascending=False)
    )

    cores = [
        c if s in ativos else t.MUTED_SOFT
        for s, c in zip(agg["segmento"], agg["cor"])
    ]

    fig = go.Figure(
        go.Bar(
            x=agg["segmento"],
            y=agg["qtd"],
            marker=dict(color=cores, line=dict(width=0)),
            hoverinfo="skip",
            width=0.65,
        )
    )
    fig.update_layout(
        height=90,
        margin=dict(l=0, r=0, t=2, b=2),
        paper_bgcolor=t.BG_CARD,
        plot_bgcolor=t.BG_CARD,
        showlegend=False,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        bargap=0.18,
    )
    return fig

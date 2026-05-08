"""
Componentes visuais · Executive Dashboard (v3).

Cada helper renderiza uma das classes do CSS em ``ui/styles.py``. Tudo o
HTML é produzido **sem indentação** (ou passa por ``textwrap.dedent``)
porque o parser de Markdown do Streamlit interpreta linhas com 4+ espaços
de indentação como bloco de código, fazendo o HTML aparecer como texto
literal. Mantemos a arquitetura declarativa e segura.
"""

from textwrap import dedent
from typing import Iterable, Optional, Sequence

import streamlit as st

from config import theme as t
from config.settings import APP_SUBTITLE, APP_TITLE


# =============================================================================
# helper interno — render seguro (sem indentação virando code-block)
# =============================================================================
def _html(markup: str) -> None:
    """Envia HTML para ``st.markdown`` removendo indentação comum."""
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


# =============================================================================
# BRAND (sidebar)
# =============================================================================
def render_brand() -> None:
    """Marca institucional no topo da sidebar (fundo escuro)."""
    _html(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-logo">'
        # Logo Data Verse — V estilizado em SVG inline (ciano + roxo)
        '<svg width="22" height="22" viewBox="0 0 32 32" fill="none" '
        'style="margin-right:8px;flex-shrink:0">'
        '<path d="M4 4 L16 28 L28 4" stroke="#00BCD4" stroke-width="5" '
        'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        '<path d="M4 4 L16 28" stroke="#7C3AED" stroke-width="5" '
        'stroke-linecap="round" fill="none"/>'
        '</svg>'
        '<div>'
        '<span class="sidebar-brand-name">Data Verse</span>'
        '<span class="sidebar-brand-mark" style="font-size:.65rem;font-weight:400;'
        'opacity:.7;display:block;margin-top:1px">FIDC Insight</span>'
        '</div>'
        '</div>'
        '<div class="sidebar-brand-tag">Grupo de Data Science — FIAP</div>'
        '</div>'
    )


# =============================================================================
# PAGE HEADER
# =============================================================================
def render_page_header(
    kicker: str,
    titulo: str,
    subtitulo: str = "",
    data_hora: str = "",
) -> None:
    """Header no topo da página — kicker + título + (opcional) timestamp à direita."""
    sub_html = f'<div class="page-head-sub">{subtitulo}</div>' if subtitulo else ""

    if data_hora:
        right_html = (
            '<div class="page-head-right">'
            f'<div class="time">{data_hora}</div>'
            '<div class="date">tempo real · Núclea</div>'
            '</div>'
        )
    else:
        right_html = ""

    _html(
        '<div class="page-head">'
        '<div class="page-head-left">'
        f'<div class="kicker">{kicker}</div>'
        f'<div class="page-head-title">{titulo}</div>'
        f'{sub_html}'
        '</div>'
        f'{right_html}'
        '</div>'
    )


def render_header(titulo: str = APP_TITLE, subtitulo: str = APP_SUBTITLE) -> None:
    """Compat: delega ao ``render_page_header``."""
    render_page_header(
        kicker="FIDC Insight · Data Verse",
        titulo=titulo,
        subtitulo=subtitulo,
    )


# =============================================================================
# SECTION HEADER
# =============================================================================
def render_section_header(titulo: str, subtitulo: str = "") -> None:
    """Título de seção estilizado com hairline inferior."""
    sub = f'<div class="sub">{subtitulo}</div>' if subtitulo else ""
    _html(
        '<div class="section-header">'
        '<div>'
        f'<div class="title">{titulo}</div>'
        f'{sub}'
        '</div>'
        '</div>'
    )


def render_section(titulo: str, descricao: str = "") -> None:
    """Alias legado."""
    render_section_header(titulo, descricao)


# =============================================================================
# DIVIDERS
# =============================================================================
def section_divider() -> None:
    _html('<div class="section-divider"></div>')


def soft_rule() -> None:
    _html('<div class="section-divider" style="margin:1rem 0;"></div>')


# =============================================================================
# CARD HEAD — header de um card (renderiza em linha acima do conteúdo)
# =============================================================================
def render_card_head(
    kicker: str = "",
    titulo: str = "",
    subtitulo: str = "",
) -> None:
    """Renderiza APENAS o cabeçalho de um card. O conteúdo (chart, df, etc.)
    vem depois e ganha visual de card por CSS aplicado ao próprio widget."""
    kicker_html = f'<div class="kicker">{kicker}</div>' if kicker else ""
    title_html = f'<div class="card-title">{titulo}</div>' if titulo else ""
    sub_html = f'<div class="card-sub">{subtitulo}</div>' if subtitulo else ""
    _html(
        '<div class="card-head-standalone">'
        '<div>'
        f'{kicker_html}{title_html}{sub_html}'
        '</div>'
        '</div>'
    )


# =============================================================================
# HERO PANEL — card escuro full-width
# =============================================================================
def render_hero_panel(
    label: str,
    value: str,
    meta: str = "",
    meta_highlight: str = "",
    stats: Optional[Sequence[tuple]] = None,
) -> None:
    """Hero panel escuro institucional — número grande + stats opcionais."""
    highlight_html = (
        f'<span class="pill-premium">{meta_highlight}</span>'
        if meta_highlight else ""
    )
    meta_html = (
        f'<div class="hero-meta">{meta}{highlight_html}</div>'
        if (meta or meta_highlight) else ""
    )

    if stats:
        cells = []
        for item in stats:
            s_label = item[0]
            s_value = item[1]
            s_foot = item[2] if len(item) > 2 else ""
            foot_html = (
                f'<div class="hero-stat-foot">{s_foot}</div>' if s_foot else ""
            )
            cells.append(
                '<div>'
                f'<div class="hero-stat-label">{s_label}</div>'
                f'<div class="hero-stat-value">{s_value}</div>'
                f'{foot_html}'
                '</div>'
            )
        stats_html = f'<div class="hero-stats">{"".join(cells)}</div>'
    else:
        stats_html = ""

    _html(
        '<div class="hero-panel">'
        '<div class="hero-grid">'
        '<div>'
        f'<div class="hero-label">{label}</div>'
        f'<div class="hero-value">{value}</div>'
        f'{meta_html}'
        '</div>'
        f'{stats_html}'
        '</div>'
        '</div>'
    )


def render_hero_stat(
    label: str,
    value: str,
    meta: str = "",
    meta_accent: str = "",
) -> None:
    """Alias legado do hero simples."""
    render_hero_panel(
        label=label.upper(),
        value=value,
        meta=meta,
        meta_highlight=meta_accent,
    )


# =============================================================================
# KPI ROW — grade horizontal de cards com borda superior colorida
# =============================================================================
_KPI_VARIANTS = {"accent", "premium", "pos", "cau", "neg", "ink"}


def render_kpi_row(kpis: Sequence[dict], cols: int = 4) -> None:
    """Renderiza uma linha de N KPI cards.

    kpi: ``{"label": ..., "value": ..., "sub": ..., "variant": ...}``
    variant: 'accent' | 'premium' | 'pos' | 'cau' | 'neg' | 'ink'
    """
    cols_class = {3: "kpi-3", 5: "kpi-5"}.get(cols, "")

    cards = []
    for k in kpis:
        variant = k.get("variant", "accent")
        variant_class = f"kpi-{variant}" if variant in _KPI_VARIANTS else ""
        sub_html = (
            f'<div class="kpi-sub">{k["sub"]}</div>' if k.get("sub") else ""
        )

        # Auto-ajuste de tamanho: valores longos (> 12 chars) como
        # "Transporte & Logística" ou "Comércio Varejista" recebem
        # fonte menor para não estourar o card.
        valor = str(k["value"])
        if len(valor) > 18:
            value_class = "kpi-value kpi-value-xs"
        elif len(valor) > 12:
            value_class = "kpi-value kpi-value-sm"
        else:
            value_class = "kpi-value"

        cards.append(
            f'<div class="kpi {variant_class}">'
            f'<div class="kpi-label">{k["label"]}</div>'
            f'<div class="{value_class}">{k["value"]}</div>'
            f'{sub_html}'
            '</div>'
        )

    _html(
        f'<div class="kpi-row {cols_class}">{"".join(cards)}</div>'
    )


def render_statbar(stats: Iterable[tuple]) -> None:
    """Legacy — delega para KPI row com variantes alternadas."""
    lista = list(stats)
    variantes = ["accent", "premium", "pos", "cau", "ink"]
    kpis = [
        {
            "label": item[0],
            "value": item[1],
            "sub": item[2] if len(item) > 2 else "",
            "variant": variantes[idx % len(variantes)],
        }
        for idx, item in enumerate(lista)
    ]
    cols = len(kpis) if len(kpis) in (3, 4, 5) else 4
    render_kpi_row(kpis, cols=cols)


# =============================================================================
# SACADO HEAD
# =============================================================================
def render_sacado_head(cnpj: str, rating: str, uf: str, score: float) -> None:
    """Cabeçalho do sacado: CNPJ · rating · UF · score em card branco horizontal."""
    chip = rating_chip(rating)
    _html(
        '<div class="sacado-head">'
        '<div class="sacado-cell">'
        '<div class="kicker">CNPJ / Identificador</div>'
        f'<div class="val">{cnpj}</div>'
        '</div>'
        '<div class="sacado-cell divider"></div>'
        '<div class="sacado-cell">'
        '<div class="kicker">Rating</div>'
        f'<div style="margin-top:0.15rem;">{chip}</div>'
        '</div>'
        '<div class="sacado-cell divider"></div>'
        '<div class="sacado-cell">'
        '<div class="kicker">UF</div>'
        f'<div class="val">{uf}</div>'
        '</div>'
        '<div class="sacado-cell divider"></div>'
        '<div class="sacado-cell">'
        '<div class="kicker">Score</div>'
        f'<div class="val">{score:.0f}'
        f'<span style="color:{t.MUTED};font-size:0.8rem;font-weight:500;"> / 1.000</span>'
        '</div>'
        '</div>'
        '</div>'
    )


# =============================================================================
# SEGMENTO ECONÔMICO (CNAE) — chip + painel
# =============================================================================
def render_segmento_panel(
    segmento: str,
    secao_letra: Optional[str] = None,
    secao_nome: Optional[str] = None,
    descricao_cnae: Optional[str] = None,
    codigo_cnae: Optional[str] = None,
    cor: str = "#7C8CA8",
) -> None:
    """Painel compacto com chip colorido + descrição da atividade CNAE.

    Desenhado para ficar logo abaixo do ``render_sacado_head`` no Parecer
    Individual. Usa a cor do segmento como hairline esquerda para reforçar
    identidade visual sem poluir a paleta.
    """
    cnae_bits = []
    if codigo_cnae:
        cnae_bits.append(
            f'<span style="font-family:{t.FONT_FAMILY_MONO};font-size:0.72rem;'
            f'color:{t.MUTED};background:{t.SURFACE};padding:0.15rem 0.45rem;'
            f'border-radius:4px;margin-right:0.5rem;">CNAE {codigo_cnae}</span>'
        )
    if secao_letra:
        cnae_bits.append(
            f'<span style="font-family:{t.FONT_FAMILY_MONO};font-size:0.7rem;'
            f'color:{t.MUTED};letter-spacing:0.08em;">SEÇÃO {secao_letra}'
            f'{" · " + secao_nome if secao_nome else ""}</span>'
        )
    cnae_row = f'<div style="margin-top:0.35rem;">{"".join(cnae_bits)}</div>' if cnae_bits else ""
    desc = descricao_cnae or "Atividade não classificada"

    _html(
        '<div style="background:#FFFFFF;border:1px solid #E3E8F0;'
        f'border-left:4px solid {cor};border-radius:10px;'
        'padding:0.9rem 1.1rem;margin:0.6rem 0 1rem 0;'
        'box-shadow:0 1px 2px rgba(10,22,40,0.03);">'
        '<div style="display:flex;align-items:center;gap:0.75rem;">'
        f'<span style="background:{cor};color:#FFFFFF;font-weight:700;'
        f'font-size:0.72rem;letter-spacing:0.06em;text-transform:uppercase;'
        'padding:0.3rem 0.6rem;border-radius:5px;white-space:nowrap;">'
        f'{segmento}</span>'
        f'<span style="color:{t.INK};font-size:0.95rem;font-weight:500;'
        f'line-height:1.35;flex:1;">{desc}</span>'
        '</div>'
        f'{cnae_row}'
        '</div>'
    )


def segmento_chip(segmento: str, cor: str = "#7C8CA8") -> str:
    """Pill inline colorido — útil em linhas de tabela/listagem."""
    return (
        f'<span style="display:inline-block;background:{cor};color:#FFFFFF;'
        f'font-family:{t.FONT_FAMILY_MONO};font-size:0.7rem;font-weight:600;'
        f'padding:0.18rem 0.55rem;border-radius:4px;letter-spacing:0.04em;'
        f'white-space:nowrap;">{segmento}</span>'
    )


# =============================================================================
# KEY-VALUE ROWS
# =============================================================================
def render_kv_rows(
    rows: Iterable[tuple],
    emphasize: Optional[Sequence[int]] = None,
) -> None:
    """Lista vertical chave-valor com hairlines entre linhas."""
    emphasize = set(emphasize or [])
    blocos = []
    for idx, item in enumerate(rows):
        label = item[0]
        value = item[1]
        sub = (
            f'<span class="kv-sub">· {item[2]}</span>'
            if len(item) > 2 and item[2] else ""
        )
        classe = "kv-row emphasis" if idx in emphasize else "kv-row"
        blocos.append(
            f'<div class="{classe}">'
            f'<div class="kv-label">{label}</div>'
            f'<div><span class="kv-value">{value}</span>{sub}</div>'
            '</div>'
        )
    _html(f'<div class="kv-list">{"".join(blocos)}</div>')


# =============================================================================
# RATING CHIP / PILLS
# =============================================================================
def rating_chip(rating: str) -> str:
    """Retorna o HTML de um chip de rating."""
    classe = {
        "A+": "rAp",
        "A":  "rA",
        "B":  "rB",
        "C":  "rC",
        "D":  "rD",
    }.get(rating, "rB")
    return f'<span class="rating-chip {classe}">{rating}</span>'


def badge_rating(rating: str) -> str:
    return rating_chip(rating)


def pill(texto: str, variante: str = "ink") -> str:
    """Pill simples — retorna HTML inline."""
    cores = {
        "ink":     (t.INK, "#FFFFFF"),
        "pos":     (t.POSITIVE, "#FFFFFF"),
        "cau":     (t.CAUTION, "#FFFFFF"),
        "neg":     (t.NEGATIVE, "#FFFFFF"),
        "accent":  (t.ACCENT, "#FFFFFF"),
        "premium": (t.PREMIUM, "#FFFFFF"),
    }
    bg, fg = cores.get(variante, cores["ink"])
    return (
        f'<span style="display:inline-block;background:{bg};color:{fg};'
        f'font-family:{t.FONT_FAMILY_MONO};font-size:0.75rem;font-weight:600;'
        f'padding:0.2rem 0.55rem;border-radius:4px;letter-spacing:0.04em;">{texto}</span>'
    )


def badge(texto: str, cor_fundo: str = t.INK, cor_texto: str = "#FFFFFF") -> str:
    return pill(texto, variante="ink")


# =============================================================================
# ALERT BOXES
# =============================================================================
def render_alert(status: str, mensagem: str) -> None:
    """Alert inline com ícone circular."""
    classe, icone = {
        "aprovado": ("alert-green", "✓"),
        "alerta":   ("alert-yellow", "!"),
        "bloqueio": ("alert-red", "✕"),
    }.get(status, ("alert-yellow", "!"))

    _html(
        f'<div class="alert-box {classe}">'
        f'<span class="alert-icon">{icone}</span>'
        f'<span>{mensagem}</span>'
        '</div>'
    )


# =============================================================================
# EWS PANEL
# =============================================================================
def render_ews_panel(
    nivel: str,
    descricao: str = "",
    probabilidade: Optional[float] = None,
) -> None:
    """Painel EWS com nível + probabilidade."""
    nivel_upper = (nivel or "").upper()
    level_class = {
        "BAIXO":    "level-pos",
        "MODERADO": "level-cau",
        "ALTO":     "level-neg",
    }.get(nivel_upper, "level-cau")

    if probabilidade is not None:
        prob_str = f"{probabilidade * 100:.1f}%"
    else:
        import re
        m = re.search(r"([\d]+[.,]?[\d]*)\s*%", descricao or "")
        prob_str = m.group(0).replace(",", ".") if m else "—"

    _html(
        f'<div class="ews-panel {level_class}">'
        '<div>'
        '<div class="ews-label">Radar de Contágio</div>'
        f'<div class="ews-level">{nivel_upper}</div>'
        '</div>'
        f'<div><div class="ews-desc">{descricao}</div></div>'
        '<div style="text-align:right;">'
        '<div class="ews-label">Probabilidade</div>'
        f'<div class="ews-prob">{prob_str}</div>'
        '</div>'
        '</div>'
    )


def render_ews_box(nivel: str, descricao: str = "") -> None:
    render_ews_panel(nivel=nivel, descricao=descricao)


# =============================================================================
# CALLOUT
# =============================================================================
def render_callout(texto: str, tipo: str = "info") -> None:
    """Nota com borda lateral colorida.

    Tipos suportados:
      info     — azul (padrão)
      tip      — dourado
      warning / alerta  — âmbar
      critico           — vermelho
      destaque / success — verde
    """
    _MAP = {
        "info":     "",
        "tip":      "tip",
        "warning":  "warning",
        "alerta":   "alerta",
        "critico":  "critico",
        "destaque": "destaque",
        "success":  "success",
    }
    classe = _MAP.get(tipo, "")
    _html(f'<div class="callout {classe}">{texto}</div>')

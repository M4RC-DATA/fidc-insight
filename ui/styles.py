"""
CSS do sistema Executive Dashboard (v3).

Sidebar escura institucional + área clara com cards de peso real.
Cada "tijolo" de informação tem um container próprio — nada fica solto no fundo.
"""

import streamlit as st

from config import theme as t


def aplicar_tema() -> None:
    """Injeta o CSS Executive Dashboard no app Streamlit."""

    css = f"""
    <style>
        /* =====================================================
           FONTES
           ===================================================== */
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

        /* =====================================================
           LIMPA CROMO DO STREAMLIT
           ===================================================== */
        #MainMenu, footer, header {{ visibility: hidden; }}
        div[data-testid="stDecoration"] {{ display: none; }}
        div[data-testid="stToolbar"] {{ display: none; }}

        /* =====================================================
           BASE
           ===================================================== */
        html, body, [class*="css"] {{
            font-family: {t.FONT_FAMILY};
            color: {t.INK};
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}

        .stApp {{
            background: {t.BG_APP};
        }}

        .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 4rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
            max-width: 1400px !important;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: {t.INK};
            font-weight: 700;
            letter-spacing: -0.02em;
            line-height: 1.2;
            margin: 0;
        }}

        /* =====================================================
           HELPERS UTILITÁRIOS
           ===================================================== */
        .kicker {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 600;
        }}
        .kicker-light {{
            font-size: {t.FS_MICRO};
            color: {t.BRAND_MUTED};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 600;
        }}
        .num {{
            font-family: {t.FONT_FAMILY_MONO};
            font-feature-settings: "tnum" 1;
            font-variant-numeric: tabular-nums;
            letter-spacing: -0.01em;
        }}

        /* =====================================================
           PAGE HEADER
           ===================================================== */
        .page-head {{
            margin: 0 0 1.75rem 0;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 1.5rem;
        }}
        .page-head-left .kicker {{ margin-bottom: 0.4rem; }}
        .page-head-title {{
            font-size: {t.FS_H2};
            font-weight: 700;
            color: {t.INK};
            letter-spacing: -0.03em;
            line-height: 1.15;
        }}
        .page-head-sub {{
            font-size: {t.FS_BODY};
            color: {t.SLATE};
            margin-top: 0.3rem;
            max-width: 760px;
        }}
        .page-head-right {{
            text-align: right;
        }}
        .page-head-right .time {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: {t.FS_SMALL};
            color: {t.SLATE};
        }}
        .page-head-right .date {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-top: 0.2rem;
        }}

        /* =====================================================
           HERO PANEL — card escuro full-width de destaque
           ===================================================== */
        .hero-panel {{
            background: linear-gradient(135deg, {t.BRAND_900} 0%, {t.BRAND_800} 55%, #1A3161 100%);
            color: {t.BRAND_TEXT};
            border-radius: 14px;
            padding: 2rem 2.25rem;
            box-shadow: {t.SHADOW_HERO};
            position: relative;
            overflow: hidden;
            margin-bottom: 1.5rem;
        }}
        .hero-panel::before {{
            content: "";
            position: absolute;
            top: -40%;
            right: -10%;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(37, 99, 235, 0.22) 0%, transparent 60%);
            pointer-events: none;
        }}
        .hero-panel::after {{
            content: "";
            position: absolute;
            bottom: -30%;
            left: -5%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(200, 149, 58, 0.12) 0%, transparent 65%);
            pointer-events: none;
        }}
        .hero-grid {{
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: 1.6fr 1fr;
            gap: 2rem;
            align-items: end;
        }}
        .hero-label {{
            font-size: {t.FS_MICRO};
            color: rgba(229, 236, 247, 0.65);
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }}
        .hero-value {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: {t.FS_HERO};
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: -0.03em;
            line-height: 1.05;
            font-feature-settings: "tnum" 1;
            font-variant-numeric: tabular-nums;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}
        .hero-meta {{
            font-size: {t.FS_BODY};
            color: rgba(229, 236, 247, 0.85);
            margin-top: 0.95rem;
            line-height: 1.55;
        }}
        .hero-meta .pill-premium {{
            display: inline-block;
            background: rgba(200, 149, 58, 0.2);
            border: 1px solid rgba(200, 149, 58, 0.4);
            color: #E3C477;
            padding: 0.15rem 0.55rem;
            border-radius: 4px;
            font-size: {t.FS_CAPTION};
            font-weight: 600;
            letter-spacing: 0.05em;
            margin-left: 0.4rem;
            font-family: {t.FONT_FAMILY_MONO};
        }}
        .hero-stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.1rem 1.5rem;
            border-left: 1px solid rgba(229, 236, 247, 0.12);
            padding-left: 2rem;
        }}
        .hero-stat-label {{
            font-size: {t.FS_MICRO};
            color: rgba(229, 236, 247, 0.55);
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 500;
            margin-bottom: 0.2rem;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}
        .hero-stat-value {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 1.35rem;
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: -0.02em;
            line-height: 1.1;
            font-feature-settings: "tnum" 1;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}
        .hero-stat-foot {{
            font-size: {t.FS_CAPTION};
            color: rgba(229, 236, 247, 0.55);
            margin-top: 0.25rem;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}

        /* =====================================================
           CARDS GENÉRICOS (bento)
           ===================================================== */
        .card {{
            background: {t.BG_CARD};
            border: 1px solid {t.BORDER};
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: {t.SHADOW_CARD};
            margin-bottom: 1rem;
            transition: box-shadow 0.18s ease;
        }}
        .card:hover {{
            box-shadow: {t.SHADOW_HOVER};
        }}
        .card-head {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
            padding-bottom: 0.9rem;
            border-bottom: 1px solid {t.BORDER_SOFT};
        }}
        .card-head-left .kicker {{ margin-bottom: 0.25rem; }}
        .card-title {{
            font-size: {t.FS_LEAD};
            font-weight: 700;
            color: {t.INK};
            letter-spacing: -0.015em;
        }}
        .card-sub {{
            font-size: {t.FS_SMALL};
            color: {t.SLATE};
            margin-top: 0.2rem;
        }}

        /* =====================================================
           CARD HEAD STANDALONE — cabeçalho que fica "grudado"
           visualmente no widget seguinte (chart, dataframe).
           ===================================================== */
        .card-head-standalone {{
            background: {t.BG_CARD};
            border: 1px solid {t.BORDER};
            border-bottom: none;
            border-radius: 12px 12px 0 0;
            padding: 1.1rem 1.4rem 0.9rem 1.4rem;
            margin-bottom: 0 !important;
            box-shadow: {t.SHADOW_CARD};
            position: relative;
            z-index: 1;
        }}
        .card-head-standalone .kicker {{ margin-bottom: 0.25rem; }}
        .card-head-standalone + div [data-testid="stPlotlyChart"],
        .card-head-standalone + div > div [data-testid="stPlotlyChart"] {{
            background: {t.BG_CARD};
            border: 1px solid {t.BORDER};
            border-top: none;
            border-radius: 0 0 12px 12px;
            padding: 0.4rem 1rem 1rem 1rem;
            box-shadow: {t.SHADOW_CARD};
            margin-bottom: 1rem;
        }}

        /* Plotly charts sem header — ganham card próprio */
        [data-testid="stPlotlyChart"] {{
            background: {t.BG_CARD};
            border-radius: 12px;
        }}

        /* =====================================================
           KPI CARDS (4 métricas em grade)
           ===================================================== */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 1.25rem;
        }}
        .kpi-row.kpi-5 {{ grid-template-columns: repeat(5, 1fr); }}
        .kpi-row.kpi-3 {{ grid-template-columns: repeat(3, 1fr); }}
        .kpi {{
            background: {t.BG_CARD};
            border: 1px solid {t.BORDER};
            border-radius: 12px;
            padding: 1.1rem 1.25rem 1.2rem 1.25rem;
            box-shadow: {t.SHADOW_CARD};
            position: relative;
            overflow: hidden;
            transition: all 0.18s ease;
            min-width: 0;
        }}
        .kpi::before {{
            content: "";
            position: absolute;
            top: 0; left: 0;
            height: 3px;
            width: 100%;
            background: {t.ACCENT};
        }}
        .kpi.kpi-premium::before {{ background: {t.PREMIUM}; }}
        .kpi.kpi-pos::before     {{ background: {t.POSITIVE}; }}
        .kpi.kpi-cau::before     {{ background: {t.CAUTION}; }}
        .kpi.kpi-neg::before     {{ background: {t.NEGATIVE}; }}
        .kpi.kpi-ink::before     {{ background: {t.INK}; }}
        .kpi:hover {{
            box-shadow: {t.SHADOW_HOVER};
            transform: translateY(-1px);
        }}
        .kpi-label {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 600;
            margin-bottom: 0.55rem;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}
        .kpi-value {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 1.75rem;
            font-weight: 600;
            color: {t.INK};
            letter-spacing: -0.025em;
            line-height: 1.1;
            font-feature-settings: "tnum" 1;
            font-variant-numeric: tabular-nums;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
            hyphens: auto;
        }}
        /* Valores textuais longos (ex.: "Transporte & Logística") ganham
           fonte menor e sem mono para caber sem cortar. */
        .kpi-value.kpi-value-sm {{
            font-family: {t.FONT_FAMILY};
            font-size: 1.25rem;
            line-height: 1.2;
            letter-spacing: -0.01em;
        }}
        .kpi-value.kpi-value-xs {{
            font-family: {t.FONT_FAMILY};
            font-size: 1.05rem;
            line-height: 1.25;
            letter-spacing: 0;
        }}
        .kpi-sub {{
            font-size: {t.FS_CAPTION};
            color: {t.SLATE};
            margin-top: 0.45rem;
            line-height: 1.4;
            overflow-wrap: anywhere;
            word-break: break-word;
        }}
        .kpi-sub .trend-up   {{ color: {t.POSITIVE}; font-weight: 600; }}
        .kpi-sub .trend-down {{ color: {t.NEGATIVE}; font-weight: 600; }}

        /* =====================================================
           BENTO GRID — 2 ou 3 colunas para cards lado a lado
           ===================================================== */
        .bento-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .bento-5-7 {{
            display: grid;
            grid-template-columns: 5fr 7fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .bento-7-5 {{
            display: grid;
            grid-template-columns: 7fr 5fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }}

        /* =====================================================
           STREAMLIT st.metric — forçamos estética de KPI card
           ===================================================== */
        div[data-testid="metric-container"] {{
            background: {t.BG_CARD};
            border: 1px solid {t.BORDER};
            border-radius: 12px;
            padding: 1.1rem 1.25rem;
            box-shadow: {t.SHADOW_CARD};
            position: relative;
            overflow: hidden;
        }}
        div[data-testid="metric-container"]::before {{
            content: "";
            position: absolute;
            top: 0; left: 0;
            height: 3px;
            width: 100%;
            background: {t.ACCENT};
        }}
        div[data-testid="metric-container"]:hover {{
            box-shadow: {t.SHADOW_HOVER};
            transform: translateY(-1px);
        }}
        div[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
            color: {t.MUTED};
            font-size: {t.FS_MICRO};
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }}
        div[data-testid="metric-container"] [data-testid="stMetricLabel"] p {{
            color: {t.MUTED};
            font-size: {t.FS_MICRO};
        }}
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
            color: {t.INK};
            font-family: {t.FONT_FAMILY_MONO};
            font-weight: 600;
            font-size: 1.65rem;
            letter-spacing: -0.025em;
            font-feature-settings: "tnum" 1;
        }}
        div[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
            font-size: {t.FS_CAPTION};
            font-family: {t.FONT_FAMILY_MONO};
        }}

        /* =====================================================
           SIDEBAR — escura institucional · FIXA (não colapsa)
           ===================================================== */

        /* Esconde o botão "<" que colapsa a sidebar (header dentro dela) */
        section[data-testid="stSidebar"] button[kind="header"],
        section[data-testid="stSidebar"] button[kind="headerNoPadding"],
        section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] {{
            display: none !important;
        }}

        /* Esconde o botão ">" que reabre a sidebar quando ela está colapsada */
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}

        /* Remove a alça de redimensionamento — largura fixa, sem drag */
        [data-testid="stSidebarResizer"],
        [data-testid="stSidebarResizeHandle"] {{
            display: none !important;
            pointer-events: none !important;
        }}

        /* Largura fixa da sidebar (padrão Streamlit é ~336px, mantemos) */
        section[data-testid="stSidebar"] {{
            background: {t.BRAND_900};
            border-right: 1px solid {t.BRAND_700};
            min-width: 300px !important;
            max-width: 300px !important;
            width: 300px !important;
            transform: none !important;  /* impede a animação de colapsar */
            visibility: visible !important;
        }}
        section[data-testid="stSidebar"] > div {{
            padding-top: 1.5rem;
        }}
        section[data-testid="stSidebar"] * {{
            color: {t.BRAND_TEXT};
        }}
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: #FFFFFF;
        }}
        section[data-testid="stSidebar"] label {{
            color: {t.BRAND_MUTED} !important;
            font-weight: 600 !important;
            font-size: {t.FS_MICRO} !important;
            text-transform: uppercase;
            letter-spacing: 0.14em;
        }}
        section[data-testid="stSidebar"] hr {{
            border: none;
            border-top: 1px solid {t.BRAND_700};
            margin: 1.25rem 0;
        }}
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea,
        section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
            background-color: {t.BRAND_800} !important;
            border: 1px solid {t.BRAND_700} !important;
            color: {t.BRAND_TEXT} !important;
            border-radius: 6px !important;
            font-size: {t.FS_SMALL};
        }}
        section[data-testid="stSidebar"] input:focus,
        section[data-testid="stSidebar"] textarea:focus {{
            border-color: {t.ACCENT} !important;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2) !important;
        }}
        section[data-testid="stSidebar"] input::placeholder {{
            color: rgba(229, 236, 247, 0.35) !important;
        }}

        /* Botão primário na sidebar — azul forte com glow */
        section[data-testid="stSidebar"] .stButton > button {{
            background: {t.BRAND_800};
            border: 1px solid {t.BRAND_700};
            color: {t.BRAND_TEXT};
            border-radius: 8px;
            font-weight: 500;
            font-size: {t.FS_SMALL};
        }}
        section[data-testid="stSidebar"] .stButton > button:hover {{
            border-color: {t.ACCENT};
            background: {t.BRAND_800};
        }}
        section[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
            background: {t.ACCENT};
            border: 1px solid {t.ACCENT};
            color: #FFFFFF;
            font-weight: 600;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
        }}
        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
            background: {t.ACCENT_DARK};
            border-color: {t.ACCENT_DARK};
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45);
        }}
        section[data-testid="stSidebar"] .stButton > button[kind="primary"]:disabled {{
            background: {t.BRAND_800};
            border-color: {t.BRAND_700};
            color: {t.BRAND_MUTED};
            box-shadow: none;
        }}

        /* Radio (nav) na sidebar — itens grandes e legíveis */
        section[data-testid="stSidebar"] [data-baseweb="radio"] {{
            padding: 0.55rem 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.15rem;
            transition: background 0.12s ease;
        }}
        section[data-testid="stSidebar"] [data-baseweb="radio"]:hover {{
            background: {t.BRAND_800};
        }}
        section[data-testid="stSidebar"] [data-baseweb="radio"] div {{
            color: {t.BRAND_TEXT} !important;
            font-size: {t.FS_BODY} !important;
            font-weight: 500 !important;
            text-transform: none !important;
            letter-spacing: 0 !important;
        }}

        /* Brand na sidebar */
        .sidebar-brand {{
            padding: 0 0 0.25rem 0;
        }}
        .sidebar-brand-logo {{
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .sidebar-brand-mark {{
            background: {t.ACCENT};
            color: #FFFFFF;
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 0.8rem;
            font-weight: 700;
            padding: 0.35rem 0.55rem;
            letter-spacing: 0.1em;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
        }}
        .sidebar-brand-name {{
            color: #FFFFFF;
            font-size: 1.2rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .sidebar-brand-tag {{
            color: {t.BRAND_MUTED};
            font-size: {t.FS_MICRO};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin-top: 0.45rem;
            font-weight: 500;
        }}

        /* =====================================================
           STATUS INDICATORS — Compliance alerts
           ===================================================== */
        .alert-box {{
            padding: 0.95rem 1.1rem;
            border-radius: 10px;
            display: flex;
            align-items: center;
            gap: 0.85rem;
            font-size: {t.FS_SMALL};
            font-weight: 500;
            margin-bottom: 0.5rem;
            border: 1px solid;
        }}
        .alert-icon {{
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-family: {t.FONT_FAMILY_MONO};
            font-weight: 700;
            font-size: 0.75rem;
            flex-shrink: 0;
            color: #FFFFFF;
        }}
        .alert-green  {{ background: {t.POSITIVE_SOFT}; border-color: {t.POSITIVE_LINE}; color: #135E33; }}
        .alert-green .alert-icon {{ background: {t.POSITIVE}; }}
        .alert-yellow {{ background: {t.CAUTION_SOFT}; border-color: {t.CAUTION_LINE}; color: #7A3E00; }}
        .alert-yellow .alert-icon {{ background: {t.CAUTION}; }}
        .alert-red    {{ background: {t.NEGATIVE_SOFT}; border-color: {t.NEGATIVE_LINE}; color: #7F1D1D; }}
        .alert-red .alert-icon {{ background: {t.NEGATIVE}; }}

        /* =====================================================
           EWS — Early Warning System panel
           ===================================================== */
        .ews-panel {{
            background: {t.BG_CARD};
            border: 1px solid {t.BORDER};
            border-radius: 12px;
            padding: 1.25rem 1.4rem;
            box-shadow: {t.SHADOW_CARD};
            display: grid;
            grid-template-columns: auto 1fr auto;
            align-items: center;
            gap: 1.5rem;
            position: relative;
            overflow: hidden;
        }}
        .ews-panel::before {{
            content: "";
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 4px;
            background: {t.INK};
        }}
        .ews-panel.level-pos::before {{ background: {t.POSITIVE}; }}
        .ews-panel.level-cau::before {{ background: {t.CAUTION}; }}
        .ews-panel.level-neg::before {{ background: {t.NEGATIVE}; }}
        .ews-label {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .ews-level {{
            font-size: 1.15rem;
            font-weight: 700;
            color: {t.INK};
            letter-spacing: -0.01em;
        }}
        .ews-desc {{
            font-size: {t.FS_SMALL};
            color: {t.SLATE};
            line-height: 1.55;
        }}
        .ews-prob {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 2rem;
            font-weight: 600;
            color: {t.INK};
            letter-spacing: -0.03em;
            line-height: 1;
            font-feature-settings: "tnum" 1;
        }}

        /* =====================================================
           KEY-VALUE ROWS (pricing breakdown)
           ===================================================== */
        .kv-list {{
            display: flex;
            flex-direction: column;
        }}
        .kv-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            padding: 0.7rem 0;
            border-bottom: 1px solid {t.BORDER_SOFT};
            gap: 1rem;
        }}
        .kv-row:last-child {{ border-bottom: none; }}
        .kv-row.emphasis {{
            background: linear-gradient(90deg, rgba(37,99,235,0.04) 0%, transparent 100%);
            margin: 0.35rem -0.75rem 0 -0.75rem;
            padding: 0.85rem 0.75rem;
            border-radius: 6px;
            border-bottom: none;
        }}
        .kv-label {{ font-size: {t.FS_SMALL}; color: {t.SLATE}; font-weight: 500; }}
        .kv-row.emphasis .kv-label {{ color: {t.INK}; font-weight: 600; }}
        .kv-value {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: {t.FS_BODY};
            font-weight: 500;
            color: {t.INK};
            text-align: right;
            font-feature-settings: "tnum" 1;
            font-variant-numeric: tabular-nums;
        }}
        .kv-row.emphasis .kv-value {{ font-size: 1.05rem; font-weight: 600; color: {t.ACCENT}; }}
        .kv-sub {{ font-size: {t.FS_CAPTION}; color: {t.MUTED}; margin-left: 0.4rem; }}

        /* =====================================================
           RATING BADGE
           ===================================================== */
        .rating-chip {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 48px;
            padding: 0.35rem 0.7rem;
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 0.95rem;
            font-weight: 700;
            border-radius: 6px;
            letter-spacing: 0.02em;
            border: 1px solid;
        }}
        .rating-chip.rA  {{ background: {t.POSITIVE_SOFT}; color: {t.POSITIVE}; border-color: {t.POSITIVE_LINE}; }}
        .rating-chip.rAp {{ background: {t.PREMIUM_SOFT}; color: {t.PREMIUM_DARK}; border-color: #E3C477; }}
        .rating-chip.rB  {{ background: {t.ACCENT_SOFT}; color: {t.ACCENT}; border-color: {t.ACCENT_LINE}; }}
        .rating-chip.rC  {{ background: {t.CAUTION_SOFT}; color: {t.CAUTION}; border-color: {t.CAUTION_LINE}; }}
        .rating-chip.rD  {{ background: {t.NEGATIVE_SOFT}; color: {t.NEGATIVE}; border-color: {t.NEGATIVE_LINE}; }}

        /* Identidade do sacado */
        .sacado-head {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            padding: 1.1rem 1.4rem;
            background: {t.BG_CARD};
            border: 1px solid {t.BORDER};
            border-radius: 12px;
            box-shadow: {t.SHADOW_CARD};
            margin-bottom: 1rem;
        }}
        .sacado-cell {{
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }}
        .sacado-cell .kicker {{ margin: 0; }}
        .sacado-cell .val {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 1.05rem;
            font-weight: 600;
            color: {t.INK};
            letter-spacing: -0.01em;
        }}
        .sacado-cell.divider {{
            width: 1px;
            background: {t.BORDER};
            align-self: stretch;
        }}

        /* =====================================================
           BOTÕES
           ===================================================== */
        .stButton > button {{
            font-family: {t.FONT_FAMILY};
            font-weight: 500;
            font-size: {t.FS_SMALL};
            border-radius: 8px;
            border: 1px solid {t.BORDER};
            background: {t.BG_CARD};
            color: {t.INK};
            padding: 0.55rem 1.1rem;
            box-shadow: {t.SHADOW_CARD};
            transition: all 0.15s ease;
        }}
        .stButton > button:hover {{
            border-color: {t.INK};
            background: {t.BG_CARD};
            transform: translateY(-1px);
            box-shadow: {t.SHADOW_HOVER};
        }}
        .stButton > button[kind="primary"] {{
            background: {t.ACCENT};
            color: #FFFFFF;
            border-color: {t.ACCENT};
            font-weight: 600;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
        }}
        .stButton > button[kind="primary"]:hover {{
            background: {t.ACCENT_DARK};
            border-color: {t.ACCENT_DARK};
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.45);
        }}
        .stButton > button[kind="primary"]:disabled {{
            background: {t.BG_SOFT};
            color: {t.MUTED};
            border-color: {t.BORDER};
            box-shadow: none;
            transform: none;
        }}
        .stDownloadButton > button {{
            font-family: {t.FONT_FAMILY};
            font-weight: 500;
            font-size: {t.FS_SMALL};
            border-radius: 8px;
            border: 1px solid {t.BORDER};
            background: {t.BG_CARD};
            color: {t.INK};
            box-shadow: {t.SHADOW_CARD};
        }}
        .stDownloadButton > button:hover {{
            border-color: {t.ACCENT};
            box-shadow: {t.SHADOW_HOVER};
        }}

        /* =====================================================
           INPUTS (área principal)
           ===================================================== */
        .stTextInput input,
        .stNumberInput input,
        .stDateInput input {{
            border: 1px solid {t.BORDER} !important;
            border-radius: 8px !important;
            font-size: {t.FS_SMALL} !important;
            padding: 0.55rem 0.8rem !important;
            height: 42px !important;
            color: {t.INK} !important;
            background: {t.BG_CARD} !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }}
        .stTextInput input::placeholder,
        .stNumberInput input::placeholder,
        .stDateInput input::placeholder {{
            color: {t.MUTED} !important;
            opacity: 1 !important;
        }}
        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus {{
            border-color: {t.ACCENT} !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
            outline: none;
        }}

        /* Wrapper BaseWeb de cada input — alinha altura e remove bordas
           internas duplicadas que causavam "linha fantasma" em alguns navegadores. */
        .stTextInput div[data-baseweb="input"],
        .stNumberInput div[data-baseweb="input"],
        .stDateInput div[data-baseweb="input"] {{
            border: none !important;
            background: transparent !important;
            border-radius: 8px !important;
        }}

        /* -----------------------------------------------------
           NUMBER INPUT — botões de +/- (step up / step down)
           ----------------------------------------------------- */
        .stNumberInput [data-testid="stNumberInputContainer"] {{
            border-radius: 8px !important;
            overflow: hidden;
        }}
        .stNumberInput button[data-testid="stNumberInputStepUp"],
        .stNumberInput button[data-testid="stNumberInputStepDown"],
        .stNumberInput button[aria-label="Step up"],
        .stNumberInput button[aria-label="Step down"],
        .stNumberInput [data-baseweb="input"] button {{
            background: #475569 !important;
            border: 1px solid #334155 !important;
            color: #FFFFFF !important;
            width: 32px !important;
            min-width: 32px !important;
            height: 42px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            border-radius: 6px !important;
            margin-left: 4px !important;
            transition: all 0.15s ease;
            cursor: pointer !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }}
        .stNumberInput button[data-testid="stNumberInputStepUp"]:hover,
        .stNumberInput button[data-testid="stNumberInputStepDown"]:hover,
        .stNumberInput [data-baseweb="input"] button:hover {{
            background: {t.ACCENT} !important;
            color: #FFFFFF !important;
            border-color: {t.ACCENT} !important;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35) !important;
        }}
        .stNumberInput button[data-testid="stNumberInputStepUp"] svg,
        .stNumberInput button[data-testid="stNumberInputStepDown"] svg,
        .stNumberInput [data-baseweb="input"] button svg {{
            width: 16px !important;
            height: 16px !important;
            fill: #FFFFFF !important;
            color: #FFFFFF !important;
            stroke: #FFFFFF !important;
            stroke-width: 1 !important;
            opacity: 1 !important;
        }}

        /* -----------------------------------------------------
           DATE INPUT — ícone de calendário + botão "clear value"
           ----------------------------------------------------- */
        .stDateInput [data-baseweb="input"] {{
            align-items: center;
        }}
        .stDateInput [data-baseweb="input"] button {{
            background: transparent !important;
            border: none !important;
            color: {t.MUTED} !important;
            padding: 0 0.35rem !important;
            height: 42px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            transition: color 0.15s ease, background 0.15s ease;
            border-radius: 6px !important;
        }}
        .stDateInput [data-baseweb="input"] button:hover {{
            color: {t.ACCENT} !important;
            background: rgba(37, 99, 235, 0.08) !important;
        }}
        .stDateInput [data-baseweb="input"] button svg {{
            width: 16px !important;
            height: 16px !important;
            fill: currentColor !important;
        }}
        /* Calendário popup */
        [data-baseweb="calendar"] {{
            border-radius: 10px !important;
            border: 1px solid {t.BORDER} !important;
            box-shadow: 0 10px 40px -10px rgba(10, 22, 40, 0.25) !important;
            font-family: {t.FONT_FAMILY} !important;
        }}

        /* -----------------------------------------------------
           TEXT INPUT — senha: ícone do olho (show/hide)
           ----------------------------------------------------- */
        .stTextInput [data-baseweb="input"] button {{
            background: transparent !important;
            border: none !important;
            color: {t.MUTED} !important;
            padding: 0 0.5rem !important;
            height: 42px !important;
            cursor: pointer !important;
            transition: color 0.15s ease;
            border-radius: 6px !important;
        }}
        .stTextInput [data-baseweb="input"] button:hover {{
            color: {t.ACCENT} !important;
            background: rgba(37, 99, 235, 0.08) !important;
        }}
        .stTextInput [data-baseweb="input"] button svg {{
            width: 18px !important;
            height: 18px !important;
            fill: currentColor !important;
        }}

        /* Labels dos inputs — maior hierarquia visual */
        .stTextInput label,
        .stNumberInput label,
        .stDateInput label {{
            font-size: {t.FS_CAPTION} !important;
            color: {t.SLATE} !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
            margin-bottom: 0.4rem !important;
        }}

        /* =====================================================
           TABS
           ===================================================== */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0;
            border-bottom: 1px solid {t.BORDER};
            background: transparent;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            color: {t.SLATE};
            border: none;
            border-bottom: 3px solid transparent;
            border-radius: 0;
            font-weight: 500;
            font-size: {t.FS_SMALL};
            padding: 0.8rem 1.25rem;
            margin-bottom: -1px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {t.ACCENT} !important;
            border-bottom: 3px solid {t.ACCENT} !important;
            font-weight: 700;
        }}

        /* =====================================================
           PROGRESS
           ===================================================== */
        .stProgress > div > div {{
            background-color: {t.BG_SOFT};
            border-radius: 4px;
            height: 8px;
        }}
        .stProgress > div > div > div > div {{
            background: linear-gradient(90deg, {t.ACCENT} 0%, {t.PREMIUM} 100%);
            border-radius: 4px;
        }}

        /* =====================================================
           DATAFRAME
           ===================================================== */
        [data-testid="stDataFrame"] {{
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid {t.BORDER};
            box-shadow: {t.SHADOW_CARD};
        }}
        [data-testid="stDataFrame"] thead tr th {{
            background: {t.BG_SUBTLE} !important;
            color: {t.MUTED} !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            font-size: {t.FS_MICRO} !important;
            letter-spacing: 0.12em;
            border-bottom: 1px solid {t.BORDER} !important;
        }}

        /* =====================================================
           ALERTS / EXPANDERS / DIVIDERS
           ===================================================== */
        div[data-testid="stAlert"] {{
            border-radius: 10px;
            border: 1px solid {t.BORDER};
            background: {t.BG_CARD};
            box-shadow: {t.SHADOW_CARD};
            padding: 0.85rem 1rem;
            font-size: {t.FS_SMALL};
        }}
        [data-testid="stExpander"] {{
            border: 1px solid {t.BORDER};
            border-radius: 12px;
            background: {t.BG_CARD};
            box-shadow: {t.SHADOW_CARD};
        }}
        [data-testid="stExpander"] summary {{
            font-weight: 600;
            color: {t.INK};
            font-size: {t.FS_SMALL};
            padding: 1rem 1.25rem;
        }}
        .section-divider {{
            height: 1px;
            background: {t.BORDER};
            margin: 2rem 0 1.5rem 0;
            border: none;
        }}

        /* =====================================================
           CALLOUT
           ===================================================== */
        .callout {{
            padding: 0.95rem 1.15rem;
            background: {t.ACCENT_SOFT};
            border-left: 3px solid {t.ACCENT};
            border-radius: 0 8px 8px 0;
            font-size: {t.FS_SMALL};
            color: {t.INK};
            margin: 1rem 0;
            line-height: 1.55;
        }}
        .callout.tip {{ background: {t.PREMIUM_SOFT}; border-left-color: {t.PREMIUM}; }}
        .callout.warning  {{ background: {t.CAUTION_SOFT};  border-left-color: {t.CAUTION};   color: #7A3E00; }}
        .callout.alerta   {{ background: {t.CAUTION_SOFT};  border-left-color: {t.CAUTION};   color: #7A3E00; }}
        .callout.critico  {{ background: {t.NEGATIVE_SOFT}; border-left-color: {t.NEGATIVE};  color: #7F1D1D; }}
        .callout.destaque {{ background: {t.POSITIVE_SOFT}; border-left-color: {t.POSITIVE};  color: #14532D; }}
        .callout.success  {{ background: {t.POSITIVE_SOFT}; border-left-color: {t.POSITIVE};  color: #14532D; }}

        /* =====================================================
           FILTER WORKSPACE — presets, chips, results bar
           ===================================================== */

        /* st.container(border=True) — herda visual de card */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border: 1px solid {t.BORDER} !important;
            border-radius: 12px !important;
            background: {t.BG_CARD};
            box-shadow: {t.SHADOW_CARD};
            padding: 1rem 1.25rem 0.6rem 1.25rem !important;
            margin-bottom: 0.9rem;
        }}

        /* Kicker que fica ACIMA do container (fora do card) */
        .filter-kicker,
        .preset-kicker {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 700;
            margin: 0.4rem 0 0.4rem 0.1rem;
            display: flex;
            align-items: center;
            gap: 0.55rem;
        }}
        .filter-kicker::before,
        .preset-kicker::before {{
            content: "";
            width: 18px;
            height: 2px;
            background: {t.ACCENT};
            display: inline-block;
        }}
        .filter-kicker-count {{
            margin-left: auto;
            background: {t.ACCENT_SOFT};
            color: {t.ACCENT_DARK};
            border: 1px solid {t.ACCENT_LINE};
            padding: 0.1rem 0.55rem;
            border-radius: 999px;
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: none;
        }}

        /* Sub-sections dentro do workspace de filtros */
        .filter-subsection-label {{
            font-size: {t.FS_SMALL};
            color: {t.INK};
            font-weight: 700;
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.55rem;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid {t.BORDER_SOFT};
        }}
        .filter-subsection-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 5px;
            background: {t.ACCENT_SOFT};
            color: {t.ACCENT_DARK};
            font-size: 0.78rem;
            font-weight: 800;
            font-family: {t.FONT_FAMILY_MONO};
        }}
        .filter-subsection-icon.premium {{ background: {t.PREMIUM_SOFT}; color: {t.PREMIUM_DARK}; }}
        .filter-subsection-icon.pos {{ background: {t.POSITIVE_SOFT}; color: {t.POSITIVE}; }}

        /* Barra de chips de filtros ativos */
        .chipbar {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            background: {t.BG_SUBTLE};
            border: 1px dashed {t.BORDER_STRONG};
            border-radius: 10px;
            margin-bottom: 1rem;
        }}
        .chipbar-label {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 700;
            margin-right: 0.25rem;
        }}
        .chip-active {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: {t.ACCENT_SOFT};
            border: 1px solid {t.ACCENT_LINE};
            color: {t.ACCENT_DARK};
            padding: 0.3rem 0.75rem;
            border-radius: 999px;
            font-size: 0.81rem;
            font-weight: 500;
        }}
        .chip-active .chip-key {{
            color: {t.INK};
            font-weight: 700;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            padding-right: 0.45rem;
            border-right: 1px solid {t.ACCENT_LINE};
        }}
        .chip-active .chip-val {{
            font-family: {t.FONT_FAMILY_MONO};
            color: {t.ACCENT_DARK};
            letter-spacing: -0.01em;
        }}
        .chip-empty {{
            color: {t.MUTED};
            font-size: {t.FS_SMALL};
            font-style: italic;
        }}

        /* Results bar — gradiente navy com número grande */
        .results-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.15rem 1.6rem;
            background: linear-gradient(90deg, {t.BRAND_900} 0%, {t.BRAND_800} 55%, #1A3161 100%);
            color: {t.BRAND_TEXT};
            border-radius: 12px;
            margin-bottom: 1.25rem;
            box-shadow: {t.SHADOW_CARD};
            position: relative;
            overflow: hidden;
        }}
        .results-bar::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 12% 50%, rgba(37, 99, 235, 0.22) 0%, transparent 45%);
            pointer-events: none;
        }}
        .results-bar > div {{
            position: relative;
            z-index: 1;
        }}
        .results-bar-label {{
            font-size: {t.FS_MICRO};
            color: rgba(229, 236, 247, 0.55);
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }}
        .results-bar-numberline {{
            display: flex;
            align-items: baseline;
            gap: 0.85rem;
        }}
        .results-bar-count {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 1.95rem;
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: -0.025em;
            line-height: 1;
            font-feature-settings: "tnum" 1;
        }}
        .results-bar-total {{
            font-size: {t.FS_SMALL};
            color: rgba(229, 236, 247, 0.65);
        }}
        .results-bar-pct {{
            background: rgba(37, 99, 235, 0.25);
            border: 1px solid rgba(147, 197, 253, 0.35);
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 0.78rem;
            color: #BFD7FE;
            font-weight: 600;
        }}
        .results-bar-right {{
            text-align: right;
        }}
        .results-bar-vol {{
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 1.4rem;
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: -0.02em;
            line-height: 1;
        }}

        /* Delta indicator (KPI cards na view de filtros) */
        .kpi-delta {{
            display: inline-flex;
            align-items: center;
            gap: 0.15rem;
            font-size: 0.72rem;
            font-family: {t.FONT_FAMILY_MONO};
            font-weight: 700;
            padding: 0.08rem 0.4rem;
            border-radius: 4px;
            margin-left: 0.35rem;
            letter-spacing: -0.01em;
        }}
        .kpi-delta.up   {{ background: {t.POSITIVE_SOFT}; color: {t.POSITIVE}; }}
        .kpi-delta.down {{ background: {t.NEGATIVE_SOFT}; color: {t.NEGATIVE}; }}
        .kpi-delta.flat {{ background: {t.BG_SOFT};       color: {t.MUTED}; }}

        /* =====================================================
           FILTER CARDS (v3 stack)
           ===================================================== */
        .fcard-head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.6rem;
            padding-bottom: 0.55rem;
            border-bottom: 1px solid {t.BORDER_SOFT};
        }}
        .fcard-head-left {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}
        .fcard-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 26px; height: 26px;
            border-radius: 7px;
            background: {t.ACCENT_SOFT};
            color: {t.ACCENT_DARK};
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 0.82rem;
            font-weight: 800;
        }}
        .fcard-icon.premium {{ background: {t.PREMIUM_SOFT}; color: {t.PREMIUM_DARK}; }}
        .fcard-icon.pos     {{ background: {t.POSITIVE_SOFT}; color: {t.POSITIVE}; }}
        .fcard-icon.ink     {{ background: {t.BG_SOFT};      color: {t.INK}; }}
        .fcard-title-block {{
            display: flex;
            flex-direction: column;
            gap: 0.08rem;
        }}
        .fcard-kicker {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 700;
            line-height: 1;
        }}
        .fcard-title {{
            font-size: {t.FS_BODY};
            color: {t.INK};
            font-weight: 700;
            letter-spacing: -0.01em;
            line-height: 1.15;
        }}
        .fcard-badge {{
            background: {t.ACCENT_SOFT};
            border: 1px solid {t.ACCENT_LINE};
            color: {t.ACCENT_DARK};
            padding: 0.18rem 0.6rem;
            border-radius: 999px;
            font-family: {t.FONT_FAMILY_MONO};
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }}
        .fcard-badge.muted {{
            background: {t.BG_SOFT};
            border-color: {t.BORDER};
            color: {t.MUTED};
        }}
        .fcard-hint {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            margin-top: 0.35rem;
            font-family: {t.FONT_FAMILY_MONO};
            letter-spacing: -0.01em;
        }}
        .fcard-mini-label {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 600;
            margin: 0.45rem 0 0.15rem 0;
        }}

        /* Região — botões compactos de atalho */
        .region-row-label {{
            font-size: {t.FS_MICRO};
            color: {t.MUTED};
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 600;
            margin: 0.2rem 0 0.35rem 0;
        }}

        /* =====================================================
           SECTION LABELS (inline)
           ===================================================== */
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin: 0 0 1rem 0;
            padding-bottom: 0.6rem;
            border-bottom: 1px solid {t.BORDER};
        }}
        .section-header .title {{
            font-size: {t.FS_H3};
            font-weight: 700;
            color: {t.INK};
            letter-spacing: -0.02em;
        }}
        .section-header .sub {{
            font-size: {t.FS_SMALL};
            color: {t.SLATE};
            margin-top: 0.2rem;
        }}
        /* =====================================================
           NAVEGAÇÃO SIDEBAR — botões por grupo
           ===================================================== */
        .nav-group-label {{
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: {t.MUTED};
            margin: 14px 0 4px 2px;
            padding: 0;
            display: block;
        }}
        .nav-btn button {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
            color: {t.INK} !important;
            font-size: {t.FS_SMALL} !important;
            font-weight: 400 !important;
            padding: 5px 8px !important;
            border-radius: 5px !important;
            height: auto !important;
            line-height: 1.5 !important;
            transition: background .12s, color .12s !important;
        }}
        .nav-btn button:hover {{
            background: {t.BG_SOFT} !important;
        }}
        .nav-btn-ativo button {{
            background: {t.ACCENT_SOFT} !important;
            color: {t.ACCENT} !important;
            font-weight: 500 !important;
        }}
        .nav-btn-ativo button:hover {{
            background: {t.ACCENT_SOFT} !important;
        }}

        /* =====================================================
           CLASSES UTILITÁRIAS DE TIPOGRAFIA
           Usam a escala do theme para garantir consistência
           entre inline styles e o CSS global.
           ===================================================== */
        .t-micro   {{ font-size: {t.FS_MICRO};   line-height: 1.4; }}
        .t-caption {{ font-size: {t.FS_CAPTION}; line-height: 1.5; }}
        .t-small   {{ font-size: {t.FS_SMALL};   line-height: 1.55; }}
        .t-body    {{ font-size: {t.FS_BODY};     line-height: 1.65; }}
        .t-lead    {{ font-size: {t.FS_LEAD};     line-height: 1.5; }}
        .t-h3      {{ font-size: {t.FS_H3};       font-weight: 500; line-height: 1.35; }}
        .t-h2      {{ font-size: {t.FS_H2};       font-weight: 400; line-height: 1.25; }}

        .t-ink     {{ color: {t.INK}; }}
        .t-slate   {{ color: {t.SLATE}; }}
        .t-muted   {{ color: {t.MUTED}; }}
        .t-accent  {{ color: {t.ACCENT}; }}
        .t-500     {{ font-weight: 500; }}
        .t-upper   {{ text-transform: uppercase; letter-spacing: 0.07em; }}

        /* Briefing panel — macro_view */
        .briefing-icon    {{ font-size: 1.25rem; line-height: 1; margin-top: 2px; }}
        .briefing-title   {{ font-size: {t.FS_BODY}; font-weight: 500; margin-bottom: 3px; }}
        .briefing-body    {{ font-size: {t.FS_SMALL}; line-height: 1.6; color: {t.SLATE}; }}
        .briefing-label   {{ font-size: {t.FS_MICRO}; font-weight: 600; letter-spacing: 0.07em;
                             text-transform: uppercase; opacity: 0.6; margin-bottom: 4px; }}
        .briefing-step    {{ font-size: {t.FS_SMALL}; margin-top: 4px; }}

        /* Cards de filtro — filters_view */
        .filter-label {{ font-size: {t.FS_MICRO}; font-weight: 600; letter-spacing: 0.08em;
                          text-transform: uppercase; color: {t.MUTED}; margin-bottom: 0.35rem; }}
        .filter-hint  {{ font-size: {t.FS_CAPTION}; line-height: 1.4;
                          color: {t.SLATE}; margin-bottom: 0.6rem; }}


        /* =====================================================
           DATA VERSE — IDENTIDADE VISUAL
           ===================================================== */

        /* Linha de acento ciana no topo da sidebar */
        section[data-testid="stSidebar"] {{
            background: {t.BRAND_900} !important;
            border-right: 1px solid rgba(0,188,212,.15) !important;
        }}
        section[data-testid="stSidebar"]::before {{
            content: '';
            display: block;
            height: 3px;
            background: linear-gradient(90deg, #00BCD4 0%, #7C3AED 100%);
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        /* Fundo do app com textura sutil */
        .stApp {{
            background: #F8FAFC !important;
            background-image: radial-gradient(circle at 20% 50%, rgba(0,188,212,.03) 0%, transparent 50%),
                              radial-gradient(circle at 80% 20%, rgba(124,58,237,.03) 0%, transparent 50%) !important;
        }}

        /* Botão primário — gradiente Data Verse */
        .stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {{
            background: linear-gradient(135deg, #0891B2 0%, #7C3AED 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 500 !important;
            letter-spacing: 0.01em !important;
            box-shadow: 0 2px 8px rgba(8,145,178,.25) !important;
            transition: all .15s ease !important;
        }}
        .stButton > button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover {{
            box-shadow: 0 4px 16px rgba(8,145,178,.35) !important;
            transform: translateY(-1px) !important;
        }}

        /* Botão secundário */
        .stButton > button[kind="secondary"],
        button[data-testid="baseButton-secondary"] {{
            background: transparent !important;
            border: 1.5px solid #E2E8F0 !important;
            color: {t.INK} !important;
            font-weight: 400 !important;
            transition: all .12s ease !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            border-color: #00BCD4 !important;
            color: #0891B2 !important;
        }}

        /* Cards / containers com borda sutil */
        div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] > div[data-testid="stVerticalBlock"] {{
            border-radius: 10px;
        }}

        /* Abas — estilo Data Verse */
        .stTabs [data-baseweb="tab-list"] {{
            background: transparent !important;
            border-bottom: 2px solid #E2E8F0 !important;
            gap: 0 !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            color: {t.SLATE} !important;
            padding: 8px 20px !important;
            border-bottom: 2px solid transparent !important;
            margin-bottom: -2px !important;
            background: transparent !important;
            transition: color .12s, border-color .12s !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: #0891B2 !important;
        }}
        .stTabs [aria-selected="true"][data-baseweb="tab"] {{
            color: #0891B2 !important;
            border-bottom-color: #00BCD4 !important;
            background: transparent !important;
        }}

        /* Métricas — mais limpas */
        div[data-testid="stMetric"] {{
            background: white !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            padding: 14px 16px !important;
        }}
        div[data-testid="stMetric"] label {{
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            letter-spacing: .07em !important;
            text-transform: uppercase !important;
            color: {t.MUTED} !important;
        }}
        div[data-testid="stMetricValue"] {{
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            color: {t.INK} !important;
            letter-spacing: -.02em !important;
        }}
        div[data-testid="stMetricDelta"] {{
            font-size: 0.78rem !important;
        }}
        div[data-testid="stMetricDelta"] svg {{
            width: 12px !important;
            height: 12px !important;
        }}

        /* Expander — mais sutil */
        details[data-testid="stExpander"] {{
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            background: white !important;
            box-shadow: none !important;
        }}
        details[data-testid="stExpander"] summary {{
            font-size: 0.83rem !important;
            font-weight: 500 !important;
            color: {t.SLATE} !important;
            padding: 10px 14px !important;
        }}
        details[data-testid="stExpander"] summary:hover {{
            color: #0891B2 !important;
        }}

        /* Inputs */
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input {{
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 6px !important;
            font-size: 0.88rem !important;
            transition: border-color .12s !important;
        }}
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus {{
            border-color: #00BCD4 !important;
            box-shadow: 0 0 0 3px rgba(0,188,212,.12) !important;
        }}

        /* Download button */
        .stDownloadButton > button {{
            background: white !important;
            border: 1.5px solid #E2E8F0 !important;
            color: {t.INK} !important;
            font-weight: 500 !important;
            transition: all .12s !important;
        }}
        .stDownloadButton > button:hover {{
            border-color: #00BCD4 !important;
            color: #0891B2 !important;
        }}

        /* Divisor sutil */
        hr {{
            border: none !important;
            border-top: 1px solid #F1F5F9 !important;
            margin: 1.5rem 0 !important;
        }}

        /* Alert / info boxes do Streamlit */
        div[data-testid="stAlert"] {{
            border-radius: 8px !important;
            border-left-width: 3px !important;
        }}

        /* Forms */
        div[data-testid="stForm"] {{
            background: white !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 10px !important;
            padding: 1.25rem 1.5rem !important;
        }}

        /* Scrollbar */
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: #CBD5E1; border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #00BCD4; }}

        /* Botão Carregar do home — forçar gradiente Data Verse */
        div[data-testid="stButton"] button[kind="primary"],
        div[data-testid="stButton"] button[data-testid="baseButton-primary"] {{
            background: linear-gradient(135deg, #0891B2 0%, #7C3AED 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 500 !important;
            box-shadow: 0 2px 8px rgba(8,145,178,.25) !important;
        }}

        /* File uploader — botão com gradiente Data Verse */
        div[data-testid="stFileUploader"] button,
        div[data-testid="stFileUploaderDropzone"] button {{
            background: linear-gradient(135deg, #0891B2 0%, #7C3AED 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 500 !important;
            box-shadow: 0 2px 8px rgba(8,145,178,.25) !important;
            transition: all .15s ease !important;
        }}
        div[data-testid="stFileUploader"] button:hover,
        div[data-testid="stFileUploaderDropzone"] button:hover {{
            box-shadow: 0 4px 16px rgba(8,145,178,.35) !important;
            transform: translateY(-1px) !important;
        }}
        div[data-testid="stFileUploaderDropzone"] {{
            border: 1.5px dashed #CBD5E1 !important;
            border-radius: 10px !important;
            background: white !important;
            transition: border-color .15s !important;
        }}
        div[data-testid="stFileUploaderDropzone"]:hover {{
            border-color: #00BCD4 !important;
        }}

        /* Marca d'água Data Verse no fundo — sutil */
        .stApp::after {{
            content: '';
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 80px;
            height: 80px;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32' fill='none'%3E%3Cpath d='M4 4 L16 28 L28 4' stroke='%2300BCD4' stroke-width='3' stroke-linecap='round' stroke-linejoin='round' fill='none' opacity='0.08'/%3E%3Cpath d='M4 4 L16 28' stroke='%237C3AED' stroke-width='3' stroke-linecap='round' fill='none' opacity='0.08'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-size: contain;
            pointer-events: none;
            z-index: 0;
        }}

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
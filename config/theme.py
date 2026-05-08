"""
Sistema de Design v3 · Executive Dashboard.

Inspiração: Ramp · Mercury · Attio · Databricks · Linear Pro.
Sidebar escura com peso institucional + área principal clara com cards
que respiram. Impacto visual à distância (banca/projetor), densidade
sem poluição, uma cor-acento viva + dourado premium como secundário.
"""

# =============================================================================
# BRAND — Sidebar escura (o "navio-almirante")
# =============================================================================
BRAND_900   = "#0A1A33"   # Sidebar background
BRAND_800   = "#0F2142"   # Hover / card dentro da sidebar
BRAND_700   = "#162B52"   # Borders internas da sidebar
BRAND_LINE  = "#1F3763"   # Divisores dentro da sidebar
BRAND_TEXT  = "#E5ECF7"   # Texto principal na sidebar
BRAND_MUTED = "#7C8CA8"   # Texto secundário na sidebar

# =============================================================================
# NEUTROS — Área clara (main)
# =============================================================================
BG_APP     = "#F8FAFC"    # Data Verse — off-white sofisticado
BG_CARD    = "#FFFFFF"    # Fundo dos cards
BG_SUBTLE  = "#F9FAFC"    # Zonas alternadas
BG_SOFT    = "#EEF1F6"    # Zonas secundárias

INK        = "#0F172A"    # Texto primário
GRAPHITE   = "#1E293B"    # Headings fortes
SLATE      = "#475569"    # Texto secundário
MUTED      = "#94A3B8"    # Captions, labels
MUTED_SOFT = "#CBD5E1"    # Linhas de apoio

BORDER        = "#E2E8F0" # Bordas de cards
BORDER_SOFT   = "#EEF2F7" # Divisores internos
BORDER_STRONG = "#CBD5E1" # Bordas em foco

# =============================================================================
# ACENTOS — cor viva primária + dourado premium
# =============================================================================
ACCENT       = "#0891B2"    # Data Verse Cyan — cor primária da marca
ACCENT_DARK  = "#0E7490"    # Data Verse Cyan escuro — hover
ACCENT_SOFT  = "#CFFAFE"    # Data Verse Cyan soft
ACCENT_LINE  = "#67E8F9"    # Data Verse Cyan line

# Data Verse — cores da marca
DV_CYAN        = "#00BCD4"    # Ciano do V — identidade principal
DV_PURPLE      = "#7C3AED"    # Roxo do V — identidade secundária
DV_CYAN_SOFT   = "#E0F7FA"    # Fundo ciano suave
DV_PURPLE_SOFT = "#EDE9FE"    # Fundo roxo suave
DV_GRADIENT    = "linear-gradient(135deg, #00BCD4 0%, #7C3AED 100%)"


PREMIUM      = "#C8953A"    # Dourado refinado — ratings A+/A e rótulos premium
PREMIUM_SOFT = "#FBF3E0"    # Fundo dourado suave para badges A
PREMIUM_DARK = "#9C7220"    # Text premium em background claro

# =============================================================================
# SEMÂNTICOS — status
# =============================================================================
POSITIVE      = "#0F9D58"
POSITIVE_SOFT = "#E6F4EA"
POSITIVE_LINE = "#81C995"

CAUTION       = "#E37400"
CAUTION_SOFT  = "#FEF1E1"
CAUTION_LINE  = "#F6B26B"

NEGATIVE      = "#D93025"
NEGATIVE_SOFT = "#FCE8E6"
NEGATIVE_LINE = "#F28B82"

INFO          = "#1A73E8"
INFO_SOFT     = "#E3F0FD"

# =============================================================================
# ALIASES — compatibilidade com código/módulos legados
# =============================================================================
NAVY_900 = BRAND_900
NAVY_800 = BRAND_800
NAVY_700 = BRAND_700
NAVY_600 = BRAND_TEXT
NAVY_500 = BRAND_MUTED
GOLD_500 = PREMIUM
GOLD_600 = PREMIUM_DARK
GOLD_400 = "#E3C477"
SUCCESS_500 = POSITIVE
SUCCESS_BG = POSITIVE_SOFT
SUCCESS_BORDER = POSITIVE_LINE
WARNING_500 = CAUTION
WARNING_BG = CAUTION_SOFT
WARNING_BORDER = CAUTION_LINE
DANGER_500 = NEGATIVE
DANGER_BG = NEGATIVE_SOFT
DANGER_BORDER = NEGATIVE_LINE
INFO_500 = INFO
INFO_BG = INFO_SOFT
BG_SUBTLE_LEGACY = BG_SOFT
BORDER_LIGHT = BORDER
BORDER_MEDIUM = BORDER_STRONG
TEXT_PRIMARY = INK
TEXT_SECONDARY = SLATE
TEXT_MUTED = MUTED
PAPER = BG_CARD
SURFACE = BG_APP
HAIRLINE = BORDER
LINE_SOFT = BORDER_SOFT

# =============================================================================
# TIPOGRAFIA
# =============================================================================
FONT_FAMILY = (
    "'DM Sans',"
    "'Inter',"
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Roboto, 'Helvetica Neue', Arial, sans-serif"
)
FONT_FAMILY_MONO = (
    "'JetBrains Mono', 'SF Mono', 'Roboto Mono', Consolas, monospace"
)

FS_MICRO   = "0.688rem"   # 11px
FS_CAPTION = "0.75rem"    # 12px
FS_SMALL   = "0.813rem"   # 13px
FS_BODY    = "0.938rem"   # 15px
FS_LEAD    = "1.125rem"   # 18px
FS_H3      = "1.375rem"   # 22px
FS_H2      = "1.75rem"    # 28px
FS_H1      = "2.5rem"     # 40px
FS_HERO    = "3.5rem"     # 56px

# =============================================================================
# SHADOWS
# =============================================================================
SHADOW_CARD    = "0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)"
SHADOW_HOVER   = "0 4px 12px rgba(15, 23, 42, 0.08), 0 2px 4px rgba(15, 23, 42, 0.06)"
SHADOW_HERO    = "0 10px 40px rgba(10, 26, 51, 0.15), 0 4px 12px rgba(10, 26, 51, 0.08)"

# =============================================================================
# PLOTLY TEMPLATE
# =============================================================================
PLOTLY_TEMPLATE = {
    "layout": {
        "font": {"family": FONT_FAMILY, "color": INK, "size": 13},
        "paper_bgcolor": BG_CARD,
        "plot_bgcolor": BG_CARD,
        "colorway": [ACCENT, PREMIUM, POSITIVE, INK, SLATE, CAUTION],
        "xaxis": {
            "gridcolor": BORDER_SOFT,
            "linecolor": BORDER,
            "tickcolor": BORDER,
            "zerolinecolor": BORDER,
            "title": {"font": {"size": 12, "color": SLATE}},
            "tickfont": {"size": 11, "color": SLATE},
        },
        "yaxis": {
            "gridcolor": BORDER_SOFT,
            "linecolor": BORDER,
            "tickcolor": BORDER,
            "zerolinecolor": BORDER,
            "title": {"font": {"size": 12, "color": SLATE}},
            "tickfont": {"size": 11, "color": SLATE},
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": "rgba(0,0,0,0)",
            "font": {"size": 11, "color": SLATE},
        },
        "margin": {"l": 56, "r": 24, "t": 30, "b": 40},
    }
}

# =============================================================================
# VELOCÍMETRO — faixas com saturação controlada
# =============================================================================
GAUGE_STEPS = [
    {"range": [0,   599], "color": "#FCE8E6"},
    {"range": [600, 699], "color": "#FEF1E1"},
    {"range": [700, 799], "color": "#FEF9C3"},
    {"range": [800, 899], "color": "#E6F4EA"},
    {"range": [900, 1000], "color": "#D4F1D8"},
]

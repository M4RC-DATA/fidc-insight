"""
View · Valoração Total da Carteira · FIDC Insight.

Responde: "O que este portfólio vale hoje, ajustado ao risco?"

Metodologia RAROC sacado a sacado consolidada:
  - Cada sacado recebe taxa = Selic + prêmio do seu rating
  - VP = face / (1 + taxa)^prazo_anos   [prazo ajustado individualmente]
  - ECL = face × PD × prazo_anos × LGD  [IFRS 9 lifetime ECL simplificado]
  - Lucro RAROC = (face - VP) - ECL

Limitação documentada: quando a base consolidada não traz prazo individual
de vencimento por boleto, usa-se o prazo do fundo como proxy. Isso tende
a superestimar o prazo dos boletos curtos (30-90 dias) e, portanto,
superestimar a ECL e subavalorizar ligeiramente o VP. A carteira real tem
prazo médio menor que o prazo do fundo.
"""

from datetime import date, datetime
import io

import numpy as np
import pandas as pd
import streamlit as st

from config.business_rules import (
    CLASSIFICACOES, LGD_PADRAO, LIMITE_POR_SACADO, LIMITE_POR_UF, ORDEM_RATINGS,
)
from domain.risk import hhi_por_uf
from services.bcb_api import buscar_selic
from ui.components import (
    render_callout, render_hero_panel, render_kpi_row,
    render_page_header, render_section_header, section_divider,
)
from utils.formatters import formatar_moeda, formatar_numero, formatar_percentual, id_curto


# ---------------------------------------------------------------------------
# Mapeamento rating → (prêmio, PD) — espelha business_rules.CLASSIFICACOES
# ---------------------------------------------------------------------------
_RATING_PARAMS: dict[str, tuple[float, float]] = {
    clf[2]: (clf[3], clf[4]) for clf in CLASSIFICACOES
}
_RATING_FALLBACK = (0.32, 0.120)  # rating D


def _params(rating: str) -> tuple[float, float]:
    return _RATING_PARAMS.get(rating, _RATING_FALLBACK)


# ---------------------------------------------------------------------------
# Veredicto narrativo
# ---------------------------------------------------------------------------
def _veredicto(margem: float, ecl_share: float, hhi: float) -> tuple[str, str, str]:
    ok = sum([margem >= 15, ecl_share < 5, hhi < 0.15])
    if ok == 3:
        return (
            "Portfólio bem precificado — retorno adequado ao risco",
            f"Margem real {margem:.1f}%, ECL {ecl_share:.1f}% da face, "
            f"HHI {hhi:.3f} (diversificado).",
            "destaque",
        )
    if ok >= 2:
        return (
            "Portfólio estável com pontos de atenção",
            f"Margem {margem:.1f}%, ECL {ecl_share:.1f}%, HHI {hhi:.3f}. "
            "Monitore o indicador fora do limiar.",
            "info",
        )
    return (
        "Margem real baixa — revisar composição ou premissas de taxas",
        f"Margem {margem:.1f}% após ECL de {ecl_share:.1f}%. "
        "Use o breakdown por rating para identificar onde o spread está comprimido.",
        "alerta",
    )


# ---------------------------------------------------------------------------
# Precificação vetorizada de toda a carteira
# ---------------------------------------------------------------------------
def _precificar_carteira_vetorizado(
    df: pd.DataFrame,
    data_vencimento: date,
    selic: float,
) -> pd.DataFrame:
    """Aplica RAROC a toda a carteira com operações vetorizadas (sem iterrows).

    Usa prazo individual se a coluna 'prazo_medio_du' estiver disponível na base;
    caso contrário usa o prazo do fundo como proxy (documentado como limitação).
    """
    today = date.today()
    prazo_fundo_dias = max((data_vencimento - today).days, 1)

    df = df.copy()
    face = df["vlr_nominal_total"].fillna(0.0).clip(lower=0)

    # Prazo ajustado: prazo individual do sacado, se disponível; senão fundo
    if "prazo_medio_du" in df.columns:
        prazo_dias = (
            pd.to_numeric(df["prazo_medio_du"], errors="coerce")
            .fillna(prazo_fundo_dias)
            .clip(lower=1)
        )
    else:
        prazo_dias = pd.Series(prazo_fundo_dias, index=df.index, dtype=float)

    # Atraso histórico → adiciona dias ao prazo efetivo.
    # Prioridade: media_atraso_real_dias > media_atraso_dias > 0
    # Não usamos `or` para não tratar 0.0 como falso.
    if "media_atraso_real_dias" in df.columns:
        atraso = pd.to_numeric(df["media_atraso_real_dias"], errors="coerce")
        if "media_atraso_dias" in df.columns:
            atraso = atraso.fillna(pd.to_numeric(df["media_atraso_dias"], errors="coerce"))
    elif "media_atraso_dias" in df.columns:
        atraso = pd.to_numeric(df["media_atraso_dias"], errors="coerce")
    else:
        atraso = pd.Series(0.0, index=df.index)

    atraso = atraso.fillna(0.0).clip(lower=0).round()  # round() como no pricing.py

    prazo_dias_total = (prazo_dias + atraso).clip(lower=1)
    prazo_anos = prazo_dias_total / 365.0

    # Prêmio e PD a partir do rating calculado
    premio = df["rating_calculado"].map(
        {r: p for r, (p, _) in _RATING_PARAMS.items()}
    ).fillna(_RATING_FALLBACK[0])
    pd_anual = df["rating_calculado"].map(
        {r: pd_ for r, (_, pd_) in _RATING_PARAMS.items()}
    ).fillna(_RATING_FALLBACK[1])

    taxa_total = (selic + premio).round(4)

    vp = (face / (1 + taxa_total) ** prazo_anos).round(2)
    receita_bruta = face - vp
    ecl = face * pd_anual * prazo_anos * LGD_PADRAO
    lucro = receita_bruta - ecl
    margem = np.where(face > 0, lucro / face * 100, 0.0)

    df["vp_carteira"]       = vp
    df["ecl_carteira"]      = ecl
    df["lucro_raroc_cart"]  = lucro
    df["margem_cart"]       = margem
    df["taxa_total_cart"]   = taxa_total
    df["prazo_anos_cart"]   = prazo_anos

    return df


# ---------------------------------------------------------------------------
# Breakdown por rating
# ---------------------------------------------------------------------------
def _breakdown_por_rating(df_calc: pd.DataFrame, face_total: float) -> pd.DataFrame:
    rows = []
    for rating in ORDEM_RATINGS:
        sub = df_calc[df_calc["rating_calculado"] == rating]
        if sub.empty:
            continue
        face = sub["vlr_nominal_total"].sum()
        lucro = sub["lucro_raroc_cart"].sum()
        margem = (lucro / face * 100) if face > 0 else 0.0
        rows.append({
            "Rating":         rating,
            "Sacados":        len(sub),
            "Face (R$)":      face,
            "VP (R$)":        sub["vp_carteira"].sum(),
            "ECL (R$)":       sub["ecl_carteira"].sum(),
            "Lucro RAROC (R$)": lucro,
            "Margem (%)":     margem,
            "% da Carteira":  face / face_total * 100 if face_total > 0 else 0.0,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------
def render(
    df_carteira: pd.DataFrame,
    data_vencimento_fundo: date,
    valor_total_override: float = 0.0,
) -> None:
    render_page_header(
        kicker="Valoração · " + data_vencimento_fundo.strftime("%d/%m/%Y"),
        titulo="O que este portfólio vale?",
        subtitulo=(
            "Face nominal não é valor. Esta análise aplica RAROC individualmente "
            "a cada sacado e consolida VP, perda esperada e lucro real do portfólio."
        ),
    )

    if data_vencimento_fundo <= date.today():
        render_callout(
            "Data de vencimento igual ou anterior a hoje. Corrija na sidebar.",
            tipo="alerta",
        )
        return

    if df_carteira.attrs.get("vlr_simulado", False):
        render_callout(
            "Volumes estimados — vlr_nominal_total ausente no BigQuery. "
            "Scores e ratings são reais; valores monetários são ilustrativos.",
            tipo="alerta",
        )

    # Reescala opcional
    df_work = df_carteira.copy()
    if valor_total_override > 0:
        total = df_work["vlr_nominal_total"].sum()
        if total > 0:
            df_work["vlr_nominal_total"] = (
                df_work["vlr_nominal_total"] * (valor_total_override / total)
            )

    selic = buscar_selic()
    with st.spinner("Aplicando RAROC vetorizado à carteira…"):
        df_calc = _precificar_carteira_vetorizado(df_work, data_vencimento_fundo, selic)

    face_total  = df_calc["vlr_nominal_total"].sum()
    vp_total    = df_calc["vp_carteira"].sum()
    ecl_total   = df_calc["ecl_carteira"].sum()
    lucro_total = df_calc["lucro_raroc_cart"].sum()
    receita     = face_total - vp_total
    margem      = (lucro_total / face_total * 100) if face_total > 0 else 0.0
    ecl_share   = (ecl_total / face_total * 100) if face_total > 0 else 0.0
    taxa_media  = df_calc["taxa_total_cart"].mean()
    prazo_dias  = max((data_vencimento_fundo - date.today()).days, 1)
    hhi         = hhi_por_uf(df_calc, coluna_valor="vlr_nominal_total")

    # Nota sobre a limitação de prazo
    usa_prazo_individual = "prazo_medio_du" in df_carteira.columns
    if not usa_prazo_individual:
        render_callout(
            "Prazo proxy: a base consolidada não contém prazo individual por boleto. "
            f"O prazo do fundo ({prazo_dias} dias) foi usado para todos os sacados. "
            "Isso pode superestimar a ECL dos boletos mais curtos — "
            "considere o VP como estimativa conservadora.",
            tipo="info",
        )

    # Veredicto
    tit, desc, tipo = _veredicto(margem, ecl_share, hhi)
    render_callout(f"{tit} — {desc}", tipo=tipo)

    # Hero
    rating_dom = (
        df_calc["rating_calculado"].mode().iloc[0] if not df_calc.empty else "—"
    )
    render_hero_panel(
        label="Valor Presente Total Sugerido (desembolso recomendado pelo fundo)",
        value=formatar_moeda(vp_total),
        meta=f"sobre face de {formatar_moeda(face_total)} · rating dominante ",
        meta_highlight=rating_dom,
        stats=[
            ("Prazo até vencimento", f"{prazo_dias} dias",              "do fundo"),
            ("Selic",               formatar_percentual(selic),         "a.a. · BCB"),
            ("Taxa média",          formatar_percentual(taxa_media),    "Selic + prêmio"),
            ("Sacados",             formatar_numero(len(df_calc)),      "precificados"),
        ],
    )

    render_kpi_row([
        {
            "label":   "Receita Bruta",
            "value":   formatar_moeda(receita),
            "sub":     f"{receita/face_total*100:.1f}% da face — o desconto cobrado"
                       if face_total > 0 else "—",
            "variant": "premium",
        },
        {
            "label":   "Perda Esperada (ECL)",
            "value":   formatar_moeda(ecl_total),
            "sub":     f"IFRS 9 · LGD {LGD_PADRAO*100:.0f}% · {ecl_share:.1f}% da face",
            "variant": "cau",
        },
        {
            "label":   "Lucro Econômico RAROC",
            "value":   formatar_moeda(lucro_total),
            "sub":     "receita bruta menos perda esperada",
            "variant": "pos" if lucro_total >= 0 else "neg",
        },
        {
            "label":   "Margem Real Ponderada",
            "value":   f"{margem:.2f}%",
            "sub":     "retorno ajustado ao risco sobre face",
            "variant": "pos" if margem >= 10 else "cau" if margem >= 5 else "neg",
        },
    ])

    section_divider()

    # ── Breakdown por rating ────────────────────────────────────────────
    render_section_header(
        titulo="Onde está o valor — e onde está o risco?",
        subtitulo=(
            "Sacados A+/A: spreads menores, ECL quase nula. "
            "Sacados C/D: spreads altos, mas ECL consome parte expressiva. "
            "O mix define o perfil de retorno real do fundo."
        ),
    )

    df_break = _breakdown_por_rating(df_calc, face_total)
    if not df_break.empty:
        top = df_break.sort_values("Face (R$)", ascending=False).iloc[0]
        share_top = top["% da Carteira"]
        if top["Rating"] in ("A+", "A"):
            msg = (
                f"Classe dominante {top['Rating']} concentra {share_top:.0f}% da face. "
                f"Margem real {top['Margem (%)']:.1f}% — alta qualidade gera spread menor. "
                "Avalie se o retorno compensa o custo de capital do fundo."
            )
        elif top["Rating"] in ("C", "D"):
            msg = (
                f"{share_top:.0f}% da face está em sacados de alto risco ({top['Rating']}). "
                f"Spread {top['Margem (%)']:.1f}%, mas ECL consome parcela expressiva. "
                "Verifique se os limites de concentração por sacado estão respeitados."
            )
        else:
            msg = (
                f"Classe dominante {top['Rating']} com {share_top:.0f}% da face, "
                f"margem {top['Margem (%)']:.1f}% — mix equilibrado entre segurança e retorno."
            )
        render_callout(msg, tipo="info")

        df_d = df_break.copy()
        df_d["Face (R$)"]        = df_d["Face (R$)"].apply(formatar_moeda)
        df_d["VP (R$)"]          = df_d["VP (R$)"].apply(formatar_moeda)
        df_d["ECL (R$)"]         = df_d["ECL (R$)"].apply(formatar_moeda)
        df_d["Lucro RAROC (R$)"] = df_d["Lucro RAROC (R$)"].apply(formatar_moeda)
        df_d["Margem (%)"]       = df_d["Margem (%)"].apply(lambda x: f"{x:.2f}%")
        df_d["% da Carteira"]    = df_d["% da Carteira"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_d, use_container_width=True, hide_index=True)

    section_divider()

    # ── Concentração ────────────────────────────────────────────────────
    render_section_header(
        titulo="A carteira está adequadamente diversificada?",
        subtitulo="HHI geográfico + enquadramento parametrizável (10% por sacado, 25% por UF — política do fundo).",
    )

    col_hhi, col_uf = st.columns(2)
    with col_hhi:
        nivel = (
            "diversificada ✅" if hhi < 0.15
            else "moderada ⚠️" if hhi < 0.25
            else "concentrada 🚨"
        )
        tipo_hhi = (
            "destaque" if hhi < 0.15
            else "alerta" if hhi < 0.25
            else "critico"
        )
        render_callout(
            f"HHI geográfico {hhi:.4f} — carteira {nivel}.", tipo=tipo_hhi
        )

    with col_uf:
        conc = (
            df_calc.groupby("uf")["vlr_nominal_total"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        alertas = [
            f"🚨 {uf} {v/face_total*100:.1f}%"
            for uf, v in conc.items()
            if face_total > 0 and v / face_total > LIMITE_POR_UF
        ]
        if alertas:
            render_callout(
                "UFs acima do limite parametrizado de 25% (política do fundo): " + " · ".join(alertas),
                tipo="alerta",
            )
        else:
            render_callout(
                f"Todas as UFs dentro do limite de {LIMITE_POR_UF*100:.0f}% do PL. ✅",
                tipo="destaque",
            )

    render_section_header(titulo="Top 5 maiores exposições individuais", subtitulo="")

    top5 = df_calc.nlargest(5, "vlr_nominal_total")[
        ["id_cnpj", "uf", "rating_calculado", "vlr_nominal_total", "margem_cart"]
    ].copy()
    top5["Concentração"] = (
        top5["vlr_nominal_total"] / face_total * 100
        if face_total > 0 else 0
    ).apply(lambda x: f"{x:.2f}%")
    top5["vlr_nominal_total"] = top5["vlr_nominal_total"].apply(formatar_moeda)
    top5["margem_cart"]       = top5["margem_cart"].apply(lambda x: f"{x:.2f}%")
    top5["id_curto"]          = top5["id_cnpj"].apply(id_curto)

    violacoes = (
        df_calc[df_calc["vlr_nominal_total"] / face_total > LIMITE_POR_SACADO]
        if face_total > 0 else pd.DataFrame()
    )
    if not violacoes.empty:
        render_callout(
            f"{len(violacoes)} sacado(s) acima do limite parametrizado de "
            f"{LIMITE_POR_SACADO*100:.0f}% por sacado (política do fundo). "
            "Novos créditos a esses sacados estão bloqueados no Parecer Individual.",
            tipo="critico",
        )

    st.dataframe(
        top5[["id_curto", "uf", "rating_calculado", "vlr_nominal_total", "margem_cart", "Concentração"]].rename(columns={
            "id_curto":         "Sacado",
            "uf":               "UF",
            "rating_calculado": "Rating",
            "vlr_nominal_total":"Face (R$)",
            "margem_cart":      "Margem RAROC",
        }),
        use_container_width=True,
        hide_index=True,
    )

    section_divider()

    # ── Exportação ──────────────────────────────────────────────────────
    render_section_header(titulo="Exportar valoração detalhada", subtitulo="")
    try:
        cols_exp = [
            c for c in [
                "id_cnpj", "uf", "rating_calculado", "score_calculado",
                "vlr_nominal_total", "vp_carteira", "ecl_carteira",
                "lucro_raroc_cart", "margem_cart", "taxa_total_cart", "prazo_anos_cart",
            ]
            if c in df_calc.columns
        ]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_calc[cols_exp].to_excel(
                w, sheet_name="Valoracao_Carteira", index=False
            )
            if not df_break.empty:
                df_break.to_excel(w, sheet_name="Por_Rating", index=False)
            # Aba de metadados
            meta = pd.DataFrame([{
                "Parâmetro":     "Data do cálculo",
                "Valor":         datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }, {
                "Parâmetro":     "Vencimento do fundo",
                "Valor":         data_vencimento_fundo.strftime("%d/%m/%Y"),
            }, {
                "Parâmetro":     "Selic utilizada",
                "Valor":         f"{selic*100:.4f}%",
            }, {
                "Parâmetro":     "LGD",
                "Valor":         f"{LGD_PADRAO*100:.0f}%",
            }, {
                "Parâmetro":     "Prazo individual?",
                "Valor":         "Sim" if usa_prazo_individual else "Não (prazo do fundo como proxy)",
            }])
            meta.to_excel(w, sheet_name="Parametros", index=False)

        st.download_button(
            "📊 Baixar Valoração em Excel",
            data=buf.getvalue(),
            file_name=f"valoracao_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
    except Exception as exc:
        render_callout(f"Não foi possível gerar o Excel: {exc}", tipo="alerta")

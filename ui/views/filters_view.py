"""
View · Explorador da Carteira · FIDC Insight.

Storytelling: "Você tem uma hipótese. Esta ferramenta ajuda a testá-la."

Estrutura narrativa:
  1. Abertura: o que o Explorador faz (contexto para o analista)
  2. Presets de investigação com contexto narrativo (não só rótulos)
  3. Filtros ativos como "recorte da carteira"
  4. Cards de filtro com distribuição ao vivo
  5. Resultados com interpretação automática

Remove: presets duplicados e confusos.
Adiciona: contexto de por que cada filtro importa.
"""

import io
from datetime import datetime
from textwrap import dedent

import pandas as pd
import streamlit as st

from config.business_rules import ORDEM_RATINGS
from ui.charts import (
    barras_segmento,
    donut_ratings,
    histograma_scores,
    mini_barras_rating,
    mini_barras_segmento,
    mini_barras_uf,
    mini_histograma,
)
from ui.components import (
    render_callout,
    render_kpi_row,
    render_page_header,
    render_section_header,
    section_divider,
)
from utils.formatters import formatar_moeda, formatar_numero, id_curto

REGIOES = {
    "Norte":        ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste":     ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste":      ["ES", "MG", "RJ", "SP"],
    "Sul":          ["PR", "RS", "SC"],
}


def _html(markup: str) -> None:
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def _default_bounds(df: pd.DataFrame) -> dict:
    vlr  = pd.to_numeric(df["vlr_nominal_total"], errors="coerce").dropna()
    atr  = pd.to_numeric(df["media_atraso_dias"], errors="coerce").dropna() if "media_atraso_dias" in df.columns else pd.Series(dtype=float)
    ufs_all  = sorted(df["uf"].dropna().unique().tolist())
    segs_all = (
        sorted(df["cnae_segmento"].dropna().astype(str).unique().tolist())
        if "cnae_segmento" in df.columns else []
    )
    return {
        "_filt_vlr_bounds":      (float(vlr.min()) if len(vlr) else 0.0, float(vlr.max()) if len(vlr) else 1.0),
        "_filt_atraso_bounds":   (0.0, float(atr.max()) if len(atr) else 60.0),
        "_filt_ufs_all":         ufs_all,
        "_filt_ratings_all":     list(ORDEM_RATINGS),
        "_filt_segmentos_all":   segs_all,
    }


def _inicializar_estado(df: pd.DataFrame) -> None:
    bounds = _default_bounds(df)
    for k, v in bounds.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("filt_ratings", list(ORDEM_RATINGS))
    st.session_state.setdefault("filt_ufs", bounds["_filt_ufs_all"])
    st.session_state.setdefault("filt_score", (0, 1000))
    st.session_state.setdefault("filt_vlr", bounds["_filt_vlr_bounds"])
    st.session_state.setdefault("filt_atraso", bounds["_filt_atraso_bounds"])
    st.session_state.setdefault("filt_search", "")
    st.session_state.setdefault("filt_segmentos", list(bounds["_filt_segmentos_all"]))


def _preset_todos() -> None:
    s = st.session_state
    s.filt_ratings = list(s._filt_ratings_all)
    s.filt_ufs = list(s._filt_ufs_all)
    s.filt_score = (0, 1000)
    s.filt_vlr = tuple(s._filt_vlr_bounds)
    s.filt_atraso = tuple(s._filt_atraso_bounds)
    s.filt_search = ""
    if "_filt_segmentos_all" in s:
        s.filt_segmentos = list(s._filt_segmentos_all)


def _preset_premium() -> None:
    st.session_state.filt_ratings = ["A+", "A"]


def _preset_em_risco() -> None:
    st.session_state.filt_ratings = ["C", "D"]


def _preset_eixo() -> None:
    disp = st.session_state._filt_ufs_all
    st.session_state.filt_ufs = [uf for uf in ["SP", "RJ", "MG"] if uf in disp]


def _preset_top_volume() -> None:
    lo, hi = st.session_state._filt_vlr_bounds
    corte = lo + (hi - lo) * 0.75
    st.session_state.filt_vlr = (corte, hi)


def _regiao_callback(regiao: str) -> None:
    ufs = REGIOES.get(regiao, [])
    disp = st.session_state._filt_ufs_all
    st.session_state.filt_ufs = [uf for uf in ufs if uf in disp]


def _regiao_todas() -> None:
    st.session_state.filt_ufs = list(st.session_state._filt_ufs_all)


def _volume_preset_micro() -> None:
    lo, _ = st.session_state._filt_vlr_bounds
    st.session_state.filt_vlr = (lo, 100_000.0)


def _volume_preset_pequeno() -> None:
    st.session_state.filt_vlr = (100_000.0, 500_000.0)


def _volume_preset_medio() -> None:
    st.session_state.filt_vlr = (500_000.0, 2_000_000.0)


def _volume_preset_grande() -> None:
    _, hi = st.session_state._filt_vlr_bounds
    st.session_state.filt_vlr = (2_000_000.0, hi)


def _volume_preset_tudo() -> None:
    st.session_state.filt_vlr = tuple(st.session_state._filt_vlr_bounds)


def _aplicar_filtros_state(df: pd.DataFrame) -> pd.DataFrame:
    s = st.session_state

    # Garantir que colunas numéricas realmente são numéricas.
    # O BigQuery às vezes retorna FLOAT64 como string dependendo da versão
    # do driver — a coerção aqui evita TypeError em todas as comparações.
    df = df.copy()
    for col in ("score_calculado", "vlr_nominal_total", "media_atraso_dias"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    m = pd.Series([True] * len(df), index=df.index)

    if s.get("filt_ratings"):
        m &= df["rating_calculado"].isin(s.filt_ratings)
    if s.get("filt_ufs"):
        m &= df["uf"].isin(s.filt_ufs)

    score_range = s.get("filt_score", (0, 1000))
    m &= (df["score_calculado"] >= float(score_range[0])) & (df["score_calculado"] <= float(score_range[1]))

    vlr_range = s.get("filt_vlr", s.get("_filt_vlr_bounds", (0.0, 1e9)))
    m &= (df["vlr_nominal_total"] >= float(vlr_range[0])) & (df["vlr_nominal_total"] <= float(vlr_range[1]))

    atr_range = s.get("filt_atraso", (0.0, 999.0))
    if "media_atraso_dias" in df.columns:
        m &= (df["media_atraso_dias"] >= float(atr_range[0])) & (df["media_atraso_dias"] <= float(atr_range[1]))

    search = str(s.get("filt_search", "")).strip()
    if search:
        m &= df["id_cnpj"].astype(str).str.contains(search, case=False, na=False)

    segs = s.get("filt_segmentos", [])
    if segs and "cnae_segmento" in df.columns:
        m &= df["cnae_segmento"].isin(segs) | df["cnae_segmento"].isna()

    return df[m].copy()


def _render_presets() -> None:
    """Presets de investigação — cada um conta uma história."""
    _html("""
    <div style="font-size:0.75rem;letter-spacing:0.08em;text-transform:uppercase;
                color:var(--text-muted,#6B7280);margin-bottom:0.5rem;font-weight:600;">
        Perguntas rápidas de investigação
    </div>
    """)
    col1, col2, col3, col4, col5 = st.columns(5, gap="small")
    with col1:
        st.button("Carteira completa", on_click=_preset_todos,
                  use_container_width=True, help="Resetar todos os filtros")
    with col2:
        st.button("Só grau de investimento", on_click=_preset_premium,
                  use_container_width=True, help="Apenas sacados A+ e A")
    with col3:
        st.button("Sacados em risco", on_click=_preset_em_risco,
                  use_container_width=True, help="Apenas C e D — candidatos a revisão")
    with col4:
        st.button("Eixo SP-RJ-MG", on_click=_preset_eixo,
                  use_container_width=True, help="Os três maiores estados")
    with col5:
        st.button("Top volume", on_click=_preset_top_volume,
                  use_container_width=True, help="Quartil superior de exposição")


def _render_chipbar() -> None:
    """Mostra os filtros ativos como contexto narrativo."""
    s = st.session_state
    chips = []

    ratings_ativos = s.get("filt_ratings", list(ORDEM_RATINGS))
    if set(ratings_ativos) != set(ORDEM_RATINGS):
        chips.append(f"Rating: {', '.join(ratings_ativos)}")

    ufs_ativas = s.get("filt_ufs", [])
    todos_ufs = s.get("_filt_ufs_all", [])
    if set(ufs_ativas) != set(todos_ufs) and ufs_ativas:
        label = ", ".join(ufs_ativas[:3])
        if len(ufs_ativas) > 3:
            label += f" +{len(ufs_ativas) - 3}"
        chips.append(f"UFs: {label}")

    score_r = s.get("filt_score", (0, 1000))
    if score_r != (0, 1000):
        chips.append(f"Score {score_r[0]}–{score_r[1]}")

    if not chips:
        return

    st.markdown(
        "Recorte ativo: " + " · ".join(f"`{c}`" for c in chips)
    )


def _render_filter_cards(df: pd.DataFrame) -> None:
    """Cards de filtro 2×2 com distribuição ao vivo."""
    s = st.session_state

    row1_col1, row1_col2 = st.columns(2, gap="medium")
    row2_col1, row2_col2 = st.columns(2, gap="medium")

    # --- Rating ---
    with row1_col1:
        with st.container(border=True):
            _html('<div class="filter-label">Risco</div>')
            _html("<p style='font-size:0.82rem;margin-bottom:0.6rem;line-height:1.4;'>"
                  "O rating sintetiza o risco total do sacado. Filtrar por rating "
                  "é o ponto de partida mais natural para qualquer análise.</p>")
            st.plotly_chart(mini_barras_rating(df, s.get("filt_ratings", list(ORDEM_RATINGS), key="filters_chart_1")), use_container_width=True,
                            config={"displayModeBar": False})
            ratings_sel = st.multiselect(
                "Selecione os ratings",
                options=list(ORDEM_RATINGS),
                default=s.get("filt_ratings", list(ORDEM_RATINGS)),
                key="filt_ratings",
                label_visibility="collapsed",
            )

    # --- Score ---
    with row1_col2:
        with st.container(border=True):
            _html('<div class="filter-label">Score</div>')
            _html("<p style='font-size:0.82rem;margin-bottom:0.6rem;line-height:1.4;'>"
                  "Para análises numéricas precisas: isole uma faixa específica "
                  "de score e veja quem está dentro dela.</p>")
            score_range = s.get("filt_score", (0, 1000))
            st.plotly_chart(
                mini_histograma(
                    pd.to_numeric(df["score_calculado"], errors="coerce", key="filters_chart_2").dropna(),
                    ativos_lo=float(score_range[0]),
                    ativos_hi=float(score_range[1]),
                ),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.slider("Faixa de score", 0, 1000,
                      s.get("filt_score", (0, 1000)), step=50, key="filt_score")

    # --- Geografia ---
    with row2_col1:
        with st.container(border=True):
            _html('<div class="filter-label">Geografia</div>')
            _html("<p style='font-size:0.82rem;margin-bottom:0.6rem;line-height:1.4;'>"
                  "Risco geográfico: crises regionais afetam todos os sacados "
                  "de uma UF ao mesmo tempo. Isole estados para medir exposição.</p>")
            st.plotly_chart(mini_barras_uf(df, s.get("filt_ufs", s.get("_filt_ufs_all", []), key="filters_chart_3")), use_container_width=True,
                            config={"displayModeBar": False})

            col_reg, col_todas = st.columns([3, 1])
            with col_reg:
                regioes = list(REGIOES.keys())
                reg_sel = st.selectbox("Selecionar por região",
                                       ["—"] + regioes, key="_geo_regiao_sel",
                                       label_visibility="collapsed")
                if reg_sel != "—":
                    _regiao_callback(reg_sel)
            with col_todas:
                if st.button("Todas", key="geo_todas"):
                    _regiao_todas()

            ufs_all = s.get("_filt_ufs_all", [])
            st.multiselect("UFs", options=ufs_all,
                           default=s.get("filt_ufs", ufs_all),
                           key="filt_ufs", label_visibility="collapsed")

    # --- Volume ---
    with row2_col2:
        with st.container(border=True):
            _html('<div class="filter-label">Volume Exposto</div>')
            _html("<p style='font-size:0.82rem;margin-bottom:0.6rem;line-height:1.4;'>"
                  "Onde está o dinheiro? Sacados de baixo volume têm risco unitário menor. "
                  "Grandes exposições individuais merecem análise própria.</p>")
            vlr_range = s.get("filt_vlr", s.get("_filt_vlr_bounds", (0.0, 1e9)))
            st.plotly_chart(
                mini_histograma(
                    pd.to_numeric(df["vlr_nominal_total"], errors="coerce", key="filters_chart_4").dropna(),
                    ativos_lo=float(vlr_range[0]),
                    ativos_hi=float(vlr_range[1]),
                ),
                use_container_width=True,
                config={"displayModeBar": False},
            )

            vcols = st.columns(5, gap="small")
            for label, callback in [
                ("Micro", _volume_preset_micro),
                ("Peq.", _volume_preset_pequeno),
                ("Méd.", _volume_preset_medio),
                ("Grand.", _volume_preset_grande),
                ("Tudo", _volume_preset_tudo),
            ]:
                with vcols.pop(0):
                    st.button(label, on_click=callback, use_container_width=True)

            vlr_bounds = s.get("_filt_vlr_bounds", (0, 1.0))
            st.slider("Volume (R$)", float(vlr_bounds[0]), float(vlr_bounds[1]),
                      s.get("filt_vlr", vlr_bounds), key="filt_vlr",
                      format="R$ %.0f")


def _render_search_row() -> None:
    col_s, col_c = st.columns([5, 1], gap="small")
    with col_s:
        st.text_input("Buscar por CNPJ ou hash", placeholder="Ex: 12345678 ou hash...",
                      key="filt_search", label_visibility="collapsed")
    with col_c:
        if st.button("Limpar tudo", use_container_width=True, type="secondary"):
            _preset_todos()


def _render_resultado(df_orig: pd.DataFrame, df_filt: pd.DataFrame) -> None:
    """Renderiza o resultado do recorte interpretando o que o subgrupo significa."""
    n_filt = len(df_filt)
    n_total = len(df_orig)
    cobertura = n_filt / n_total * 100 if n_total > 0 else 0
    pl_filt = df_filt["vlr_nominal_total"].sum()
    pl_orig = df_orig["vlr_nominal_total"].sum()
    share_pl = pl_filt / pl_orig * 100 if pl_orig > 0 else 0

    st.markdown("---")

    if n_filt == 0:
        render_callout(
            "Nenhum sacado encontrado com os filtros aplicados. "
            "Tente ampliar os critérios ou use uma investigação guiada acima.",
            tipo="alerta",
        )
        return

    def _score_ponderado(sub: pd.DataFrame) -> float:
        """Média do score ponderada pelo volume — reflete o risco real da carteira."""
        pesos = sub["vlr_nominal_total"].clip(lower=0)
        if pesos.sum() > 0:
            return float((pesos * sub["score_calculado"]).sum() / pesos.sum())
        return float(sub["score_calculado"].mean())

    score_filt = _score_ponderado(df_filt)
    score_orig = _score_ponderado(df_orig)
    diff_score = score_filt - score_orig
    rating_dom = df_filt["rating_calculado"].mode().iloc[0] if not df_filt.empty else "—"

    # ── Interpretação automática — a história do subgrupo
    if abs(diff_score) > 50:
        direcao = "significativamente melhor" if diff_score > 0 else "significativamente pior"
        contexto = f"Este recorte tem score médio {score_filt:.0f} pts — {direcao} que a carteira total ({score_orig:.0f} pts). "
    elif abs(diff_score) > 20:
        direcao = "ligeiramente melhor" if diff_score > 0 else "ligeiramente pior"
        contexto = f"Score médio {score_filt:.0f} pts — {direcao} que a média geral ({score_orig:.0f} pts). "
    else:
        contexto = f"Score médio {score_filt:.0f} pts — alinhado com a carteira total ({score_orig:.0f} pts). "

    pct_inad = (df_filt["rating_calculado"].isin(["C", "D"])).mean() * 100 if n_filt > 0 else 0
    if pct_inad > 50:
        contexto += f"{pct_inad:.0f}% dos sacados deste recorte estão em rating C ou D — subgrupo de alto risco."
    elif pct_inad > 25:
        contexto += f"{pct_inad:.0f}% em rating C/D — perfil de risco elevado neste subgrupo."
    else:
        pct_premium = (df_filt["rating_calculado"].isin(["A+", "A"])).mean() * 100
        contexto += f"{pct_premium:.0f}% em grau de investimento — qualidade acima do limiar mínimo."

    tipo_narrativa = "alerta" if pct_inad > 40 or diff_score < -50 else "destaque" if diff_score > 30 else "info"
    render_callout(contexto, tipo=tipo_narrativa)

    render_section_header(
        titulo=f"{formatar_numero(n_filt)} sacados · {share_pl:.1f}% do PL · {formatar_moeda(pl_filt, casas=0)}",
        subtitulo=f"{cobertura:.1f}% da base total · rating dominante {rating_dom}",
    )

    render_kpi_row([
        {"label": "Sacados no Recorte",  "value": formatar_numero(n_filt),
         "sub": f"{cobertura:.1f}% da base total", "variant": "accent"},
        {"label": "Volume Exposto",      "value": formatar_moeda(pl_filt, casas=0),
         "sub": f"{share_pl:.1f}% do PL da carteira", "variant": "premium"},
        {"label": "Score Médio",         "value": f"{score_filt:.0f}",
         "sub": f"{'▲' if diff_score > 0 else '▼'} {abs(diff_score):.0f} pts vs carteira total",
         "variant": "pos" if diff_score >= 0 else "neg"},
        {"label": "Rating Dominante",    "value": rating_dom,
         "sub": "classe mais frequente", "variant": "ink"},
    ], cols=4)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.plotly_chart(donut_ratings(df_filt), key="filters_chart_5", use_container_width=True,
                        config={"displayModeBar": False})
    with c2:
        st.plotly_chart(histograma_scores(df_filt), key="filters_chart_6", use_container_width=True,
                        config={"displayModeBar": False})

    if "cnae_segmento" in df_filt.columns and df_filt["cnae_segmento"].notna().any():
        st.plotly_chart(barras_segmento(df_filt, modo="volume", top_n=10), key="filters_chart_7",
                        use_container_width=True, config={"displayModeBar": False})

    section_divider()
    render_section_header(titulo="Dados do recorte", subtitulo="")

    cols_show = ["id_cnpj", "uf", "rating_calculado", "score_calculado", "vlr_nominal_total"]
    if "cnae_segmento" in df_filt.columns:
        cols_show.append("cnae_segmento")
    if "media_atraso_dias" in df_filt.columns:
        cols_show.append("media_atraso_dias")
    cols_show = [c for c in cols_show if c in df_filt.columns]

    df_tabela = df_filt[cols_show].copy()
    df_tabela["id_cnpj"] = df_tabela["id_cnpj"].apply(id_curto)

    st.dataframe(df_tabela.rename(columns={
        "id_cnpj": "Sacado", "uf": "UF", "rating_calculado": "Rating",
        "score_calculado": "Score Nuclea", "vlr_nominal_total": "Volume (R$)",
        "cnae_segmento": "Segmento", "media_atraso_dias": "Atraso médio (d)",
    }), use_container_width=True, hide_index=True, height=360)

    buf = io.BytesIO()
    df_filt[cols_show].to_excel(buf, index=False)
    st.download_button(
        "📥 Exportar recorte (.xlsx)", data=buf.getvalue(),
        file_name=f"recorte_carteira_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def _render_investigacoes_guiadas(df: pd.DataFrame) -> None:
    """5 investigações nomeadas como perguntas de negócio.

    Cada cartão descreve QUAL pergunta responde e configura os filtros
    automaticamente quando clicado. O gestor não pensa em "filtrar rating C e D" —
    ele pensa "quero ver os sacados que precisam de atenção".
    """
    s = st.session_state
    _pesos = df["vlr_nominal_total"].clip(lower=0)
    score_medio = float((_pesos * df["score_calculado"]).sum() / _pesos.sum()) if _pesos.sum() > 0 else float(df["score_calculado"].mean())

    investigacoes = [
        {
            "titulo": "Quem precisa de atenção?",
            "descricao": "Sacados com rating C ou D — alto risco de inadimplência. Candidatos a revisão manual ou saída de posição.",
            "icone": "🔴",
            "callback": lambda: (
                s.update({"filt_ratings": ["C", "D"]}),
            ),
            "on_click": _preset_em_risco,
        },
        {
            "titulo": "Onde está o dinheiro bom?",
            "descricao": "Grau de investimento (A+/A) — base da qualidade do portfólio. Como está performando o núcleo saudável?",
            "icone": "✅",
            "callback": None,
            "on_click": _preset_premium,
        },
        {
            "titulo": "Grandes exposições têm qualidade?",
            "descricao": "25% das maiores posições da carteira. Grandes exposições com rating baixo concentram risco relevante.",
            "icone": "📊",
            "callback": None,
            "on_click": _preset_top_volume,
        },
        {
            "titulo": "Há risco regional concentrado?",
            "descricao": "Eixo SP-RJ-MG — os três maiores estados. Crises regionais impactam todos os sacados de uma UF simultaneamente.",
            "icone": "🗺️",
            "callback": None,
            "on_click": _preset_eixo,
        },
        {
            "titulo": "Ver carteira completa",
            "descricao": "Resetar todos os filtros e ver a carteira inteira. Ponto de partida para qualquer análise.",
            "icone": "🔄",
            "callback": None,
            "on_click": _preset_todos,
        },
    ]

    st.markdown(
        '<div style="font-size:0.72rem;letter-spacing:.08em;text-transform:uppercase;'
        'color:var(--color-text-secondary);margin-bottom:0.75rem;font-weight:500;">'
        'Investigações rápidas — clique para configurar os filtros automaticamente</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(len(investigacoes), gap="small")
    for col, inv in zip(cols, investigacoes):
        with col:
            with st.container(border=True):
                st.markdown(
                    f'<div style="font-size:16px;margin-bottom:4px">{inv["icone"]}</div>'
                    f'<div style="font-size:12px;font-weight:500;color:var(--color-text-primary);'
                    f'margin-bottom:4px;line-height:1.3">{inv["titulo"]}</div>'
                    f'<div style="font-size:11px;color:var(--color-text-secondary);'
                    f'line-height:1.4">{inv["descricao"]}</div>',
                    unsafe_allow_html=True,
                )
                st.button(
                    "Investigar",
                    on_click=inv["on_click"],
                    use_container_width=True,
                    key=f"inv_{inv['titulo'][:10]}",
                )


def render(df: pd.DataFrame) -> None:
    """Renderiza o Explorador com investigações guiadas e filtros detalhados."""

    render_page_header(
        kicker="Investigação da Carteira",
        titulo="Quem está aqui dentro?",
        subtitulo=(
            "Comece por uma investigação guiada ou configure os filtros manualmente. "
            "Cada recorte é interpretado automaticamente — você vê o que o subgrupo significa, "
            "não só os dados brutos."
        ),
    )

    _inicializar_estado(df)

    # ── Investigações guiadas (perguntas de negócio)
    _render_investigacoes_guiadas(df)

    _render_chipbar()

    section_divider()

    # ── Filtros detalhados (modo avançado)
    with st.expander("⚙️ Filtros detalhados", expanded=False):
        _render_filter_cards(df)
        _render_search_row()

    df_filt = _aplicar_filtros_state(df)
    _render_resultado(df, df_filt)
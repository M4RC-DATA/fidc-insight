"""
View · Consulta Individual · FIDC Insight.

Estrutura:
  1. Header compacto (sacado + rating + UF)
  2. Decisão: APROVADO / REVISAR / BLOQUEADO
  3. 4 números essenciais (VP, ECL, Lucro, Margem)
  4. Raio-X de pagamentos
  5. Expander "Saiba mais" → cálculos, score, lastro, compliance
  6. Exportar
"""

from datetime import date, datetime
import pandas as pd
import streamlit as st

from config.business_rules import LGD_PADRAO, PESOS
from domain.lastro import validar_lastro
from domain.pricing import precificar_operacao
from domain.risk import (
    avaliar_concentracao_sacado, avaliar_concentracao_uf,
    calcular_probabilidade_contagio, classificar_nivel_contagio, hhi_por_uf,
)
from domain.scoring import classificar_score, percentil_na_carteira
from exports.excel_generator import gerar_excel_parecer
from exports.pdf_generator import gerar_pdf_auditoria
from services.bcb_api import buscar_selic
from services.database import buscar_historico_transacional, registrar_precificacao
from ui.charts import (
    barras_componentes_icl, scatter_lastro_historico, velocimetro_score,
)
from ui.components import (
    render_alert, render_callout, render_card_head, render_ews_panel,
    render_kpi_row, render_kv_rows, render_segmento_panel, section_divider,
)
from utils.formatters import formatar_moeda, formatar_numero, formatar_percentual, id_curto


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _safe_str(v) -> str:
    if v is None: return ""
    try:
        if pd.isna(v): return ""
    except (TypeError, ValueError): pass
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(v).strip()


def _pick_cnae(row) -> str:
    for c in ["cd_cnae_prin","cd_cnae_princ","cnae_principal","cnae_fiscal","cnae","cd_cnae"]:
        v = _safe_str(row.get(c))
        if v: return v
    return ""


def _decisao(clf, score, lastro, comp_sacado, comp_uf, margem) -> tuple[str,str,list[str]]:
    bloqueios, atencoes = [], []
    if comp_sacado.status == "bloqueio": bloqueios.append(comp_sacado.mensagem)
    if comp_uf.status == "bloqueio":     bloqueios.append(comp_uf.mensagem)
    if bloqueios:
        return "bloqueio", "Operação bloqueada", bloqueios
    if lastro.selo.value == "VERMELHO":
        atencoes.append(f"Lastro suspeito — ICL {lastro.icl:.0f}%")
    if clf.rating in ("C","D"):
        atencoes.append(f"Rating {clf.rating} — PD {clf.pd_anual*100:.1f}% a.a. · margem {margem:.1f}%")
    if comp_sacado.status == "alerta": atencoes.append(comp_sacado.mensagem)
    if comp_uf.status    == "alerta":  atencoes.append(comp_uf.mensagem)
    if atencoes:
        return "revisao", "Revisão necessária", atencoes
    return "aprovado", "Operação aprovada", [
        f"Rating {clf.rating} · margem real {margem:.1f}%",
        f"ICL {lastro.icl:.0f}% — lastro verificado",
        "Enquadrado nos limites do fundo",
    ]


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render(df_carteira: pd.DataFrame, cnpj: str, valor: float, data_vencimento: date) -> None:

    df_cnpj = df_carteira[df_carteira["id_cnpj"] == cnpj]
    if df_cnpj.empty:
        render_callout(f"Sacado `{id_curto(cnpj)}` não encontrado na base.", tipo="alerta")
        return

    row  = df_cnpj.iloc[0]
    clf  = classificar_score(float(row["score_calculado"]))
    selic = buscar_selic()

    # Atraso histórico — sem falsy-zero bug
    _ar = row.get("media_atraso_real_dias")
    _ad = row.get("media_atraso_dias", 0.0)
    atraso = float(_ar if _ar is not None else (_ad or 0.0))
    if atraso != atraso or atraso < 0: atraso = 0.0

    resultado = precificar_operacao(
        valor_face=valor, data_vencimento=data_vencimento, data_hoje=date.today(),
        selic=selic, premio_anual=clf.premio_anual, pd_anual=clf.pd_anual,
        lgd=LGD_PADRAO, atraso_historico_dias=atraso,
    )

    uf_sacado = str(row.get("uf", "—"))
    score     = float(row["score_calculado"])
    prob_cont = calcular_probabilidade_contagio(
        media_atraso_dias=atraso,
        share_inadimplencia=float(row.get("share_vl_inad_pag_bol_6_a_15d", 0.0) or 0.0),
    )
    nivel_cont = classificar_nivel_contagio(prob_cont)
    df_hist_tr = buscar_historico_transacional(cnpj=cnpj, row_sacado=row)
    lastro = validar_lastro(
        df_historico=df_hist_tr, valor_proposto=valor,
        prazo_proposto=max((data_vencimento - date.today()).days, 1),
    )
    comp_sacado = avaliar_concentracao_sacado(df_carteira, cnpj, valor)
    comp_uf     = avaliar_concentracao_uf(df_carteira, uf_sacado, valor)

    # ── 1. HEADER COMPACTO ──────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:14px;'
        f'padding:14px 0 4px;">'
        f'<div style="font-size:1.5rem;font-weight:600;color:#0F172A;letter-spacing:-.02em">'
        f'{id_curto(cnpj)}</div>'
        f'<div style="display:flex;gap:8px;align-items:center">'
        f'<span style="background:#DBEAFE;color:#1D4ED8;font-size:.75rem;font-weight:600;'
        f'padding:2px 10px;border-radius:20px">{clf.rating}</span>'
        f'<span style="color:#64748B;font-size:.82rem">{uf_sacado}</span>'
        f'<span style="color:#94A3B8;font-size:.75rem">{score:.0f} pts Nuclea</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # Segmento CNAE se disponível
    segmento = _safe_str(row.get("cnae_segmento"))
    if segmento and segmento.lower() != "nan":
        render_segmento_panel(
            segmento=segmento,
            secao_letra=_safe_str(row.get("cnae_secao")) or None,
            secao_nome=_safe_str(row.get("cnae_secao_nome")) or None,
            descricao_cnae=_safe_str(row.get("cnae_descricao")) or None,
            codigo_cnae=_pick_cnae(row) or None,
            cor=_safe_str(row.get("cnae_cor")) or "#7C8CA8",
        )

    # ── 2. DECISÃO ──────────────────────────────────────────────────────
    status, titulo, razoes = _decisao(clf, score, lastro, comp_sacado, comp_uf, resultado.margem_real)
    ESTILOS = {
        "bloqueio": ("critico", "🚫"),
        "revisao":  ("alerta",  "⚠️"),
        "aprovado": ("destaque","✅"),
    }
    tipo_c, icone = ESTILOS[status]
    linhas = "".join(f"<br>• {r}" for r in razoes)
    render_callout(f"<strong>{icone} {titulo}</strong>{linhas}", tipo=tipo_c)

    # ── 3. QUATRO NÚMEROS ESSENCIAIS ────────────────────────────────────
    render_kpi_row([
        {"label": "VP Sugerido",    "value": formatar_moeda(resultado.valor_presente, casas=0),
         "sub": f"face {formatar_moeda(valor, casas=0)}", "variant": "accent"},
        {"label": "Perda Esperada", "value": formatar_moeda(resultado.perda_esperada, casas=0),
         "sub": "ECL · IFRS 9", "variant": "cau"},
        {"label": "Lucro RAROC",    "value": formatar_moeda(resultado.lucro_raroc, casas=0),
         "sub": "ajustado ao risco",
         "variant": "pos" if resultado.lucro_raroc >= 0 else "neg"},
        {"label": "Margem Real",    "value": f"{resultado.margem_real:.2f}%",
         "sub": f"taxa {formatar_percentual(resultado.taxa_total)} a.a.",
         "variant": "pos" if resultado.margem_real >= 5 else "cau"},
    ])

    section_divider()

    # ── 4. RAIO-X DE PAGAMENTOS ─────────────────────────────────────────
    st.markdown("Raio-X de Pagamentos")
    _render_raiox(row)

    section_divider()

    # ── 5. SAIBA MAIS + CONTEXTO NUCLEA ─────────────────────────────────
    aba_saber, aba_contexto = st.tabs(["Saiba mais", "Contexto Nuclea"])

    with aba_saber:
        st.markdown("Decomposição do Preço")
        col_v, col_d = st.columns([4, 5], gap="medium")
        with col_v:
            st.plotly_chart(velocimetro_score(score, "Nuclea"), use_container_width=True,
                            config={"displayModeBar": False}, key="iv_velocimetro")
        with col_d:
            render_kv_rows([
                ("Valor de face",         formatar_moeda(resultado.valor_face)),
                ("Valor presente (VP)",   formatar_moeda(resultado.valor_presente)),
                ("Receita bruta",         formatar_moeda(resultado.desconto_bruto)),
                ("Perda esperada (ECL)",  formatar_moeda(resultado.perda_esperada)),
                ("Taxa total a.a.",       formatar_percentual(resultado.taxa_total),
                 f"Selic {formatar_percentual(selic)} + prêmio {formatar_percentual(clf.premio_anual)}"),
                ("Prazo contratual",      f"{resultado.prazo_contratual_dias} dias"),
                ("Atraso histórico",      f"+{resultado.atraso_esperado_dias} dias"),
                ("Prazo efetivo",         f"{resultado.prazo_dias} dias",
                 f"{resultado.prazo_anos:.3f} anos"),
                ("Lucro RAROC",           formatar_moeda(resultado.lucro_raroc)),
                ("Margem real",           f"{resultado.margem_real:.2f}%"),
            ], emphasize=[8, 9])

        section_divider()
        st.markdown("Composição do Score Nuclea")
        comp_q = float(row.get("v_qualidade", 0.0) or 0.0)
        comp_i = float(row.get("v_inadimplencia", 0.0) or 0.0)
        comp_l = float(row.get("v_liquidez", 0.0) or 0.0)
        comp_r = float(row.get("v_regional", 0.0) or 0.0)
        render_kpi_row([
            {"label": "Qualidade",    "value": f"{comp_q*PESOS['qualidade']*1000:.0f} pts",
             "sub": f"peso {int(PESOS['qualidade']*100)}%", "variant": "accent"},
            {"label": "Inadimplência","value": f"{comp_i*PESOS['inadimplencia']*1000:.0f} pts",
             "sub": f"peso {int(PESOS['inadimplencia']*100)}%", "variant": "cau"},
            {"label": "Liquidez",     "value": f"{comp_l*PESOS['liquidez']*1000:.0f} pts",
             "sub": f"peso {int(PESOS['liquidez']*100)}%", "variant": "premium"},
            {"label": "Regional",     "value": f"{comp_r*PESOS['regional']*1000:.0f} pts",
             "sub": f"peso {int(PESOS['regional']*100)}%", "variant": "ink"},
        ])

        section_divider()
        st.markdown("Verificação de Lastro (Anti-fraude)")
        sel = lastro.selo.value
        render_alert(
            {"VERDE":"aprovado","AMARELO":"alerta","VERMELHO":"bloqueio"}[sel],
            f"<b>ICL {lastro.icl:.1f}%</b> — {lastro.recomendacao}",
        )
        col_s, col_c = st.columns([6, 5], gap="medium")
        with col_s:
            n = lastro.historico.n_operacoes
            if n >= 6:
                st.plotly_chart(scatter_lastro_historico(
                    df_historico=df_hist_tr, valor_proposto=valor,
                    z_score_valor=lastro.z_score_valor, selo=sel,
                    media_historica=lastro.historico.valor_medio,
                    desvio_historico=lastro.historico.valor_desvio,
                ), use_container_width=True, config={"displayModeBar": False}, key="iv_scatter")
            else:
                render_callout(f"Histórico raso ({n} op.). Análise por recorrência e prazo.", tipo="info")
        with col_c:
            st.plotly_chart(barras_componentes_icl(lastro.componentes),
                            use_container_width=True, config={"displayModeBar": False}, key="iv_icl")

        section_divider()
        st.markdown("Risco de Contágio na Rede (EWS)")
        render_ews_panel(
            nivel=nivel_cont.value,
            probabilidade=prob_cont,
            descricao=(
                f"Atraso médio {atraso:.1f} dias · "
                f"Inadimplência {formatar_percentual(float(row.get('share_vl_inad_pag_bol_6_a_15d', 0.0) or 0.0))}"
            ),
        )

        section_divider()
        st.markdown("Enquadramento (Política do Fundo)")
        render_alert(comp_sacado.status, comp_sacado.mensagem)
        render_alert(comp_uf.status, comp_uf.mensagem)

    with aba_contexto:
        _render_contexto_nuclea(df_carteira, cnpj, score, clf.rating, uf_sacado)

    # ── 6. EXPORTAR ─────────────────────────────────────────────────────
    section_divider()
    _render_exports(cnpj, uf_sacado, valor, resultado, clf, nivel_cont.value, score, lastro)


def _render_raiox(row):
    tot    = int(row.get("total_boletos", 0) or 0)
    pagos  = int(row.get("boletos_pagos", 0) or 0)
    inad   = int(row.get("boletos_inadimplentes", 0) or 0)
    tx_liq = float(row.get("taxa_liquidacao", 0.0) or 0.0)
    tx_in  = float(row.get("taxa_inadimplencia", 0.0) or 0.0)
    atr_m  = float(row.get("media_atraso_real_dias", 0.0) or 0.0)
    atr_mx = float(row.get("atraso_max_real_dias", 0.0) or 0.0)
    vlr_t  = float(row.get("vlr_nominal_total", 0.0) or 0.0)
    vlr_m  = float(row.get("vlr_nominal_medio", 0.0) or 0.0)

    render_kpi_row([
        {"label": "Total de Boletos",   "value": formatar_numero(tot),
         "sub": f"{pagos} pagos · {inad} em atraso", "variant": "accent"},
        {"label": "Taxa de Liquidação", "value": formatar_percentual(tx_liq),
         "sub": "histórico", "variant": "pos"},
        {"label": "Taxa de Inadimp.",   "value": formatar_percentual(tx_in),
         "sub": "histórico", "variant": "cau"},
        {"label": "Atraso Médio",       "value": f"{atr_m:.1f}d",
         "sub": f"máx. {atr_mx:.0f}d",
         "variant": "neg" if atr_m > 30 else "ink"},
        {"label": "Volume Histórico",   "value": formatar_moeda(vlr_t, casas=0),
         "sub": f"ticket {formatar_moeda(vlr_m, casas=0)}", "variant": "ink"},
    ])


def _render_exports(cnpj, uf, valor, resultado, clf, nivel_cont, score, lastro):
    dh = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    excel = gerar_excel_parecer(cnpj=cnpj, data_hora=dh, valor=valor,
                                resultado=resultado, classificacao=clf)
    pdf   = gerar_pdf_auditoria(cnpj=cnpj, valor=valor, resultado=resultado,
                                rating=clf.rating, risco_rede=nivel_cont,
                                data_hora=dh, resultado_lastro=lastro)
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.download_button("⬇ Parecer Excel", data=excel,
            file_name=f"Parecer_{cnpj[:8]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
    with col2:
        st.download_button("⬇ Dossiê PDF (SHA-256)", data=pdf,
            file_name=f"Dossie_{cnpj[:8]}.pdf",
            mime="application/pdf", use_container_width=True, type="primary")
    registrar_precificacao(cnpj=cnpj, uf=uf, score=score,
                           rating=clf.rating, vp=resultado.valor_presente)


# =============================================================================
# Contexto Nuclea — posição do sacado na base
# =============================================================================

def _render_contexto_nuclea(df_carteira: pd.DataFrame, cnpj: str,
                             score: float, rating: str, uf: str) -> None:
    """Compara o sacado com a base Nuclea em 3 dimensões."""
    from utils.formatters import formatar_percentual

    n_total = len(df_carteira)
    if n_total == 0:
        st.info("Base Nuclea não disponível para comparação.")
        return

    # Percentil geral
    pct = percentil_na_carteira(score, df_carteira["score_calculado"])
    scores = df_carteira["score_calculado"]
    media_geral = float(scores.mean())

    # Comparação por UF
    df_uf = df_carteira[df_carteira["uf"] == uf]["score_calculado"]
    media_uf = float(df_uf.mean()) if len(df_uf) > 0 else None

    # Comparação por rating (sacados com mesmo rating)
    df_rating = df_carteira[df_carteira["rating_calculado"] == rating]["score_calculado"]
    media_rating = float(df_rating.mean()) if len(df_rating) > 0 else None
    pct_mesmo_rating = len(df_rating) / n_total * 100 if n_total > 0 else 0

    st.markdown("Posição deste sacado na base Nuclea")

    # 3 comparações em cards
    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        delta = score - media_geral
        st.metric(
            label="vs. Base completa",
            value=f"{score:.0f} pts",
            delta=f"{delta:+.0f} pts vs média {media_geral:.0f}",
        )
        st.caption(f"Top {100-pct:.0f}% da base · {n_total} sacados")

    with col2:
        if media_uf:
            delta_uf = score - media_uf
            st.metric(
                label=f"vs. Sacados de {uf}",
                value=f"{score:.0f} pts",
                delta=f"{delta_uf:+.0f} pts vs média {media_uf:.0f}",
            )
            st.caption(f"{len(df_uf)} sacados nesta UF")
        else:
            st.metric(label=f"vs. Sacados de {uf}", value="—")
            st.caption("UF sem dados suficientes")

    with col3:
        if media_rating:
            delta_r = score - media_rating
            st.metric(
                label=f"vs. Rating {rating}",
                value=f"{score:.0f} pts",
                delta=f"{delta_r:+.0f} pts vs média do grupo",
            )
            st.caption(f"{pct_mesmo_rating:.1f}% da base tem rating {rating}")
        else:
            st.metric(label=f"vs. Rating {rating}", value="—")

    section_divider()

    # Distribuição de ratings na base como referência
    st.markdown("Distribuição de ratings na base Nuclea")
    dist = df_carteira["rating_calculado"].value_counts(normalize=True).sort_index()
    from ui.charts import donut_ratings
    st.plotly_chart(donut_ratings(df_carteira), use_container_width=True,
                    config={"displayModeBar": False}, key="iv_ctx_donut")
    st.caption(f"Base completa: {n_total} sacados · score médio {media_geral:.0f} pts")

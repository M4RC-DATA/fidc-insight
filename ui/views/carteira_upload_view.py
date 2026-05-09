"""
View · Minha Carteira — upload, análise e exportação.

Abas após o upload:
  1. Resumo     — visão geral da carteira
  2. Valoração  — RAROC consolidado com data de vencimento
  3. Exportar   — Excel + PDF resumo executivo
"""

from datetime import date, datetime
import io
import numpy as np
import pandas as pd
import streamlit as st

from config.business_rules import CLASSIFICACOES, LGD_PADRAO, LIMITE_POR_SACADO, LIMITE_POR_UF, ORDEM_RATINGS
from domain.risk import hhi_por_uf
from services.bcb_api import buscar_selic
from services.database import buscar_sacados_por_cnpjs
from ui.charts import donut_ratings, histograma_scores, barras_uf
from ui.components import render_callout, render_kpi_row, section_divider
from exports.pdf_generator import gerar_pdf_carteira
from utils.formatters import formatar_moeda, formatar_numero, formatar_percentual, id_curto

_ALIAS_ID    = {"id_cnpj","cnpj","sacado","hash","id_hash","id_pagador","devedor","documento","cpf_cnpj"}
_ALIAS_VALOR = {"valor","valor_face","face","vl_face","vlr_face","value","montante","principal"}
_ALIAS_VENC  = {"vencimento","data_vencimento","dt_venc","maturity","due_date","prazo"}
_RATING_PAR  = {clf[2]: (clf[3], clf[4]) for clf in CLASSIFICACOES}
_D_PAR       = (CLASSIFICACOES[-1][3], CLASSIFICACOES[-1][4])  # fallback rating D — dinâmico


def _detectar(df, aliases):
    m = {c.lower().strip(): c for c in df.columns}
    for a in aliases:
        if a in m: return m[a]
    return None


def _normalizar_id(v):
    v = str(v).strip().lower()
    if len(v) == 64 and all(c in "0123456789abcdef" for c in v): return v
    d = "".join(c for c in v if c.isdigit())
    return d.zfill(14) if d else v


def _precificar(df, df_nuclea, col_id, col_val, col_venc, dt_pad, selic, incluir_nd, nd):
    hoje = date.today()
    df = df.copy()
    df["_id_n"] = df[col_id].astype(str).apply(_normalizar_id)
    df["_val"]  = pd.to_numeric(df[col_val], errors="coerce").fillna(0).clip(lower=0)
    df["_venc"] = (pd.to_datetime(df[col_venc], errors="coerce").dt.date.fillna(dt_pad)
                   if col_venc else pd.Series(dt_pad, index=df.index))

    dn = df_nuclea.copy()
    dn["_id_n"] = dn["id_cnpj"].astype(str).apply(_normalizar_id)
    mg = df.merge(dn[["_id_n","rating_calculado","score_calculado","media_atraso_dias","uf"]].drop_duplicates("_id_n"),
                  on="_id_n", how="inner")

    if incluir_nd and nd:
        nd_n = [_normalizar_id(x) for x in nd]
        df_nd = df[df["_id_n"].isin(nd_n)].copy()
        df_nd["rating_calculado"] = "D"; df_nd["score_calculado"] = 500.0
        df_nd["media_atraso_dias"] = 0.0; df_nd["uf"] = "—"
        mg = pd.concat([mg, df_nd], ignore_index=True)

    if mg.empty: return mg

    face   = mg["_val"]
    atraso = pd.to_numeric(mg.get("media_atraso_dias", 0), errors="coerce").fillna(0).clip(lower=0).round()
    prazo  = mg["_venc"].apply(lambda v: max((v - hoje).days, 1)) + atraso
    p_anos = prazo / 365.0
    premio = mg["rating_calculado"].map({r: p for r,(p,_) in _RATING_PAR.items()}).fillna(_D_PAR[0])
    pd_a   = mg["rating_calculado"].map({r: pd for r,(_,pd) in _RATING_PAR.items()}).fillna(_D_PAR[1])
    taxa   = (selic + premio).round(6)
    vp     = (face / (1 + taxa) ** p_anos).round(2)
    ecl    = face * pd_a * p_anos * LGD_PADRAO
    lucro  = (face - vp) - ecl
    margem = np.where(face > 0, lucro / face * 100, 0.0)

    mg["vlr_nominal_total"] = face
    mg["vp"] = vp; mg["ecl"] = ecl; mg["lucro"] = lucro; mg["margem"] = margem
    return mg


def _metricas(df_calc):
    face_t  = df_calc["vlr_nominal_total"].sum()
    vp_t    = df_calc["vp"].sum()
    ecl_t   = df_calc["ecl"].sum()
    lucro_t = df_calc["lucro"].sum()
    margem  = lucro_t / face_t * 100 if face_t > 0 else 0.0
    hhi     = hhi_por_uf(df_calc)
    pesos   = df_calc["vlr_nominal_total"].clip(lower=0)
    score_m = float((pesos * df_calc["score_calculado"]).sum() / pesos.sum()) if pesos.sum() > 0 else 500.0
    pct_a   = df_calc["rating_calculado"].isin(["A+","A"]).mean() * 100
    rating_dom = df_calc["rating_calculado"].mode().iloc[0] if len(df_calc) else "—"
    return face_t, vp_t, ecl_t, lucro_t, margem, hhi, score_m, pct_a, rating_dom


def render(df_nuclea: pd.DataFrame) -> None:

    st.markdown("### Minha Carteira")

    # ── Upload ──────────────────────────────────────────────────────────
    # Se já tem carteira na sessão, mostrar opção de trocar
    df_sessao = st.session_state.get("df_carteira_upload")
    info_sessao = st.session_state.get("df_carteira_upload_info", {})

    if df_sessao is not None and not df_sessao.empty:
        nome = info_sessao.get("nome_arquivo", "carteira")
        n    = info_sessao.get("n_sacados", len(df_sessao))
        col_info, col_trocar = st.columns([5, 1])
        with col_info:
            st.success(f"Carteira ativa: {nome} · {n} sacados")
        with col_trocar:
            if st.button("Trocar", key="btn_trocar_carteira"):
                st.session_state.pop("df_carteira_upload", None)
                st.session_state.pop("df_carteira_upload_info", None)
                st.rerun()
        df_calc = df_sessao
    else:
        # Formulário de upload
        with st.expander("📋 Formato esperado", expanded=False):
            st.markdown("""
Colunas (nomes flexíveis):

| Campo | Exemplos de nome | Obrigatório |
|---|---|---|
| Identificador | `id_cnpj`, `cnpj`, `hash` | Sim |
| Valor nominal (R$) | `valor`, `valor_face`, `face` | Sim |
| Vencimento | `vencimento`, `data_vencimento` | Não |
            """)

        arq = st.file_uploader("Selecione a planilha", type=["xlsx","xls","csv"])
        if arq is None:
            return

        try:
            df_up = pd.read_csv(arq) if arq.name.lower().endswith(".csv") else pd.read_excel(arq, engine="openpyxl")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}"); return

        col_id  = _detectar(df_up, _ALIAS_ID)
        col_val = _detectar(df_up, _ALIAS_VALOR)
        col_venc= _detectar(df_up, _ALIAS_VENC)

        if not col_id or not col_val:
            st.error(f"Colunas não detectadas. Encontradas: {', '.join(df_up.columns)}"); return

        col_a, col_b = st.columns(2)
        with col_a:
            dt_pad = st.date_input("Vencimento padrão", value=date.today().replace(year=date.today().year+1), min_value=date.today())
        with col_b:
            incluir_nd = st.radio("Sacados não encontrados",
                ["Excluir", "Incluir com rating D"], index=0) == "Incluir com rating D"

        ids_up = df_up[col_id].astype(str).tolist()
        df_enc, nd = buscar_sacados_por_cnpjs(df_nuclea, ids_up)
        n_tot = len(ids_up); n_enc = len(df_enc); n_nd = len(nd)

        if n_nd == n_tot and not incluir_nd:
            st.error(f"Nenhum dos {n_tot} identificadores foi encontrado na base Nuclea."); return
        if n_nd > 0:
            render_callout(f"{n_enc} de {n_tot} encontrados · {n_nd} não encontrados.", tipo="alerta")
            with st.expander(f"Ver {n_nd} não encontrado(s)"):
                st.dataframe(pd.DataFrame({"Identificador": nd}), use_container_width=True, hide_index=True)
        else:
            render_callout(f"Todos os {n_tot} encontrados na base Nuclea.", tipo="destaque")

        selic = buscar_selic()
        with st.spinner("Precificando…"):
            df_calc = _precificar(df_up, df_nuclea, col_id, col_val, col_venc, dt_pad, selic, incluir_nd, nd)

        if df_calc.empty:
            st.error("Sem dados suficientes."); return

        st.session_state["df_carteira_upload"] = df_calc
        st.session_state["df_carteira_upload_info"] = {
            "nome_arquivo": arq.name, "n_sacados": len(df_calc),
            "n_encontrados": n_enc, "n_nao_encontrados": n_nd,
        }
        st.session_state["selic_carteira"] = buscar_selic()

    # ── Abas de resultado ────────────────────────────────────────────────
    section_divider()
    face_t, vp_t, ecl_t, lucro_t, margem, hhi, score_m, pct_a, rating_dom = _metricas(df_calc)

    aba_resumo, aba_valorizacao, aba_exportar, aba_bench = st.tabs(["Resumo", "Valoração RAROC", "Exportar", "Benchmark"])

    # ── ABA 1: RESUMO ────────────────────────────────────────────────────
    with aba_resumo:
        if margem >= 15:
            render_callout(f"Carteira saudável — margem {margem:.1f}%, score médio {score_m:.0f} pts.", tipo="destaque")
        elif margem >= 8:
            render_callout(f"Carteira estável — margem {margem:.1f}%.", tipo="info")
        else:
            render_callout(f"Margem baixa ({margem:.1f}%) — revise a composição.", tipo="alerta")

        render_kpi_row([
            {"label": "Sacados",        "value": formatar_numero(len(df_calc)),
             "sub": f"score médio {score_m:.0f} pts", "variant": "accent"},
            {"label": "Score Nuclea",   "value": f"{score_m:.0f}",
             "sub": "ponderado por volume", "variant": "premium"},
            {"label": "Grau de Invest.","value": f"{pct_a:.1f}%",
             "sub": "sacados A+/A", "variant": "pos" if pct_a >= 60 else "cau"},
            {"label": "HHI Geográfico", "value": f"{hhi:.3f}",
             "sub": "diversificado" if hhi < 0.15 else "moderado" if hhi < 0.25 else "concentrado",
             "variant": "pos" if hhi < 0.15 else "cau" if hhi < 0.25 else "neg"},
        ])

        col1, col2 = st.columns(2, gap="medium")
        with col1:
            st.markdown("Mix de Risco")
            st.plotly_chart(donut_ratings(df_calc), key="carteiraupload_chart_1", use_container_width=True, config={"displayModeBar": False})
        with col2:
            st.markdown("Score Nuclea")
            st.plotly_chart(histograma_scores(df_calc), key="carteiraupload_chart_2", use_container_width=True, config={"displayModeBar": False})

        with st.expander("▶ Concentração geográfica"):
            st.plotly_chart(barras_uf(df_calc), key="carteiraupload_chart_3", use_container_width=True, config={"displayModeBar": False})

        with st.expander("▶ Ver todos os sacados"):
            cols = [c for c in ["id_cnpj","uf","rating_calculado","score_calculado","vlr_nominal_total","vp","margem"] if c in df_calc.columns]
            df_show = df_calc[cols].copy()
            if "id_cnpj" in df_show.columns:
                df_show["id_cnpj"] = df_show["id_cnpj"].apply(id_curto)
            st.dataframe(df_show.rename(columns={
                "id_cnpj":"Sacado","uf":"UF","rating_calculado":"Rating",
                "score_calculado":"Score","vlr_nominal_total":"Face (R$)",
                "vp":"VP (R$)","margem":"Margem (%)"
            }), use_container_width=True, hide_index=True, height=350)

    # ── ABA 2: VALORAÇÃO ─────────────────────────────────────────────────
    with aba_valorizacao:
        st.markdown("Informe a data de vencimento do fundo para calcular o RAROC consolidado.")
        with st.form("form_valorizacao_carteira"):
            col_a, col_b = st.columns(2)
            with col_a:
                dt_venc = st.date_input("Vencimento do fundo", value=None, min_value=date.today())
            with col_b:
                valor_override = st.number_input("Valor total (R$) — opcional",
                    min_value=0.0, value=0.0, step=100_000.0, format="%.2f",
                    help="0 = usa os valores reais")
            calcular = st.form_submit_button("Calcular →", type="primary", use_container_width=True)

        if calcular:
            if dt_venc is None:
                st.warning("Informe a data de vencimento.")
            else:
                with st.spinner("Calculando…"):
                    from ui.views.carteira_view import render as render_valorizacao
                    render_valorizacao(
                        df_carteira=df_calc,
                        data_vencimento_fundo=dt_venc,
                        valor_total_override=valor_override,
                    )

    # ── ABA 3: EXPORTAR ──────────────────────────────────────────────────
    with aba_exportar:
        st.markdown("Exporte os dados da carteira analisada.")
        section_divider()

        col1, col2 = st.columns(2, gap="medium")

        # Excel
        with col1:
            st.markdown("Excel — detalhe por sacado")
            buf = io.BytesIO()
            cols_exp = [c for c in ["id_cnpj","uf","rating_calculado","score_calculado",
                                     "vlr_nominal_total","vp","ecl","lucro","margem"] if c in df_calc.columns]
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_calc[cols_exp].to_excel(w, sheet_name="Carteira", index=False)
                pd.DataFrame([{
                    "Gerado em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Sacados": len(df_calc),
                    "Face total (R$)": face_t,
                    "VP total (R$)": vp_t,
                    "ECL (R$)": ecl_t,
                    "Lucro RAROC (R$)": lucro_t,
                    "Margem (%)": margem,
                }]).to_excel(w, sheet_name="Consolidado", index=False)
            st.download_button(
                "⬇ Baixar Excel",
                data=buf.getvalue(),
                file_name=f"carteira_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # PDF
        with col2:
            st.markdown("PDF — resumo executivo")
            dh = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            nome_arq = info_sessao.get("nome_arquivo", "carteira")
            pdf_bytes = gerar_pdf_carteira(
                n_sacados=len(df_calc),
                face_total=face_t, vp_total=vp_t, ecl_total=ecl_t,
                lucro_total=lucro_t, margem=margem, score_medio=score_m,
                rating_dom=rating_dom, hhi=hhi, pct_a=pct_a,
                data_hora=dh, nome_arquivo=nome_arq,
            )
            st.download_button(
                "⬇ Baixar PDF",
                data=pdf_bytes,
                file_name=f"resumo_carteira_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )


    # ── ABA 4: BENCHMARK ─────────────────────────────────────────────────
    with aba_bench:
        from ui.views.nuclea_base_view import render as render_benchmark
        render_benchmark(df_nuclea)
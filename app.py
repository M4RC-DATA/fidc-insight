"""FIDC Insight · Entry Point"""

import streamlit as st
from config.settings import APP_ICON, APP_TITLE
from services.auth import usuario_autenticado, logout
from services.database import carregar_carteira
from services.logger import get_logger
from ui.styles import aplicar_tema
from ui.views import (
    home_view, carteira_upload_view, carteira_view,
    individual_view, macro_view, nuclea_base_view,
    audit_view, admin_users_view,
)

logger = get_logger(__name__)

st.set_page_config(
    page_title=f"{APP_TITLE} | Data Verse",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _esconder_sidebar():
    st.markdown("""
    <style>
    [data-testid="stSidebar"]         { display: none !important; }
    [data-testid="collapsedControl"]  { display: none !important; }
    #MainMenu                         { display: none !important; }
    footer                            { display: none !important; }
    header                            { display: none !important; }
    .block-container { padding-top: 2rem !important; max-width: 960px; }
    </style>
    """, unsafe_allow_html=True)


def _topbar_com_nav(usuario, pagina_atual: str):
    """Barra superior com logo + navegação breadcrumb + sair."""
    labels = {
        "home": "Início",
        "individual": "Consulta Individual",
        "carteira_upload": "Minha Carteira",
        "macro": "Visão Geral",
        "carteira": "Valoração",
        "nuclea_base": "Núclea",
        "auditoria": "Auditoria",
        "admin": "Administração",
    }
    pagina_label = labels.get(pagina_atual, "")

    col_logo, col_mid, col_user = st.columns([2, 5, 2])

    with col_logo:
        if st.button("← FIDC Insight", key="btn_home_top", type="secondary"):
            st.session_state["pagina"] = "home"
            st.rerun()

    with col_mid:
        if pagina_label and pagina_atual != "home":
            st.markdown(
                f'<div style="text-align:center;font-size:.85rem;color:#64748B;'
                f'padding:.4rem 0">{pagina_label}</div>',
                unsafe_allow_html=True,
            )

    with col_user:
        if st.button(f"Sair ({usuario.papel})", key="btn_sair_top",
                     use_container_width=True, type="secondary"):
            logout()
            st.rerun()

    st.markdown('<hr style="margin:.5rem 0 1.5rem;border-color:#E2E8F0">', unsafe_allow_html=True)


def main() -> None:
    aplicar_tema()
    _esconder_sidebar()

    # Autenticação
    from ui.views.login_view import render as render_login
    usuario = usuario_autenticado()
    if usuario is None:
        render_login()
        st.stop()

    # Estado de navegação
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "home"

    pagina = st.session_state["pagina"]

    # Páginas sem topbar (home tem o seu próprio)
    if pagina == "home":
        _esconder_sidebar()
        home_view.render(usuario)
        return

    # Topbar de navegação para todas as outras páginas
    _topbar_com_nav(usuario, pagina)

    # Páginas sem BigQuery
    if pagina == "auditoria":
        audit_view.render()
        return
    if pagina == "admin":
        admin_users_view.render()
        return

    # Carregar dados
    with st.spinner("Carregando dados Núclea…"):
        df_nuclea = carregar_carteira()

    if df_nuclea is None or df_nuclea.empty:
        st.error("Não foi possível carregar a base Núclea. Verifique a conexão com o BigQuery.")
        st.stop()

    df_upload = st.session_state.get("df_carteira_upload")
    modo_upload = df_upload is not None and not df_upload.empty
    df_ativo = df_upload if modo_upload else df_nuclea

    # Roteamento
    if pagina == "individual":
        _render_individual_inline(df_nuclea)

    elif pagina == "carteira_upload":
        carteira_upload_view.render(df_nuclea)

    elif pagina == "macro":
        if modo_upload:
            macro_view.render(df_ativo)
        else:
            st.info("Nenhuma carteira carregada. Use Minha Carteira para fazer upload.")

    elif pagina == "carteira":
        if modo_upload:
            _render_valorizacao_inline(df_ativo)
        else:
            st.info("Nenhuma carteira carregada. Use Minha Carteira para fazer upload.")

    elif pagina == "nuclea_base":
        nuclea_base_view.render(df_nuclea)


def _render_individual_inline(df_nuclea):
    """Formulário + resultado na tela principal, sem sidebar.
    Resultado persiste na sessão — não é perdido ao navegar."""
    from datetime import date

    st.markdown("### Consulta Individual")

    # Formulário — mostra sempre no topo
    with st.form("form_individual"):
        col1, col2, col3 = st.columns(3)
        with col1:
            cnpj = st.text_input("Identificador do sacado",
                                  placeholder="Hash SHA-256 ou CNPJ")
        with col2:
            valor = st.number_input("Valor nominal (R$)", min_value=0.0,
                                     value=0.0, step=5_000.0, format="%.2f")
        with col3:
            dt_venc = st.date_input("Vencimento", value=None,
                                     min_value=date.today())
        submitted = st.form_submit_button("Analisar →", type="primary",
                                           use_container_width=True)

    if submitted:
        if not cnpj.strip() or valor <= 0 or dt_venc is None:
            st.warning("Preencha todos os campos para continuar.")
            return
        # Salvar parâmetros da consulta na sessão
        st.session_state["ultima_consulta"] = {
            "cnpj": cnpj.strip(), "valor": valor, "dt_venc": dt_venc,
        }

    # Restaurar e exibir resultado da última consulta (persiste entre navegações)
    ultima = st.session_state.get("ultima_consulta")
    if ultima:
        with st.spinner("Analisando…"):
            individual_view.render(
                df_carteira=df_nuclea,
                cnpj=ultima["cnpj"],
                valor=ultima["valor"],
                data_vencimento=ultima["dt_venc"],
            )


def _render_valorizacao_inline(df_ativo):
    """Formulário de valoração na tela principal."""
    from datetime import date

    st.markdown("### Valoração da Carteira")
    with st.form("form_valorizacao"):
        col1, col2 = st.columns(2)
        with col1:
            dt_venc = st.date_input("Vencimento do fundo", value=None,
                                     min_value=date.today())
        with col2:
            valor_total = st.number_input(
                "Valor total (R$) — opcional",
                min_value=0.0, value=0.0, step=100_000.0, format="%.2f",
                help="0 = usa os valores reais do BigQuery",
            )
        submitted = st.form_submit_button("Calcular →", type="primary",
                                           use_container_width=True)

    if submitted:
        if dt_venc is None:
            st.warning("Informe a data de vencimento do fundo.")
            return
        with st.spinner("Calculando…"):
            carteira_view.render(
                df_carteira=df_ativo,
                data_vencimento_fundo=dt_venc,
                valor_total_override=valor_total,
            )


main()

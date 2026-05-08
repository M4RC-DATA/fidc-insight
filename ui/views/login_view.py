"""
Tela de Login · FIDC Insight — Data Verse.
Estrutura original preservada. Apenas identidade Data Verse aplicada.
"""

from __future__ import annotations

import streamlit as st

from config.auth_rules import PAPEIS_DESCRICAO, Papel
from services.auth import LoginErro, autenticar
from ui.components import _html


def _css_login() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

            section[data-testid="stSidebar"] {
                display: none !important;
                visibility: hidden !important;
                width: 0 !important;
                min-width: 0 !important;
                max-width: 0 !important;
            }
            [data-testid="collapsedControl"],
            [data-testid="stSidebarCollapsedControl"] { display: none !important; }

            /* Fundo Data Verse — gradiente sutil ciano/roxo */
            .stApp {
                background: #F8FAFC !important;
                background-image:
                    radial-gradient(ellipse at 15% 70%, rgba(0,188,212,.07) 0%, transparent 50%),
                    radial-gradient(ellipse at 85% 15%, rgba(124,58,237,.06) 0%, transparent 50%) !important;
                font-family: 'DM Sans', sans-serif !important;
            }

            .block-container {
                padding-top: 3rem !important;
                padding-bottom: 3rem !important;
                max-width: 440px !important;
            }

            /* Card — original com borda-topo gradiente Data Verse */
            .login-card {
                background: #FFFFFF;
                border: 1px solid #E3E8F0;
                border-radius: 14px;
                padding: 2.25rem 2rem 2rem 2rem;
                box-shadow: 0 20px 60px -20px rgba(10, 22, 40, 0.15);
                overflow: hidden;
                position: relative;
            }
            .login-card::before {
                content: '';
                display: block;
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 3px;
                background: linear-gradient(90deg, #00BCD4 0%, #7C3AED 100%);
            }

            /* Logo Data Verse no lugar do FI */
            .login-brand {
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 0.25rem;
            }
            .login-brand-name {
                font-weight: 700;
                font-size: 1.1rem;
                color: #0A1628;
                letter-spacing: -0.01em;
            }
            .login-brand-sub {
                font-size: 0.7rem;
                color: #94A3B8;
                margin-top: 1px;
            }

            /* Kicker em ciano Data Verse */
            .login-kicker {
                text-transform: uppercase;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.7rem;
                color: #0891B2;
                letter-spacing: 0.1em;
                margin: 1.25rem 0 0.25rem 0;
            }
            .login-title {
                font-weight: 700;
                font-size: 1.45rem;
                color: #0A1628;
                letter-spacing: -0.02em;
                line-height: 1.2;
            }
            .login-sub {
                font-size: 0.88rem;
                color: #57627A;
                margin-top: 0.45rem;
                line-height: 1.5;
            }
            .login-foot {
                margin-top: 1.25rem;
                padding-top: 1rem;
                border-top: 1px solid #EEF1F6;
                font-size: 0.72rem;
                color: #7C8CA8;
                line-height: 1.6;
            }
            .login-foot code {
                font-family: 'JetBrains Mono', monospace;
                background: #F3F5F9;
                padding: 0.08rem 0.35rem;
                border-radius: 3px;
                font-size: 0.72rem;
                color: #2D3A52;
            }

            /* Form — original */
            .stForm {
                border: none !important;
                padding: 0 !important;
                margin-top: 1.4rem !important;
                background: transparent !important;
            }
            .stForm label {
                font-size: 0.78rem !important;
                color: #2D3A52 !important;
                font-weight: 600 !important;
                letter-spacing: 0.02em !important;
                margin-bottom: 0.35rem !important;
            }
            .stForm .stTextInput input {
                height: 46px !important;
                padding: 0.65rem 0.95rem !important;
                font-size: 0.95rem !important;
                border: 1px solid #D7DDE7 !important;
                border-radius: 10px !important;
                background: #FFFFFF !important;
                color: #0A1628 !important;
                box-shadow: none !important;
                transition: border-color 0.15s ease, box-shadow 0.15s ease;
            }
            .stForm .stTextInput input::placeholder {
                color: #A8B1C2 !important;
                opacity: 1 !important;
            }
            /* Foco ciano Data Verse no lugar do azul */
            .stForm .stTextInput input:focus {
                border-color: #00BCD4 !important;
                box-shadow: 0 0 0 3px rgba(0,188,212,0.15) !important;
                outline: none !important;
            }
            .stForm .stTextInput div[data-baseweb="input"] {
                border: none !important;
                background: transparent !important;
                padding: 0 !important;
            }
            .stForm .stTextInput [data-baseweb="input"] button {
                background: transparent !important;
                border: none !important;
                color: #7C8CA8 !important;
                padding: 0 0.6rem !important;
                height: 46px !important;
                cursor: pointer !important;
                border-radius: 8px !important;
                transition: color 0.15s ease, background 0.15s ease;
            }
            .stForm .stTextInput [data-baseweb="input"] button:hover {
                color: #0891B2 !important;
                background: rgba(0,188,212,0.08) !important;
            }
            .stForm .stTextInput [data-baseweb="input"] button svg {
                width: 18px !important;
                height: 18px !important;
                fill: currentColor !important;
            }
            .stForm .stTextInput {
                margin-bottom: 0.85rem !important;
            }
            /* Botão Entrar — gradiente Data Verse no lugar do preto */
            .stForm button[kind="primaryFormSubmit"],
            .stForm .stFormSubmitButton button {
                height: 46px !important;
                border-radius: 10px !important;
                font-weight: 600 !important;
                font-size: 0.95rem !important;
                background: linear-gradient(135deg, #0891B2 0%, #7C3AED 100%) !important;
                color: #FFFFFF !important;
                border: none !important;
                box-shadow: 0 2px 8px rgba(8,145,178,.25) !important;
                transition: all 0.15s ease !important;
                margin-top: 0.25rem !important;
            }
            .stForm button[kind="primaryFormSubmit"]:hover,
            .stForm .stFormSubmitButton button:hover {
                box-shadow: 0 8px 20px -6px rgba(8,145,178,.45) !important;
                transform: translateY(-1px);
            }
            .stForm button[kind="primaryFormSubmit"]:active,
            .stForm .stFormSubmitButton button:active {
                transform: translateY(0);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    _css_login()

    _html(
        '<div class="login-card">'
        '<div class="login-brand">'
        '<svg width="28" height="28" viewBox="0 0 32 32" fill="none">'
        '<path d="M4 4 L16 28 L28 4" stroke="#00BCD4" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        '<path d="M4 4 L16 28" stroke="#7C3AED" stroke-width="5" stroke-linecap="round" fill="none"/>'
        '</svg>'
        '<div>'
        '<div class="login-brand-name">Data Verse</div>'
        '<div class="login-brand-sub">Grupo de Data Science — FIAP</div>'
        '</div>'
        '</div>'
        '<div class="login-kicker">FIDC Insight</div>'
        '<div class="login-title">Acesse sua conta</div>'
        '<div class="login-sub">Informe suas credenciais corporativas para '
        'acessar a análise de crédito dos FIDCs.</div>'
        '</div>'
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(
            "Usuário",
            placeholder="ex.: nielsen.mgbr",
            autocomplete="username",
        )
        senha = st.text_input(
            "Senha",
            type="password",
            placeholder="••••••••",
            autocomplete="current-password",
        )
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        submit = st.form_submit_button(
            "Entrar",
            type="primary",
            use_container_width=True,
        )

    if submit:
        try:
            usuario = autenticar(username, senha)
            st.success(f"Bem-vindo, {usuario.nome.split()[0]}.")
            st.rerun()
        except LoginErro as erro:
            st.error(str(erro))

    papeis_lista = "".join(
        f"<div>· <code>{p.value}</code> — {PAPEIS_DESCRICAO[p]}</div>"
        for p in Papel
    )
    _html(
        '<div class="login-foot">'
        '<strong>Papéis do sistema</strong><br>'
        f'{papeis_lista}'
        '<div style="margin-top: 0.65rem; opacity: 0.7;">'
        'Para o primeiro acesso, execute <code>python seed_users.py</code> '
        'na raiz do projeto.'
        '</div>'
        '</div>'
    )

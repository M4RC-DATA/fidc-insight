"""
Tela de Administração de Usuários.

Visível apenas para o papel ``admin``. Permite:
  * Listar todos os usuários (ativos e inativos)
  * Criar novo usuário (aplicando política de senha)
  * Ativar / desativar conta
  * Resetar senha

Operações de CRUD não geram evento de auditoria porque o escopo
acordado para o audit log é apenas **autenticação** (login, logout,
falhas, lockout). Mudanças administrativas são logadas pelo módulo
``services.logger`` via stdout.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from config.auth_rules import PAPEIS_DESCRICAO, Papel
from services.auth import (
    alterar_ativo,
    alterar_senha,
    criar_usuario,
    listar_usuarios,
    validar_politica_senha,
)
from ui.components import (
    render_page_header,
    render_section_header,
    section_divider,
)


# =============================================================================
# Listagem
# =============================================================================
def _render_listagem() -> None:
    usuarios = listar_usuarios(apenas_ativos=False)
    if not usuarios:
        st.info("Nenhum usuário cadastrado. Execute `python seed_users.py`.")
        return

    df = pd.DataFrame(
        [
            {
                "Usuário": u.username,
                "Nome": u.nome,
                "Papel": u.papel,
                "Ativo": "Sim" if u.ativo else "Não",
                "Email": u.email or "—",
                "Último login": (
                    u.ultimo_login.strftime("%Y-%m-%d %H:%M UTC")
                    if u.ultimo_login
                    else "—"
                ),
            }
            for u in usuarios
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================================
# Criar usuário
# =============================================================================
def _render_criar() -> None:
    with st.form("criar_usuario", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Usuário (login)")
            nome = st.text_input("Nome completo")
            email = st.text_input("Email (opcional)")
        with c2:
            papel = st.selectbox(
                "Papel",
                options=[p.value for p in Papel],
                format_func=lambda v: f"{v} · {PAPEIS_DESCRICAO[Papel(v)]}",
            )
            senha = st.text_input(
                "Senha inicial",
                type="password",
                help="Mínimo 8 caracteres, com maiúscula e dígito.",
            )
            senha2 = st.text_input(
                "Confirmar senha",
                type="password",
            )

        submit = st.form_submit_button("Criar usuário", type="primary")

    if not submit:
        return

    if not username or not senha or not nome:
        st.error("Usuário, nome e senha são obrigatórios.")
        return

    if senha != senha2:
        st.error("As senhas não conferem.")
        return

    erro = validar_politica_senha(senha)
    if erro:
        st.error(erro)
        return

    try:
        u = criar_usuario(
            username=username.strip(),
            senha=senha,
            nome=nome.strip(),
            papel=papel,
            email=email.strip() or None,
        )
        st.success(f"Usuário '{u.username}' criado com papel '{u.papel}'.")
    except ValueError as exc:
        st.error(str(exc))


# =============================================================================
# Ativar/Desativar
# =============================================================================
def _render_ativacao() -> None:
    usuarios = listar_usuarios(apenas_ativos=False)
    if not usuarios:
        return

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        alvo = st.selectbox(
            "Selecione o usuário",
            options=[u.username for u in usuarios],
            key="ativa_alvo",
            format_func=lambda x: (
                f"{x} · {next((u.papel for u in usuarios if u.username == x), '')}"
                f" · {'ativo' if next((u.ativo for u in usuarios if u.username == x), False) else 'inativo'}"
            ),
        )
    with c2:
        if st.button("Desativar", use_container_width=True, key="desativar_btn"):
            alterar_ativo(alvo, ativo=False)
            st.success(f"Usuário '{alvo}' desativado.")
            st.rerun()
    with c3:
        if st.button("Reativar", use_container_width=True, key="reativar_btn"):
            alterar_ativo(alvo, ativo=True)
            st.success(f"Usuário '{alvo}' reativado.")
            st.rerun()


# =============================================================================
# Reset de senha
# =============================================================================
def _render_reset_senha() -> None:
    usuarios = listar_usuarios(apenas_ativos=True)
    if not usuarios:
        return

    with st.form("reset_senha", clear_on_submit=True):
        c1, c2 = st.columns([1, 1])
        with c1:
            alvo = st.selectbox(
                "Usuário",
                options=[u.username for u in usuarios],
                key="reset_alvo",
            )
        with c2:
            nova = st.text_input(
                "Nova senha",
                type="password",
            )
        submit = st.form_submit_button("Aplicar nova senha", type="primary")

    if submit:
        if not nova:
            st.error("Informe a nova senha.")
            return
        try:
            alterar_senha(alvo, nova)
            st.success(f"Senha de '{alvo}' alterada. O lockout (se havia) foi liberado.")
        except ValueError as exc:
            st.error(str(exc))


# =============================================================================
# Main
# =============================================================================
def render() -> None:
    """Renderiza a tela de admin de usuários."""
    render_page_header(
        kicker="Administração · Controle de Acesso",
        titulo="Gerência de Usuários",
        subtitulo=(
            "Crie, desative ou resete senhas de usuários da plataforma. "
            "Operações aqui afetam quem pode acessar o FIDC Insight e com qual papel."
        ),
        data_hora=datetime.utcnow().strftime("%d/%m/%Y · %H:%M UTC"),
    )

    render_section_header(
        "Usuários cadastrados",
        "Lista completa, incluindo contas desativadas.",
    )
    _render_listagem()

    section_divider()
    render_section_header(
        "Criar novo usuário",
        "A senha inicial precisa respeitar a política (8+ chars, maiúscula e dígito).",
    )
    _render_criar()

    section_divider()
    render_section_header(
        "Ativar / Desativar",
        "Usuários desativados não conseguem mais se autenticar. O histórico é preservado.",
    )
    _render_ativacao()

    section_divider()
    render_section_header(
        "Resetar senha",
        "Substitui a senha atual e libera eventual lockout por tentativas falhas.",
    )
    _render_reset_senha()

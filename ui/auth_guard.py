"""
Guard de autenticação.

Ponto de entrada de todo o app: antes de qualquer view ser executada,
verificamos se há uma sessão válida em ``st.session_state``. Se não
houver, redirecionamos o usuário para a tela de login.

Também centraliza a checagem de permissão por view — se o papel do
usuário não pode acessar a página escolhida, mostramos uma tela de
"acesso negado" em vez da view original.
"""

from __future__ import annotations

import streamlit as st

from config.auth_rules import PERMISSOES_VIEWS, Papel, pode_acessar
from services.auth import Usuario, usuario_autenticado
from ui.components import render_callout, render_page_header
from ui.views import login_view


def exigir_login() -> Usuario:
    """Garante que há um usuário autenticado na sessão.

    Se não houver, renderiza a tela de login e interrompe a execução do
    script (``st.stop()``). Se houver, retorna o :class:`Usuario` logado.
    """
    usuario = usuario_autenticado()
    if usuario is None:
        login_view.render()
        st.stop()
    return usuario  # type: ignore[return-value]


def exigir_acesso(usuario: Usuario, view: str) -> None:
    """Bloqueia a execução se o papel do usuário não pode acessar a view.

    Em vez de derrubar o app, mostra um card com o motivo do bloqueio
    para que o usuário saiba por que não chegou onde queria.
    """
    if pode_acessar(usuario.papel, view):
        return

    render_page_header(
        kicker="Acesso Restrito",
        titulo="Você não tem permissão para esta área",
        subtitulo=(
            f"Seu papel atual é “{usuario.papel}”. Para ganhar acesso a esta "
            "funcionalidade, solicite elevação ao administrador."
        ),
    )
    render_callout(
        "O FIDC Insight segue o princípio de menor privilégio: cada papel "
        "enxerga apenas as áreas necessárias para sua função. Isso reduz a "
        "superfície de risco e é auditável pela trilha da plataforma.",
        tipo="warning",
    )
    st.stop()


def views_permitidas(usuario: Usuario) -> set[str]:
    """Retorna o conjunto de views que o usuário pode acessar."""
    try:
        return PERMISSOES_VIEWS[Papel(usuario.papel)]
    except (ValueError, KeyError):
        return set()

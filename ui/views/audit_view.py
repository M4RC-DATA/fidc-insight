"""
Tela de Auditoria.

Dashboard read-only com:
  * KPIs da janela (24h por padrão) — total de eventos, logins ok/falha,
    bloqueios e usuários distintos.
  * Filtros combináveis (usuário, ação, severidade, janela temporal).
  * Tabela dos eventos mais recentes (limite configurável).
  * Export CSV para evidência externa.

Visível apenas para os papéis ``auditor`` e ``admin`` — o
:mod:`ui.auth_guard` já faz o bloqueio de acesso em ``app.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from config.auth_rules import Acao, Severidade
from config.settings import PROJECT_ROOT
from services.audit import exportar_csv, listar_eventos, resumo_metricas
from ui.components import (
    render_kpi_row,
    render_page_header,
    render_section_header,
    section_divider,
)


# =============================================================================
# KPIs da janela
# =============================================================================
def _render_kpis(janela_horas: int) -> None:
    m = resumo_metricas(janela_horas=janela_horas)
    render_kpi_row(
        [
            {
                "label": "Total de eventos",
                "value": f"{m['total_eventos']:,}".replace(",", "."),
                "sub": f"últimas {janela_horas}h",
                "variant": "ink",
            },
            {
                "label": "Logins bem-sucedidos",
                "value": f"{m['logins_ok']:,}".replace(",", "."),
                "sub": "acessos normais",
                "variant": "pos",
            },
            {
                "label": "Falhas de login",
                "value": f"{m['logins_falha']:,}".replace(",", "."),
                "sub": "senha inválida / não existe",
                "variant": "cau",
            },
            {
                "label": "Contas bloqueadas",
                "value": f"{m['contas_bloqueadas']:,}".replace(",", "."),
                "sub": "excedeu tentativas",
                "variant": "neg",
            },
        ],
        cols=4,
    )


# =============================================================================
# Filtros
# =============================================================================
def _render_filtros() -> dict:
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1])

    with c1:
        usuario = st.text_input(
            "Usuário",
            value="",
            placeholder="ex.: admin",
            help="Filtro exato (case-sensitive).",
        )
    with c2:
        acao = st.selectbox(
            "Ação",
            options=["(todas)"] + [a.value for a in Acao],
        )
    with c3:
        severidade = st.selectbox(
            "Severidade",
            options=["(todas)"] + [s.value for s in Severidade],
        )
    with c4:
        janela = st.selectbox(
            "Janela",
            options=["24h", "7 dias", "30 dias", "Tudo"],
            index=0,
        )

    # Converte janela para (desde, ate)
    agora = datetime.utcnow()
    janelas_map = {
        "24h": agora - timedelta(hours=24),
        "7 dias": agora - timedelta(days=7),
        "30 dias": agora - timedelta(days=30),
        "Tudo": None,
    }
    desde = janelas_map[janela]

    return {
        "usuario": usuario.strip() or None,
        "acao": None if acao == "(todas)" else acao,
        "severidade": None if severidade == "(todas)" else severidade,
        "desde": desde,
        "janela_label": janela,
    }


# =============================================================================
# Tabela
# =============================================================================
def _render_tabela(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Nenhum evento encontrado para os filtros aplicados.")
        return

    df_display = df.copy()
    df_display["timestamp"] = (
        pd.to_datetime(df_display["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    )
    df_display = df_display.rename(
        columns={
            "id": "#",
            "timestamp": "Quando (UTC)",
            "usuario": "Usuário",
            "acao": "Ação",
            "severidade": "Severidade",
            "detalhes": "Detalhes",
            "sessao_id": "Sessão",
        }
    )

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "Quando (UTC)": st.column_config.TextColumn(width="medium"),
            "Usuário": st.column_config.TextColumn(width="small"),
            "Ação": st.column_config.TextColumn(width="medium"),
            "Severidade": st.column_config.TextColumn(width="small"),
            "Detalhes": st.column_config.TextColumn(width="large"),
            "Sessão": st.column_config.TextColumn(width="small"),
        },
    )


# =============================================================================
# Série temporal (linha de eventos por hora)
# =============================================================================
def _render_serie(df: pd.DataFrame) -> None:
    if df.empty:
        return

    df_copy = df.copy()
    df_copy["hora"] = pd.to_datetime(df_copy["timestamp"]).dt.floor("h")
    serie = (
        df_copy.groupby(["hora", "severidade"])
        .size()
        .reset_index(name="eventos")
        .pivot(index="hora", columns="severidade", values="eventos")
        .fillna(0)
    )

    # Reordena colunas para sempre ter INFO/WARNING/CRITICAL na mesma ordem
    for col in ("INFO", "WARNING", "CRITICAL"):
        if col not in serie.columns:
            serie[col] = 0
    serie = serie[["INFO", "WARNING", "CRITICAL"]]

    st.line_chart(serie, height=220)


# =============================================================================
# Main
# =============================================================================
def render() -> None:
    """Renderiza a tela de auditoria."""
    render_page_header(
        kicker="Governança · Observabilidade",
        titulo="Trilha de Auditoria",
        subtitulo=(
            "Registro imutável de todos os eventos de autenticação. "
            "Use os filtros para investigar incidentes e exporte em CSV "
            "para auditores externos."
        ),
        data_hora=datetime.utcnow().strftime("%d/%m/%Y · %H:%M UTC"),
    )

    # Converte janela label para horas (usadas nos KPIs)
    janela_default_horas = 24
    _render_kpis(janela_default_horas)
    section_divider()

    # ---------- Filtros ----------
    render_section_header(
        "Filtros",
        "Combine múltiplos filtros. Resultados ordenados do mais recente para o mais antigo.",
    )
    filtros = _render_filtros()

    # ---------- Busca ----------
    df = listar_eventos(
        limite=500,
        usuario=filtros["usuario"],
        acao=filtros["acao"],
        severidade=filtros["severidade"],
        desde=filtros["desde"],
    )

    # ---------- Gráfico ----------
    render_section_header(
        f"Eventos por hora · {filtros['janela_label']}",
        "Granularidade horária por severidade.",
    )
    _render_serie(df)

    # ---------- Tabela ----------
    render_section_header(
        "Eventos recentes",
        f"Mostrando até 500 registros · {len(df)} eventos na janela.",
    )
    _render_tabela(df)

    # ---------- Export ----------
    section_divider()
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Exportar CSV", use_container_width=True):
            destino = (
                PROJECT_ROOT / "exports"
                / f"auditoria_{datetime.utcnow():%Y%m%d_%H%M%S}.csv"
            )
            try:
                caminho = exportar_csv(destino, limite=10_000)
                with open(caminho, "rb") as fh:
                    st.download_button(
                        "Download do CSV",
                        data=fh.read(),
                        file_name=caminho.name,
                        mime="text/csv",
                        use_container_width=True,
                    )
                st.success(f"Arquivo gerado em {caminho.name}.")
            except Exception as exc:
                st.error(f"Falha ao exportar: {exc}")

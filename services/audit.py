"""
Trilha de auditoria imutável · SQLite.

Registra eventos de autenticação do FIDC Insight em ``data/auth.db``
(tabela ``audit_log``). Cada evento guarda:

    - timestamp UTC
    - usuário (ou "anônimo" quando a tentativa é pré-login)
    - ação (vocabulário controlado em ``config.auth_rules.Acao``)
    - detalhes opcionais (JSON serializado)
    - sessao_id (UUID da sessão Streamlit)
    - severidade (INFO | WARNING | CRITICAL)

Escrita é append-only — não existe UPDATE nem DELETE na API pública.
Isso garante integridade da trilha: se o auditor ver um log, ele está
lá desde o momento do evento.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from config.auth_rules import (
    AUTH_DB_PATH,
    Acao,
    SCHEMA_AUDIT_LOG,
    SCHEMA_INDICES,
    SCHEMA_USUARIOS,
    Severidade,
)
from services.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Infra: bootstrap do banco
# =============================================================================
def _garantir_db(caminho: Path = AUTH_DB_PATH) -> Path:
    """Cria o arquivo SQLite e as tabelas caso ainda não existam.

    Idempotente — pode ser chamado em todo boot sem custo.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(caminho) as conn:
        conn.execute(SCHEMA_USUARIOS)
        conn.execute(SCHEMA_AUDIT_LOG)
        for ddl in SCHEMA_INDICES:
            conn.execute(ddl)
        conn.commit()
    return caminho


def _conn(caminho: Path = AUTH_DB_PATH) -> sqlite3.Connection:
    """Abre conexão garantindo que o schema exista."""
    _garantir_db(caminho)
    # check_same_thread=False porque o Streamlit usa múltiplas threads
    # para re-runs. SQLite aceita mas o WAL mode dá mais segurança.
    conn = sqlite3.connect(caminho, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# =============================================================================
# API de escrita
# =============================================================================
def registrar_evento(
    usuario: str,
    acao: Acao | str,
    detalhes: Optional[dict[str, Any]] = None,
    sessao_id: Optional[str] = None,
    severidade: Severidade | str = Severidade.INFO,
) -> None:
    """Grava um evento na trilha de auditoria.

    Args:
        usuario: username do ator (ou "anonimo" para tentativas pré-login).
        acao: uma das constantes de :class:`config.auth_rules.Acao`.
        detalhes: dict opcional com metadados (será serializado em JSON).
        sessao_id: identificador da sessão Streamlit, se houver.
        severidade: INFO | WARNING | CRITICAL.

    Nunca lança exceção para o chamador — falhas de I/O são logadas
    mas não quebram o fluxo da aplicação. A trilha é observabilidade,
    não caminho crítico.
    """
    acao_str = acao.value if isinstance(acao, Acao) else str(acao)
    sev_str = severidade.value if isinstance(severidade, Severidade) else str(severidade)
    detalhes_json = json.dumps(detalhes, ensure_ascii=False) if detalhes else None

    try:
        with _conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                    (timestamp, usuario, acao, detalhes, sessao_id, severidade)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(timespec="seconds"),
                    usuario,
                    acao_str,
                    detalhes_json,
                    sessao_id,
                    sev_str,
                ),
            )
            conn.commit()
        logger.info("audit[%s] %s · %s", sev_str, acao_str, usuario)
    except Exception as exc:  # pragma: no cover — defensivo
        logger.error("Falha ao registrar auditoria (%s): %s", acao_str, exc)


# =============================================================================
# API de leitura — para a tela de auditoria
# =============================================================================
def listar_eventos(
    limite: int = 500,
    usuario: Optional[str] = None,
    acao: Optional[str] = None,
    severidade: Optional[str] = None,
    desde: Optional[datetime] = None,
    ate: Optional[datetime] = None,
) -> pd.DataFrame:
    """Retorna eventos da trilha já ordenados (mais recente primeiro).

    Todos os filtros são opcionais e combináveis. A query usa placeholders
    parametrizados (``?``) — sem risco de SQL injection.
    """
    where_clauses = []
    params: list[Any] = []

    if usuario:
        where_clauses.append("usuario = ?")
        params.append(usuario)
    if acao:
        where_clauses.append("acao = ?")
        params.append(acao)
    if severidade:
        where_clauses.append("severidade = ?")
        params.append(severidade)
    if desde:
        where_clauses.append("timestamp >= ?")
        params.append(desde.isoformat(timespec="seconds"))
    if ate:
        where_clauses.append("timestamp <= ?")
        params.append(ate.isoformat(timespec="seconds"))

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        SELECT id, timestamp, usuario, acao, severidade, detalhes, sessao_id
        FROM audit_log
        {where_sql}
        ORDER BY timestamp DESC
        LIMIT ?
    """
    params.append(int(limite))

    try:
        with _conn() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        # Parse timestamp para facilitar plots
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as exc:
        logger.error("Falha ao ler auditoria: %s", exc)
        return pd.DataFrame(
            columns=["id", "timestamp", "usuario", "acao", "severidade", "detalhes", "sessao_id"]
        )


def resumo_metricas(janela_horas: int = 24) -> dict[str, int]:
    """KPIs da janela (últimas N horas) para o dashboard de auditoria.

    Retorna dict com: total_eventos, logins_ok, logins_falha,
    contas_bloqueadas, usuarios_distintos.
    """
    sql = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN acao = 'LOGIN_OK'         THEN 1 ELSE 0 END) AS logins_ok,
            SUM(CASE WHEN acao = 'LOGIN_FALHA'      THEN 1 ELSE 0 END) AS logins_falha,
            SUM(CASE WHEN acao = 'CONTA_BLOQUEADA'  THEN 1 ELSE 0 END) AS bloqueios,
            COUNT(DISTINCT usuario) AS usuarios
        FROM audit_log
        WHERE timestamp >= datetime('now', ?)
    """
    offset = f"-{int(janela_horas)} hours"
    try:
        with _conn() as conn:
            cur = conn.execute(sql, (offset,))
            row = cur.fetchone()
        return {
            "total_eventos": int(row[0] or 0),
            "logins_ok": int(row[1] or 0),
            "logins_falha": int(row[2] or 0),
            "contas_bloqueadas": int(row[3] or 0),
            "usuarios_distintos": int(row[4] or 0),
        }
    except Exception as exc:
        logger.error("Falha ao calcular métricas de auditoria: %s", exc)
        return {
            "total_eventos": 0, "logins_ok": 0, "logins_falha": 0,
            "contas_bloqueadas": 0, "usuarios_distintos": 0,
        }


def exportar_csv(caminho_saida: Path, limite: int = 10_000) -> Path:
    """Exporta a trilha completa (ou os N mais recentes) em CSV.

    Usado pela tela de auditoria quando o auditor externo pede a
    evidência. O caller escolhe o caminho de saída.
    """
    df = listar_eventos(limite=limite)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho_saida, index=False, encoding="utf-8-sig")
    return caminho_saida

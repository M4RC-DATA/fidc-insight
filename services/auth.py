"""
Autenticação · SQLite + bcrypt.

Este módulo implementa:
  * Hashing de senhas com bcrypt (12 salt rounds — OWASP 2023)
  * Login com bloqueio progressivo após N tentativas falhadas
  * Validação de política de senha
  * CRUD mínimo de usuários (criar, ativar/desativar, listar, trocar senha)
  * Controle de sessão via ``st.session_state`` + timeout por inatividade

A sessão é identificada por um UUID gerado no primeiro login e guardado
em ``st.session_state["auth"]``. O timeout é verificado em cada rerun
(Streamlit recria a execução do script a cada interação).

Toda mudança relevante dispara um evento de auditoria via
:mod:`services.audit` — login ok/falha, lockout, senha alterada, logout.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import bcrypt
import streamlit as st

from config.auth_rules import (
    AUTH_DB_PATH,
    BCRYPT_SALT_ROUNDS,
    BLOQUEIO_MINUTOS,
    MAX_TENTATIVAS_FALHAS,
    Acao,
    Papel,
    SENHA_EXIGE_DIGITO,
    SENHA_EXIGE_ESPECIAL,
    SENHA_EXIGE_MAIUSCULA,
    SENHA_MIN_CHARS,
    SESSAO_TIMEOUT_MINUTOS,
    Severidade,
)
from services.audit import _conn, _garantir_db, registrar_evento
from services.logger import get_logger

logger = get_logger(__name__)

SESSAO_KEY = "auth"  # chave usada em st.session_state


# =============================================================================
# Modelo
# =============================================================================
@dataclass
class Usuario:
    """Representação imutável do usuário logado na sessão."""
    id: int
    username: str
    nome: str
    email: Optional[str]
    papel: str
    ativo: bool
    ultimo_login: Optional[datetime] = None

    def eh_admin(self) -> bool:
        return self.papel == Papel.ADMIN.value

    def eh_auditor(self) -> bool:
        return self.papel == Papel.AUDITOR.value


# =============================================================================
# Hashing de senha (bcrypt)
# =============================================================================
def hash_senha(senha: str) -> str:
    """Gera hash bcrypt da senha em claro. Salt é gerado automaticamente."""
    salt = bcrypt.gensalt(rounds=BCRYPT_SALT_ROUNDS)
    return bcrypt.hashpw(senha.encode("utf-8"), salt).decode("utf-8")


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Compara uma senha em claro com o hash armazenado. Time-safe."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_armazenado.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# =============================================================================
# Validação de senha (política OWASP ASVS §2.1)
# =============================================================================
def validar_politica_senha(senha: str) -> Optional[str]:
    """Retorna None se a senha é válida; string de erro caso contrário."""
    if len(senha) < SENHA_MIN_CHARS:
        return f"A senha precisa ter no mínimo {SENHA_MIN_CHARS} caracteres."
    if SENHA_EXIGE_MAIUSCULA and not re.search(r"[A-Z]", senha):
        return "A senha precisa ter ao menos uma letra maiúscula."
    if SENHA_EXIGE_DIGITO and not re.search(r"\d", senha):
        return "A senha precisa ter ao menos um dígito."
    if SENHA_EXIGE_ESPECIAL and not re.search(r"[^A-Za-z0-9]", senha):
        return "A senha precisa ter ao menos um caractere especial."
    return None


# =============================================================================
# CRUD de usuários
# =============================================================================
def criar_usuario(
    username: str,
    senha: str,
    nome: str,
    papel: str,
    email: Optional[str] = None,
    ignorar_politica: bool = False,
) -> Usuario:
    """Cria um novo usuário. Falha se o username já existe ou senha fraca.

    Args:
        ignorar_politica: usado pelo seed inicial para permitir senhas
            que seriam rejeitadas em produção (ex.: demo).

    Raises:
        ValueError: username já existe, senha fraca ou papel inválido.
    """
    if papel not in [p.value for p in Papel]:
        raise ValueError(f"Papel inválido: {papel}. Use um de {list(Papel)}.")

    if not ignorar_politica:
        erro = validar_politica_senha(senha)
        if erro:
            raise ValueError(erro)

    senha_hash = hash_senha(senha)
    _garantir_db()
    try:
        with _conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO usuarios (username, nome, email, senha_hash, papel)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, nome, email, senha_hash, papel),
            )
            conn.commit()
            user_id = cur.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Usuário '{username}' já existe.") from exc

    logger.info("Usuário criado: %s (papel=%s, id=%s)", username, papel, user_id)
    return Usuario(
        id=user_id, username=username, nome=nome, email=email,
        papel=papel, ativo=True,
    )


def listar_usuarios(apenas_ativos: bool = False) -> list[Usuario]:
    """Retorna todos os usuários cadastrados, sem expor o hash da senha."""
    _garantir_db()
    where = "WHERE ativo = 1" if apenas_ativos else ""
    query = f"""
        SELECT id, username, nome, email, papel, ativo, ultimo_login
        FROM usuarios
        {where}
        ORDER BY username
    """
    with _conn() as conn:
        rows = conn.execute(query).fetchall()

    usuarios = []
    for r in rows:
        ultimo = None
        if r[6]:
            try:
                ultimo = datetime.fromisoformat(r[6])
            except ValueError:
                ultimo = None
        usuarios.append(Usuario(
            id=r[0], username=r[1], nome=r[2], email=r[3],
            papel=r[4], ativo=bool(r[5]), ultimo_login=ultimo,
        ))
    return usuarios


def _buscar_usuario_interno(username: str) -> Optional[tuple]:
    """Busca usuário por username. Retorna tuple crua do SQLite (inclui hash)."""
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT id, username, nome, email, senha_hash, papel, ativo,
                   tentativas_falhas, bloqueado_ate, ultimo_login
            FROM usuarios
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
    return row


def alterar_ativo(username: str, ativo: bool) -> None:
    """Ativa ou desativa um usuário (não apaga — mantém para auditoria)."""
    with _conn() as conn:
        conn.execute(
            "UPDATE usuarios SET ativo = ? WHERE username = ?",
            (1 if ativo else 0, username),
        )
        conn.commit()
    logger.info("Usuário %s %s", username, "reativado" if ativo else "desativado")


def alterar_senha(username: str, nova_senha: str) -> None:
    """Atualiza a senha do usuário aplicando política. Limpa lockout."""
    erro = validar_politica_senha(nova_senha)
    if erro:
        raise ValueError(erro)

    senha_hash = hash_senha(nova_senha)
    with _conn() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?, tentativas_falhas = 0, bloqueado_ate = NULL
            WHERE username = ?
            """,
            (senha_hash, username),
        )
        conn.commit()

    registrar_evento(
        usuario=username,
        acao=Acao.SENHA_ALTERADA,
        severidade=Severidade.WARNING,
    )


# =============================================================================
# Lockout (bloqueio progressivo)
# =============================================================================
def _registrar_tentativa_falha(username: str) -> tuple[int, Optional[datetime]]:
    """Incrementa o contador de falhas. Se chegar ao limite, bloqueia.

    Returns:
        (tentativas_totais, bloqueado_ate) — bloqueado_ate é None se não bloqueou.
    """
    with _conn() as conn:
        # Lê atual
        row = conn.execute(
            "SELECT tentativas_falhas FROM usuarios WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return (0, None)

        novas = int(row[0]) + 1
        bloqueio_ate: Optional[str] = None

        if novas >= MAX_TENTATIVAS_FALHAS:
            bloqueio_ate = (
                datetime.utcnow() + timedelta(minutes=BLOQUEIO_MINUTOS)
            ).isoformat(timespec="seconds")

        conn.execute(
            """
            UPDATE usuarios
            SET tentativas_falhas = ?, bloqueado_ate = ?
            WHERE username = ?
            """,
            (novas, bloqueio_ate, username),
        )
        conn.commit()

    bloqueio_dt = datetime.fromisoformat(bloqueio_ate) if bloqueio_ate else None
    return (novas, bloqueio_dt)


def _limpar_tentativas(username: str) -> None:
    with _conn() as conn:
        conn.execute(
            """
            UPDATE usuarios
            SET tentativas_falhas = 0,
                bloqueado_ate = NULL,
                ultimo_login = ?
            WHERE username = ?
            """,
            (datetime.utcnow().isoformat(timespec="seconds"), username),
        )
        conn.commit()


def _esta_bloqueado(bloqueado_ate_iso: Optional[str]) -> bool:
    if not bloqueado_ate_iso:
        return False
    try:
        return datetime.fromisoformat(bloqueado_ate_iso) > datetime.utcnow()
    except ValueError:
        return False


# =============================================================================
# Login / Logout
# =============================================================================
class LoginErro(Exception):
    """Erro controlado de autenticação — mensagem amigável ao usuário."""


def autenticar(username: str, senha: str) -> Usuario:
    """Autentica um usuário e inicializa a sessão.

    Fluxo:
      1. Busca o usuário. Se não existir → erro genérico (evita enumeração).
      2. Se inativo → erro específico.
      3. Se bloqueado → erro com tempo restante.
      4. Valida a senha. Errou → incrementa contador, possivelmente bloqueia.
      5. Acertou → limpa contador, grava ultimo_login, cria sessão.

    Args:
        username: nome de usuário (case-sensitive).
        senha: senha em claro (bcrypt internamente).

    Returns:
        Usuario autenticado.

    Raises:
        LoginErro: credenciais inválidas, conta inativa ou bloqueada.
    """
    # Normalização leve — trimming
    username = (username or "").strip()
    senha = senha or ""

    if not username or not senha:
        raise LoginErro("Informe usuário e senha.")

    row = _buscar_usuario_interno(username)

    if row is None:
        # Evita enumeração: registra como falha genérica
        registrar_evento(
            usuario="anonimo",
            acao=Acao.LOGIN_FALHA,
            detalhes={"motivo": "usuario_inexistente", "tentado": username},
            severidade=Severidade.WARNING,
        )
        raise LoginErro("Usuário ou senha inválidos.")

    (uid, uname, nome, email, senha_hash, papel,
     ativo, tentativas, bloqueado_ate, ultimo_login) = row

    if not ativo:
        registrar_evento(
            usuario=uname, acao=Acao.LOGIN_FALHA,
            detalhes={"motivo": "conta_inativa"},
            severidade=Severidade.WARNING,
        )
        raise LoginErro("Conta desativada. Procure o administrador.")

    if _esta_bloqueado(bloqueado_ate):
        restante = datetime.fromisoformat(bloqueado_ate) - datetime.utcnow()
        minutos = max(int(restante.total_seconds() / 60) + 1, 1)
        registrar_evento(
            usuario=uname, acao=Acao.LOGIN_FALHA,
            detalhes={"motivo": "conta_bloqueada"},
            severidade=Severidade.WARNING,
        )
        raise LoginErro(
            f"Conta bloqueada por excesso de tentativas. Tente novamente em {minutos} min."
        )

    if not verificar_senha(senha, senha_hash):
        novas_tent, bloqueou = _registrar_tentativa_falha(uname)
        if bloqueou:
            registrar_evento(
                usuario=uname, acao=Acao.CONTA_BLOQUEADA,
                detalhes={"tentativas": novas_tent,
                          "desbloqueio_utc": bloqueou.isoformat()},
                severidade=Severidade.CRITICAL,
            )
            raise LoginErro(
                f"Número máximo de tentativas excedido. "
                f"Conta bloqueada por {BLOQUEIO_MINUTOS} min."
            )
        restantes = MAX_TENTATIVAS_FALHAS - novas_tent
        registrar_evento(
            usuario=uname, acao=Acao.LOGIN_FALHA,
            detalhes={"tentativas": novas_tent, "restantes": restantes},
            severidade=Severidade.WARNING,
        )
        raise LoginErro(
            f"Usuário ou senha inválidos. Restam {restantes} "
            f"{'tentativa' if restantes == 1 else 'tentativas'}."
        )

    # Sucesso
    _limpar_tentativas(uname)
    usuario = Usuario(
        id=uid, username=uname, nome=nome, email=email,
        papel=papel, ativo=True, ultimo_login=datetime.utcnow(),
    )
    sessao_id = str(uuid.uuid4())
    _iniciar_sessao(usuario, sessao_id)

    registrar_evento(
        usuario=uname, acao=Acao.LOGIN_OK,
        detalhes={"papel": papel},
        sessao_id=sessao_id,
        severidade=Severidade.CRITICAL if usuario.eh_admin() else Severidade.INFO,
    )
    return usuario


# =============================================================================
# Sessão (st.session_state)
# =============================================================================
def _iniciar_sessao(usuario: Usuario, sessao_id: str) -> None:
    st.session_state[SESSAO_KEY] = {
        "usuario": usuario,
        "sessao_id": sessao_id,
        "ultima_atividade": datetime.utcnow(),
    }


def _tocar_sessao() -> None:
    """Atualiza o timestamp de última atividade — chamado em cada rerun."""
    if SESSAO_KEY in st.session_state:
        st.session_state[SESSAO_KEY]["ultima_atividade"] = datetime.utcnow()


def _sessao_expirada() -> bool:
    estado = st.session_state.get(SESSAO_KEY)
    if not estado:
        return True
    ultima = estado.get("ultima_atividade")
    if not isinstance(ultima, datetime):
        return True
    return (datetime.utcnow() - ultima) > timedelta(minutes=SESSAO_TIMEOUT_MINUTOS)


def usuario_autenticado() -> Optional[Usuario]:
    """Retorna o Usuario da sessão se existir e não estiver expirada.

    Também atualiza ``ultima_atividade`` (sliding window).
    """
    if SESSAO_KEY not in st.session_state:
        return None

    if _sessao_expirada():
        estado = st.session_state.get(SESSAO_KEY, {})
        usr = estado.get("usuario")
        if isinstance(usr, Usuario):
            registrar_evento(
                usuario=usr.username,
                acao=Acao.SESSAO_EXPIRADA,
                sessao_id=estado.get("sessao_id"),
                severidade=Severidade.INFO,
            )
        st.session_state.pop(SESSAO_KEY, None)
        return None

    _tocar_sessao()
    return st.session_state[SESSAO_KEY]["usuario"]


def logout() -> None:
    """Encerra a sessão e registra na auditoria."""
    estado = st.session_state.get(SESSAO_KEY, {})
    usr = estado.get("usuario")
    if isinstance(usr, Usuario):
        registrar_evento(
            usuario=usr.username,
            acao=Acao.LOGOUT,
            sessao_id=estado.get("sessao_id"),
            severidade=Severidade.INFO,
        )
    st.session_state.pop(SESSAO_KEY, None)


def sessao_id_atual() -> Optional[str]:
    """Retorna o UUID da sessão se houver, para uso em auditoria externa."""
    estado = st.session_state.get(SESSAO_KEY)
    if estado:
        return estado.get("sessao_id")
    return None

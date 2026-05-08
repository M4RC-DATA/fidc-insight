"""
Regras de autenticação e controle de acesso.

Centraliza política de senha, timeouts, papéis (RBAC) e DDL das tabelas
SQLite de autenticação. Mantida em ``config/`` porque é parte do contrato
de segurança da aplicação — se mudar aqui, muda em todos os lugares.

Padrões de mercado adotados:
  - bcrypt com 12 salt rounds (OWASP 2023)
  - Bloqueio progressivo após 5 tentativas (mitigação de brute-force)
  - Session timeout 30 min (compatível com práticas BACEN para sistemas financeiros)
  - Política mínima: 8+ chars, 1 maiúscula, 1 dígito
"""

from enum import Enum
from pathlib import Path

from config.settings import PROJECT_ROOT


# =============================================================================
# Persistência
# =============================================================================
AUTH_DB_PATH: Path = PROJECT_ROOT / "data" / "auth.db"


# =============================================================================
# Política de senha (OWASP ASVS v4 §2.1)
# =============================================================================
SENHA_MIN_CHARS = 8
SENHA_EXIGE_MAIUSCULA = True
SENHA_EXIGE_DIGITO = True
SENHA_EXIGE_ESPECIAL = False  # mantido como opcional para demo acadêmica

BCRYPT_SALT_ROUNDS = 12  # ~300 ms por hash em CPU moderna — equilíbrio UX/segurança


# =============================================================================
# Bloqueio progressivo (anti brute-force)
# =============================================================================
MAX_TENTATIVAS_FALHAS = 5
BLOQUEIO_MINUTOS = 15


# =============================================================================
# Sessão
# =============================================================================
SESSAO_TIMEOUT_MINUTOS = 30  # inatividade


# =============================================================================
# RBAC — Papéis e permissões
# =============================================================================
class Papel(str, Enum):
    """Papéis de RBAC do FIDC Insight.

    Herda de str para permitir comparação direta com strings vindas
    do SQLite sem conversão explícita.
    """
    ANALISTA = "analista"
    GESTOR = "gestor"
    AUDITOR = "auditor"
    ADMIN = "admin"


# Descrições para exibir na UI (tela de admin, chip da sidebar)
PAPEIS_DESCRICAO = {
    Papel.ANALISTA: "Gera parecer individual · exporta PDF/Excel",
    Papel.GESTOR:   "Parecer + Visão Macro + Filtros da carteira",
    Papel.AUDITOR:  "Read-only · acesso exclusivo à trilha de auditoria",
    Papel.ADMIN:    "Controle total · gerência de usuários e sistema",
}


# Matriz de permissões: papel → conjunto de views habilitadas
#   'macro'        = Cockpit FIDC (visão decisória da carteira)
#   'individual'   = Parecer Individual (requer CNPJ)
#   'filtros'      = Explorador / Filtros
#   'nuclea_base'  = Benchmark / Base de Referência
#   'parametros'   = Parâmetros e Modelo (governança)
#   'auditoria'    = Trilha de auditoria
#   'admin'        = Gerência de usuários
PERMISSOES_VIEWS = {
    Papel.ANALISTA: {"home", "individual", "macro", "nuclea_base"},
    Papel.GESTOR:   {"home", "macro", "individual", "carteira", "carteira_upload",
                     "nuclea_base"},
    Papel.AUDITOR:  {"home", "macro", "auditoria", "nuclea_base"},
    Papel.ADMIN:    {"home", "macro", "individual", "carteira", "carteira_upload",
                     "nuclea_base", "auditoria", "admin"},
}


def pode_acessar(papel: str, view: str) -> bool:
    """Retorna True se o papel tem permissão para a view."""
    try:
        return view in PERMISSOES_VIEWS[Papel(papel)]
    except (ValueError, KeyError):
        return False


# =============================================================================
# Severidade de eventos de auditoria
# =============================================================================
class Severidade(str, Enum):
    """Classificação de severidade do evento de auditoria."""
    INFO = "INFO"            # Eventos normais (login ok, logout)
    WARNING = "WARNING"      # Eventos suspeitos (senha errada)
    CRITICAL = "CRITICAL"    # Eventos graves (conta bloqueada, login de admin)


# =============================================================================
# Ações de auditoria (vocabulário controlado)
# =============================================================================
# Mantemos um vocabulário fixo para facilitar filtros e relatórios.
# Escolher strings curtas e em MAIÚSCULAS (padrão log analytics).
class Acao(str, Enum):
    LOGIN_OK         = "LOGIN_OK"
    LOGIN_FALHA      = "LOGIN_FALHA"
    LOGOUT           = "LOGOUT"
    SESSAO_EXPIRADA  = "SESSAO_EXPIRADA"
    CONTA_BLOQUEADA  = "CONTA_BLOQUEADA"
    CONTA_DESBLOQUEADA = "CONTA_DESBLOQUEADA"
    SENHA_ALTERADA   = "SENHA_ALTERADA"


# =============================================================================
# DDL — criação das tabelas (idempotente)
# =============================================================================
SCHEMA_USUARIOS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    username           TEXT    NOT NULL UNIQUE,
    nome               TEXT    NOT NULL,
    email              TEXT,
    senha_hash         TEXT    NOT NULL,
    papel              TEXT    NOT NULL CHECK (papel IN ('analista','gestor','auditor','admin')),
    ativo              INTEGER NOT NULL DEFAULT 1,
    criado_em          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_login       TIMESTAMP,
    tentativas_falhas  INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate      TIMESTAMP
);
"""

SCHEMA_AUDIT_LOG = """
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario      TEXT    NOT NULL,
    acao         TEXT    NOT NULL,
    detalhes     TEXT,
    sessao_id    TEXT,
    severidade   TEXT    NOT NULL DEFAULT 'INFO'
);
"""

SCHEMA_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_audit_usuario   ON audit_log(usuario);",
    "CREATE INDEX IF NOT EXISTS idx_audit_acao      ON audit_log(acao);",
    "CREATE INDEX IF NOT EXISTS idx_usuarios_ativo  ON usuarios(ativo);",
]

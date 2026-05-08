"""
Seed de usuários iniciais do FIDC Insight.

Cria os 4 papéis RBAC com usuários-modelo para demo / graduação. A senha
padrão segue a política (8+ chars, maiúscula e dígito).

Uso:
    python seed_users.py          # cria os 4 usuários (ignora os já existentes)
    python seed_users.py --reset  # apaga e recria o arquivo auth.db
    python seed_users.py --list   # apenas lista usuários cadastrados

Credenciais geradas (troque em produção!):
    admin     / Admin@2025
    gestor    / Gestor@2025
    analista  / Analista@2025
    auditor   / Auditor@2025
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permite rodar de qualquer CWD (ex.: `python seed_users.py` na raiz)
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from config.auth_rules import AUTH_DB_PATH, Papel  # noqa: E402
from services.auth import criar_usuario, listar_usuarios  # noqa: E402


SEED = [
    {
        "username": "admin",
        "senha": "Admin@2025",
        "nome": "Administrador do Sistema",
        "papel": Papel.ADMIN.value,
        "email": "admin@dataverse.local",
    },
    {
        "username": "gestor",
        "senha": "Gestor@2025",
        "nome": "Gestor da Carteira",
        "papel": Papel.GESTOR.value,
        "email": "gestor@dataverse.local",
    },
    {
        "username": "analista",
        "senha": "Analista@2025",
        "nome": "Analista de Crédito",
        "papel": Papel.ANALISTA.value,
        "email": "analista@dataverse.local",
    },
    {
        "username": "auditor",
        "senha": "Auditor@2025",
        "nome": "Auditor de Trilha",
        "papel": Papel.AUDITOR.value,
        "email": "auditor@dataverse.local",
    },
]


def _reset_db() -> None:
    """Apaga o arquivo SQLite para recomeçar do zero."""
    if AUTH_DB_PATH.exists():
        AUTH_DB_PATH.unlink()
        print(f"[reset] arquivo removido: {AUTH_DB_PATH}")
    else:
        print(f"[reset] nada a remover ({AUTH_DB_PATH} não existe)")


def _listar() -> None:
    usuarios = listar_usuarios(apenas_ativos=False)
    if not usuarios:
        print("Nenhum usuário cadastrado.")
        return
    print(f"{'Usuário':<14} {'Papel':<10} {'Ativo':<6} Nome")
    print("-" * 80)
    for u in usuarios:
        print(f"{u.username:<14} {u.papel:<10} {'sim' if u.ativo else 'não':<6} {u.nome}")


def _semear() -> None:
    existentes = {u.username for u in listar_usuarios()}
    criados = 0
    for cfg in SEED:
        if cfg["username"] in existentes:
            print(f"[skip] '{cfg['username']}' já existe")
            continue
        try:
            # ignorar_politica=False — queremos validar mesmo no seed
            u = criar_usuario(
                username=cfg["username"],
                senha=cfg["senha"],
                nome=cfg["nome"],
                papel=cfg["papel"],
                email=cfg["email"],
            )
            print(f"[ok]   '{u.username}' criado · papel={u.papel}")
            criados += 1
        except ValueError as exc:
            print(f"[erro] '{cfg['username']}': {exc}")

    print(f"\nResumo: {criados} usuário(s) criado(s).")
    print(f"Arquivo SQLite: {AUTH_DB_PATH}")
    print("\nCredenciais:")
    for cfg in SEED:
        print(f"  {cfg['username']:<10} · {cfg['senha']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed de usuários do FIDC Insight")
    parser.add_argument("--reset", action="store_true", help="Apaga o auth.db antes de semear.")
    parser.add_argument("--list", action="store_true", help="Apenas lista os usuários atuais.")
    args = parser.parse_args()

    if args.list:
        _listar()
        return

    if args.reset:
        _reset_db()

    _semear()


if __name__ == "__main__":
    main()

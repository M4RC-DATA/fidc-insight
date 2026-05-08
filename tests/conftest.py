"""Configuração do pytest · injeta a raiz do projeto no sys.path.

Garante que `import domain.scoring` funcione quando o pytest é executado
de dentro da pasta `tests/` ou a partir da raiz do projeto.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Raiz do projeto = pasta que contém a pasta `tests/`
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

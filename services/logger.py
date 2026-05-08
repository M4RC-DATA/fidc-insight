"""
Logger centralizado.

Substitui os `except: pass` silenciosos do código original por logging
estruturado. Facilita debug em produção e apresentação (banca pode ver
no console os passos do sistema).
"""

import logging
import sys
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s"
_LOG_DATEFMT = "%H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado com formato padrão do projeto.

    Args:
        name: nome do módulo (geralmente __name__)

    Returns:
        logger configurado que escreve em stdout.
    """
    logger = logging.getLogger(name)

    # Evita handlers duplicados se get_logger for chamado múltiplas vezes
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATEFMT)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger

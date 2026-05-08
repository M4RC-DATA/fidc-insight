"""
Funções de formatação para padrão brasileiro.

Centraliza formatação de moeda, percentual, data e CNPJ para garantir
consistência visual em todas as telas e documentos.
"""

from datetime import date, datetime
from typing import Union

Number = Union[int, float]


# =============================================================================
# Moeda e valores numéricos
# =============================================================================
def formatar_moeda(valor: Number, casas: int = 2) -> str:
    """Formata um valor como moeda brasileira.

    >>> formatar_moeda(1234567.89)
    'R$ 1.234.567,89'
    """
    if valor is None:
        return "R$ 0,00"
    fmt = f"{{:,.{casas}f}}".format(valor)
    # Troca separadores para padrão brasileiro
    return "R$ " + fmt.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor: Number, casas: int = 0) -> str:
    """Formata número com separadores brasileiros (sem R$)."""
    if valor is None:
        return "0"
    fmt = f"{{:,.{casas}f}}".format(valor)
    return fmt.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor: Number, casas: int = 2, ja_em_percentual: bool = False) -> str:
    """Formata um valor decimal como percentual.

    >>> formatar_percentual(0.1375)
    '13,75%'
    >>> formatar_percentual(13.75, ja_em_percentual=True)
    '13,75%'
    """
    if valor is None:
        return "0,00%"
    pct = valor if ja_em_percentual else valor * 100
    return f"{pct:.{casas}f}%".replace(".", ",")


# =============================================================================
# Datas
# =============================================================================
def formatar_data(d: Union[date, datetime, str, None], com_hora: bool = False) -> str:
    """Formata data em padrão brasileiro (dd/mm/aaaa)."""
    if d is None:
        return "—"
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d.replace("Z", "+00:00"))
        except ValueError:
            return d
    if com_hora and isinstance(d, datetime):
        return d.strftime("%d/%m/%Y %H:%M:%S")
    return d.strftime("%d/%m/%Y")


# =============================================================================
# CNPJ
# =============================================================================
def formatar_cnpj(cnpj: str) -> str:
    """Aplica máscara visual ao CNPJ: 00.000.000/0000-00.

    Aceita CNPJ com ou sem pontuação. Retorna o input original
    se não tiver 14 dígitos (pode ser hash no caso do dataset).
    """
    if not cnpj:
        return ""
    digitos = "".join(c for c in str(cnpj) if c.isdigit())
    if len(digitos) != 14:
        return str(cnpj)  # Pode ser hash ou ID não-CNPJ
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def limpar_cnpj(cnpj: str) -> str:
    """Remove toda pontuação do CNPJ, deixando só dígitos."""
    return "".join(c for c in str(cnpj) if c.isdigit()) if cnpj else ""


def id_curto(identificador: str) -> str:
    """Retorna um identificador abreviado para tabelas.

    Se for CNPJ válido (14 dígitos) → aplica máscara normal.
    Se for hash/identificador longo (> 16) → pega 8 primeiros + 4 últimos,
    separados por reticências, para que o usuário ainda consiga comparar
    visualmente entre linhas e prefixos (padrão Git short-hash).
    """
    if not identificador:
        return ""
    s = str(identificador)
    digitos = "".join(c for c in s if c.isdigit())
    if len(digitos) == 14:
        return formatar_cnpj(s)
    if len(s) > 16:
        return f"{s[:8]}…{s[-4:]}"
    return s

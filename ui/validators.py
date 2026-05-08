"""
Validação de CNPJ brasileiro.

Implementa o algoritmo oficial da Receita Federal para cálculo do
dígito verificador — não basta só validar formato, precisa validar
que o CNPJ é matematicamente válido.
"""

from utils.formatters import limpar_cnpj


def validar_cnpj(cnpj: str) -> bool:
    """Valida um CNPJ incluindo checagem dos dígitos verificadores.

    Args:
        cnpj: CNPJ com ou sem pontuação.

    Returns:
        True se o CNPJ for matematicamente válido. False caso contrário.

    >>> validar_cnpj("11.222.333/0001-81")
    True
    >>> validar_cnpj("11222333000100")
    False
    """
    digitos = limpar_cnpj(cnpj)

    if len(digitos) != 14:
        return False

    # Rejeita CNPJs com todos os dígitos iguais (ex: "00000000000000")
    if len(set(digitos)) == 1:
        return False

    # Validação do primeiro dígito verificador
    pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma_1 = sum(int(d) * p for d, p in zip(digitos[:12], pesos_1))
    resto_1 = soma_1 % 11
    dv_1 = 0 if resto_1 < 2 else 11 - resto_1

    if int(digitos[12]) != dv_1:
        return False

    # Validação do segundo dígito verificador
    pesos_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma_2 = sum(int(d) * p for d, p in zip(digitos[:13], pesos_2))
    resto_2 = soma_2 % 11
    dv_2 = 0 if resto_2 < 2 else 11 - resto_2

    return int(digitos[13]) == dv_2


def parece_hash(identificador: str) -> bool:
    """Verifica se o identificador parece um hash (não é CNPJ numérico).

    Útil porque o dataset Núclea usa hashes nos IDs dos sacados por
    questões de LGPD.
    """
    if not identificador:
        return False
    # Hash hexadecimal costuma ter 32+ caracteres alfanuméricos
    return len(identificador) >= 16 and any(c.isalpha() for c in identificador)

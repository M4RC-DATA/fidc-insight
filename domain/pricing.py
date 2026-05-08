"""
Motor de precificação de operações FIDC.

Calcula valor presente sugerido, receita bruta e margem real considerando
a perda esperada (RAROC-style). Todas as funções são puras.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ResultadoPrecificacao:
    """Resultado completo da precificação de uma operação."""
    valor_face: float           # Valor nominal (valor recebido do sacado no vencimento)
    valor_presente: float       # Valor desembolsado hoje (VP)
    desconto_bruto: float       # Receita bruta da operação (face - VP)
    perda_esperada: float       # Expected Credit Loss (IFRS 9 / Basel)
    lucro_raroc: float          # Lucro econômico ajustado ao risco
    margem_real: float          # Margem % sobre o valor face
    taxa_total: float           # Selic + prêmio de risco
    prazo_dias: int             # Prazo ajustado total (contratual + atraso esperado)
    prazo_contratual_dias: int  # Prazo contratual puro (vencimento - hoje)
    atraso_esperado_dias: int   # Dias de atraso histórico adicionados ao prazo
    prazo_anos: float           # Prazo total em anos (para composição da taxa)


def precificar_operacao(
    valor_face: float,
    data_vencimento: date,
    data_hoje: date,
    selic: float,
    premio_anual: float,
    pd_anual: float,
    lgd: float,
    atraso_historico_dias: float = 0.0,
) -> ResultadoPrecificacao:
    """Precifica uma operação FIDC com base na metodologia RAROC.

    Prazo ajustado:
        O prazo contratual é a diferença em dias entre o vencimento e hoje.
        O atraso histórico adiciona os dias que esse sacado costuma atrasar,
        estimando o prazo efetivo de recebimento.

        Ex: vencimento em 90 dias + sacado atrasa 12 dias em média = 102 dias efetivos.

        Por que isso importa:
        - VP menor (mais tempo de desconto = menor valor presente)
        - ECL maior (mais tempo de exposição = mais perda esperada)
        Ambos os efeitos são conservadores e corretos: o fundo não deve
        precificar como se fosse receber no prazo exato se o sacado costuma atrasar.

    Fórmula:
        prazo_total_dias = (vencimento − hoje) + round(atraso_histórico)
        taxa_total       = Selic + prêmio de risco do rating
        VP               = Face / (1 + taxa)^(prazo_total_anos)
        ECL              = Face × PD_anual × prazo_total_anos × LGD
        Lucro RAROC      = (Face − VP) − ECL

    Args:
        valor_face: Valor nominal do título.
        data_vencimento: Data de vencimento contratual da operação.
        data_hoje: Data-base da precificação.
        selic: Taxa Selic em formato decimal (ex: 0.1075 = 10,75% a.a.).
        premio_anual: Spread de risco do rating em formato decimal.
        pd_anual: Probability of Default anual em formato decimal.
        lgd: Loss Given Default em formato decimal (ex: 0.50 = 50%).
        atraso_historico_dias: Atraso médio histórico do sacado em dias.
            Deve ser >= 0. Valores negativos são tratados como 0.

    Returns:
        ResultadoPrecificacao com todas as métricas calculadas.
    """
    prazo_contratual = max((data_vencimento - data_hoje).days, 1)

    # round() em vez de int() para não truncar: 11.8 → 12, não 11
    # max(0, ...) garante que atraso negativo (dado ruim) não reduz o prazo
    atraso_arredondado = max(0, round(atraso_historico_dias))

    prazo_dias = prazo_contratual + atraso_arredondado
    prazo_anos = prazo_dias / 365.0

    taxa_total = round(selic + premio_anual, 6)

    valor_presente = round(valor_face / (1 + taxa_total) ** prazo_anos, 2)
    desconto_bruto = valor_face - valor_presente

    perda_esperada = valor_face * pd_anual * prazo_anos * lgd
    lucro_raroc = desconto_bruto - perda_esperada
    margem_real = (lucro_raroc / valor_face) * 100 if valor_face > 0 else 0.0

    return ResultadoPrecificacao(
        valor_face=valor_face,
        valor_presente=valor_presente,
        desconto_bruto=desconto_bruto,
        perda_esperada=perda_esperada,
        lucro_raroc=lucro_raroc,
        margem_real=margem_real,
        taxa_total=taxa_total,
        prazo_dias=prazo_dias,
        prazo_contratual_dias=prazo_contratual,
        atraso_esperado_dias=atraso_arredondado,
        prazo_anos=prazo_anos,
    )

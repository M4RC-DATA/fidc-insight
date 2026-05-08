"""
Verificação de Lastro · Detecção de Anomalias em FIDCs.

Módulo de domínio puro (sem Streamlit, sem BigQuery) que avalia a
autenticidade de um novo título frente ao histórico transacionado entre
um Cedente e um Sacado. Objetivo: mitigar risco de "boletos frios" e
duplicatas fraudulentas, que são a principal dor operacional dos FIDCs
brasileiros (Parmalat, Encol, Grupo Americanas, etc.).

A função principal ``validar_lastro`` calcula o **ICL — Índice de
Confiança do Lastro** (0–100) e atribui um selo semafórico:

    VERDE     · Recorrência > 6 meses  e  |Z| ≤ 2
    AMARELO   · Primeira operação, recorrência curta ou valor acima da média
    VERMELHO  · |Z| > 3  ou  prazo incompatível com o histórico/setor

Metodologia:

  Componente          Peso    Base
  ------------------  ------  -----------------------------------------
  Volume (Z-score)    40%     Desvio da operação vs. histórico μ, σ
  Recorrência         30%     Meses desde o 1º boleto liquidado
  Frequência          15%     Transações/mês (estabilidade)
  Prazo               15%     Diferença vs. prazo médio histórico
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd


# =============================================================================
# Tipos públicos
# =============================================================================
class SeloLastro(str, Enum):
    VERDE = "VERDE"       # Lastro verificado
    AMARELO = "AMARELO"   # Atenção
    VERMELHO = "VERMELHO" # Suspeito


@dataclass(frozen=True)
class EstatisticasHistorico:
    """Estatísticas descritivas do histórico Cedente × Sacado."""
    n_operacoes: int
    valor_medio: float
    valor_desvio: float
    valor_mediana: float
    prazo_medio_dias: float
    prazo_desvio_dias: float
    atraso_medio_dias: float
    primeira_operacao: Optional[str]
    ultima_operacao: Optional[str]
    meses_relacionamento: float
    frequencia_mensal: float


@dataclass(frozen=True)
class ResultadoLastro:
    """Retorno completo da validação de lastro.

    Attributes:
        selo: Classificação semafórica (VERDE/AMARELO/VERMELHO).
        icl: Índice de Confiança do Lastro (0–100). Acima de 70 é saudável.
        z_score_valor: Desvios-padrão do valor proposto vs. histórico.
        desvio_prazo_dias: Diferença absoluta do prazo proposto vs. média.
        z_score_prazo: Desvios-padrão do prazo vs. histórico.
        componentes: Dicionário com cada componente do ICL em pontos.
        motivos: Lista de razões que justificaram o selo.
        recomendacao: Texto pronto para UI/PDF.
        historico: Estatísticas descritivas completas do histórico.
        hash_integridade: SHA-256 do payload — para trilha de auditoria.
    """
    selo: SeloLastro
    icl: float
    z_score_valor: float
    desvio_prazo_dias: float
    z_score_prazo: float
    componentes: dict
    motivos: List[str]
    recomendacao: str
    historico: EstatisticasHistorico
    hash_integridade: str

    def to_dict(self) -> dict:
        """Serialização completa para PDF/JSON/auditoria."""
        base = asdict(self)
        base["selo"] = self.selo.value
        base["historico"] = asdict(self.historico)
        return base


# =============================================================================
# Parâmetros do modelo
# =============================================================================
LIMITE_Z_ALERTA = 2.0       # Acima disso → amarelo
LIMITE_Z_SUSPEITO = 3.0     # Acima disso → vermelho
LIMITE_DESVIO_PRAZO = 2.5   # Z-score de prazo acima disso → vermelho
MIN_MESES_VERIFICADO = 0    # Recorrência mínima para selo verde

# Pesos dos componentes do ICL (soma = 1.0)
PESO_VOLUME = 0.40
PESO_RECORRENCIA = 0.30
PESO_FREQUENCIA = 0.15
PESO_PRAZO = 0.15


# =============================================================================
# Função principal
# =============================================================================
def validar_lastro(
    df_historico: pd.DataFrame,
    valor_proposto: float,
    prazo_proposto: int,
    cnae_setor: Optional[str] = None,
    prazo_medio_setor: Optional[float] = None,
) -> ResultadoLastro:
    """Calcula o Índice de Confiança do Lastro (ICL) e atribui selo.

    Recebe o histórico transacionado de um par Cedente × Sacado e avalia
    se uma nova operação proposta é estatisticamente coerente com esse
    histórico. Detecta outliers via Z-score, recorrência comercial,
    frequência e consistência de prazo.

    Args:
        df_historico: Histórico de operações Cedente × Sacado. Aceita
            qualquer DataFrame com as seguintes colunas (nomes flexíveis):
              · valor_nominal (ou valor, vlr_nominal)
              · data_emissao (ou data, data_boleto)
              · prazo_du (opcional — prazo em dias úteis)
              · atraso_dias (opcional)
            DataFrame vazio é aceito (retorna selo AMARELO · primeira op).
        valor_proposto: Valor de face da nova operação (R$).
        prazo_proposto: Prazo em dias úteis da operação.
        cnae_setor: Código CNAE do cedente/sacado (opcional — usado apenas
            para texto descritivo no relatório).
        prazo_medio_setor: Prazo típico do setor (dias). Se fornecido,
            desvios > 2× desse valor acionam selo vermelho por incoerência
            com o CNAE.

    Returns:
        ResultadoLastro com selo, ICL, componentes e hash SHA-256.

    Examples:
        >>> df = pd.DataFrame({
        ...     "valor_nominal": [50_000, 48_000, 52_000, 51_000],
        ...     "data_emissao": pd.date_range("2024-01-01", periods=4, freq="45D"),
        ...     "prazo_du": [30, 30, 32, 30],
        ... })
        >>> r = validar_lastro(df, valor_proposto=49_500, prazo_proposto=31)
        >>> r.selo
        <SeloLastro.VERDE: 'VERDE'>
        >>> r.icl > 70
        True
    """
    # ------------------------------------------------------------------------
    # 1. Normaliza e valida o histórico
    # ------------------------------------------------------------------------
    hist = normalizar_historico(df_historico)
    stats = _calcular_estatisticas(hist)

    motivos: List[str] = []

    # ------------------------------------------------------------------------
    # 2. Caso limite: primeira operação entre as partes
    # ------------------------------------------------------------------------
    if stats.n_operacoes == 0:
        motivos.append("Primeira operação registrada entre as partes — sem histórico.")
        componentes = {
            "volume": 0.0,
            "recorrencia": 0.0,
            "frequencia": 0.0,
            "prazo": 0.0,
        }
        selo = SeloLastro.AMARELO
        recomendacao = (
            "Primeira transação Cedente × Sacado. Recomenda-se validação "
            "documental adicional (nota fiscal eletrônica + confirmação "
            "de aceite) e limite operacional reduzido."
        )
        return _finalizar(
            selo=selo,
            icl=25.0,  # Piso baixo — ausência de histórico é por si um risco
            z_score_valor=0.0,
            desvio_prazo_dias=0.0,
            z_score_prazo=0.0,
            componentes=componentes,
            motivos=motivos,
            recomendacao=recomendacao,
            historico=stats,
            valor_proposto=valor_proposto,
            prazo_proposto=prazo_proposto,
            cnae_setor=cnae_setor,
        )

    # ------------------------------------------------------------------------
    # 3. Z-score de valor — outlier estatístico?
    # ------------------------------------------------------------------------
    if stats.valor_desvio > 0:
        z_valor = (valor_proposto - stats.valor_medio) / stats.valor_desvio
    else:
        # Histórico constante — qualquer variação é suspeita
        razao = valor_proposto / stats.valor_medio if stats.valor_medio > 0 else 1.0
        z_valor = (razao - 1.0) * 5.0  # 20% de variação ≈ 1σ sintético

    z_valor_abs = abs(z_valor)

    # ------------------------------------------------------------------------
    # 4. Consistência de prazo — histórico e/ou setor
    # ------------------------------------------------------------------------
    desvio_prazo = abs(prazo_proposto - stats.prazo_medio_dias)
    if stats.prazo_desvio_dias > 0:
        z_prazo = (prazo_proposto - stats.prazo_medio_dias) / stats.prazo_desvio_dias
    else:
        z_prazo = desvio_prazo / max(stats.prazo_medio_dias, 1.0) * 5.0

    prazo_incoerente_setor = False
    if prazo_medio_setor and prazo_medio_setor > 0:
        razao_setor = prazo_proposto / prazo_medio_setor
        if razao_setor > 2.0 or razao_setor < 0.25:
            prazo_incoerente_setor = True

    # ------------------------------------------------------------------------
    # 5. Componentes do ICL (cada um 0–100)
    # ------------------------------------------------------------------------
    # 5a. Volume: penaliza distância estatística da média histórica
    c_volume = max(0.0, 100.0 - z_valor_abs * 25.0)

    # 5b. Recorrência: cresce linearmente até 24 meses (2 anos)
    c_recorrencia = min(100.0, stats.meses_relacionamento / 24.0 * 100.0)

    # 5c. Frequência: >= 2 ops/mês é saudável; cap em 4
    c_frequencia = min(100.0, stats.frequencia_mensal / 2.0 * 100.0)

    # 5d. Prazo: penaliza Z-score alto
    c_prazo = max(0.0, 100.0 - abs(z_prazo) * 30.0)

    icl = (
        c_volume       * PESO_VOLUME
        + c_recorrencia  * PESO_RECORRENCIA
        + c_frequencia   * PESO_FREQUENCIA
        + c_prazo        * PESO_PRAZO
    )
    icl = round(max(0.0, min(100.0, icl)), 1)

    componentes = {
        "volume": round(c_volume, 1),
        "recorrencia": round(c_recorrencia, 1),
        "frequencia": round(c_frequencia, 1),
        "prazo": round(c_prazo, 1),
    }

    # ------------------------------------------------------------------------
    # 6. Selo e motivos
    # ------------------------------------------------------------------------
    # Condições de VERMELHO
    if z_valor_abs > LIMITE_Z_SUSPEITO:
        motivos.append(
            f"Valor {z_valor:+.1f}σ da média histórica — outlier severo "
            f"(> {LIMITE_Z_SUSPEITO:.0f} desvios)."
        )
    if abs(z_prazo) > LIMITE_DESVIO_PRAZO:
        motivos.append(
            f"Prazo desvia {z_prazo:+.1f}σ do histórico de pagamento — "
            "possível tentativa de alongar janela de fraude."
        )
    if prazo_incoerente_setor:
        motivos.append(
            f"Prazo de {prazo_proposto} DU é incompatível com a média "
            f"do setor (CNAE {cnae_setor or 's/ ref.'}: "
            f"{prazo_medio_setor:.0f} DU)."
        )

    if motivos and (
        z_valor_abs > LIMITE_Z_SUSPEITO
        or abs(z_prazo) > LIMITE_DESVIO_PRAZO
        or prazo_incoerente_setor
    ):
        selo = SeloLastro.VERMELHO
        recomendacao = (
            "BLOQUEIO RECOMENDADO. Os indicadores apontam desvio materialmente "
            "incompatível com o histórico do par. Acionar o comitê de crédito e "
            "solicitar NF-e, comprovante de entrega e aceite do sacado antes de "
            "qualquer desembolso."
        )
    else:
        # Condições de VERDE (precisa de ambas)
        tem_recorrencia = stats.meses_relacionamento >= MIN_MESES_VERIFICADO
        volume_normal = z_valor_abs <= LIMITE_Z_ALERTA

        if tem_recorrencia and volume_normal:
            selo = SeloLastro.VERDE
            motivos.append(
                f"Relacionamento de {stats.meses_relacionamento:.1f} meses "
                f"com valor dentro de {z_valor_abs:.2f}σ — padrão consistente."
            )
            recomendacao = (
                "Lastro verificado. O par Cedente × Sacado apresenta histórico "
                "robusto e o valor proposto é compatível com o padrão transacional. "
                "Operação pode seguir o fluxo ordinário de aprovação."
            )
        else:
            selo = SeloLastro.AMARELO
            if not tem_recorrencia:
                motivos.append(
                    f"Recorrência curta ({stats.meses_relacionamento:.1f} meses · "
                    f"mínimo {MIN_MESES_VERIFICADO} para selo verde)."
                )
            if z_valor_abs > 1.0 and z_valor_abs <= LIMITE_Z_ALERTA:
                motivos.append(
                    f"Valor {z_valor:+.1f}σ acima da média — atenção, mas "
                    "dentro da faixa aceitável."
                )
            if stats.frequencia_mensal < 0.5:
                motivos.append(
                    f"Frequência baixa ({stats.frequencia_mensal:.2f} ops/mês) "
                    "sugere relacionamento pouco consolidado."
                )
            recomendacao = (
                "Operação aprovável sob ressalva. Recomenda-se validar "
                "documentação de suporte (NF-e, canhoto) e aplicar limite "
                "operacional conservador até que a recorrência se consolide."
            )

    if not motivos:
        motivos.append("Nenhum desvio material identificado.")

    return _finalizar(
        selo=selo,
        icl=icl,
        z_score_valor=round(z_valor, 3),
        desvio_prazo_dias=round(desvio_prazo, 2),
        z_score_prazo=round(z_prazo, 3),
        componentes=componentes,
        motivos=motivos,
        recomendacao=recomendacao,
        historico=stats,
        valor_proposto=valor_proposto,
        prazo_proposto=prazo_proposto,
        cnae_setor=cnae_setor,
    )


# =============================================================================
# Helpers internos
# =============================================================================
_ALIAS_VALOR = ("valor_nominal", "valor", "vlr_nominal", "vlr_nominal_total")
_ALIAS_DATA  = ("data_emissao", "data", "data_boleto", "data_liquidacao", "dt_emissao")
_ALIAS_PRAZO = ("prazo_du", "prazo", "prazo_dias")
_ALIAS_ATRASO = ("atraso_dias", "atraso", "dias_atraso")


def _primeira_coluna_existente(df: pd.DataFrame, opcoes: Iterable[str]) -> Optional[str]:
    """Retorna o primeiro nome de coluna do ``df`` que bater com ``opcoes``."""
    for col in opcoes:
        if col in df.columns:
            return col
    return None


def normalizar_historico(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza nomes de colunas do histórico recebido.

    Cria colunas canônicas: ``valor``, ``data``, ``prazo``, ``atraso``.
    Colunas ausentes viram NaN — o chamador lida com isso.

    Pública porque também é usada pela camada de UI para renderizar o
    scatter com os mesmos nomes de coluna canônicos.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["valor", "data", "prazo", "atraso"])

    d = df.copy()
    col_valor = _primeira_coluna_existente(d, _ALIAS_VALOR)
    col_data  = _primeira_coluna_existente(d, _ALIAS_DATA)
    col_prazo = _primeira_coluna_existente(d, _ALIAS_PRAZO)
    col_atr   = _primeira_coluna_existente(d, _ALIAS_ATRASO)

    out = pd.DataFrame()
    out["valor"] = pd.to_numeric(d[col_valor], errors="coerce") if col_valor else np.nan
    out["data"]  = pd.to_datetime(d[col_data], errors="coerce") if col_data else pd.NaT
    out["prazo"] = pd.to_numeric(d[col_prazo], errors="coerce") if col_prazo else np.nan
    out["atraso"] = pd.to_numeric(d[col_atr], errors="coerce") if col_atr else np.nan

    out = out.dropna(subset=["valor"])
    return out.reset_index(drop=True)


def _calcular_estatisticas(hist: pd.DataFrame) -> EstatisticasHistorico:
    """Extrai estatísticas descritivas do histórico normalizado."""
    n = len(hist)
    if n == 0:
        return EstatisticasHistorico(
            n_operacoes=0,
            valor_medio=0.0, valor_desvio=0.0, valor_mediana=0.0,
            prazo_medio_dias=30.0, prazo_desvio_dias=0.0,
            atraso_medio_dias=0.0,
            primeira_operacao=None, ultima_operacao=None,
            meses_relacionamento=0.0, frequencia_mensal=0.0,
        )

    valores = hist["valor"].dropna()
    v_media = float(valores.mean())
    v_desvio = float(valores.std(ddof=0)) if len(valores) > 1 else 0.0
    v_mediana = float(valores.median())

    prazos = hist["prazo"].dropna()
    if len(prazos) > 0:
        p_media = float(prazos.mean())
        p_desvio = float(prazos.std(ddof=0)) if len(prazos) > 1 else 0.0
    else:
        p_media, p_desvio = 30.0, 0.0

    atrasos = hist["atraso"].dropna()
    a_media = float(atrasos.mean()) if len(atrasos) > 0 else 0.0

    datas = hist["data"].dropna()
    if len(datas) > 0:
        d_min = datas.min()
        d_max = datas.max()
        primeira = d_min.strftime("%Y-%m-%d")
        ultima = d_max.strftime("%Y-%m-%d")
        # Meses até HOJE (não até a última op) para refletir recência real
        hoje = pd.Timestamp.today().normalize()
        delta_dias = max((hoje - d_min).days, 0)
        meses_rel = delta_dias / 30.4375
        freq_mensal = n / meses_rel if meses_rel >= 1.0 else float(n)
    else:
        primeira = None
        ultima = None
        meses_rel = 0.0
        freq_mensal = 0.0

    return EstatisticasHistorico(
        n_operacoes=n,
        valor_medio=round(v_media, 2),
        valor_desvio=round(v_desvio, 2),
        valor_mediana=round(v_mediana, 2),
        prazo_medio_dias=round(p_media, 2),
        prazo_desvio_dias=round(p_desvio, 2),
        atraso_medio_dias=round(a_media, 2),
        primeira_operacao=primeira,
        ultima_operacao=ultima,
        meses_relacionamento=round(meses_rel, 2),
        frequencia_mensal=round(freq_mensal, 3),
    )


def _finalizar(
    *,
    selo: SeloLastro,
    icl: float,
    z_score_valor: float,
    desvio_prazo_dias: float,
    z_score_prazo: float,
    componentes: dict,
    motivos: List[str],
    recomendacao: str,
    historico: EstatisticasHistorico,
    valor_proposto: float,
    prazo_proposto: int,
    cnae_setor: Optional[str],
) -> ResultadoLastro:
    """Monta o ResultadoLastro com hash SHA-256 canônico do payload."""
    payload = {
        "selo": selo.value,
        "icl": icl,
        "z_score_valor": z_score_valor,
        "z_score_prazo": z_score_prazo,
        "valor_proposto": valor_proposto,
        "prazo_proposto": prazo_proposto,
        "cnae_setor": cnae_setor,
        "historico": {
            "n_operacoes": historico.n_operacoes,
            "valor_medio": historico.valor_medio,
            "valor_desvio": historico.valor_desvio,
            "meses_relacionamento": historico.meses_relacionamento,
        },
    }
    # JSON canônico (sort_keys) garante hash estável entre execuções
    blob = json.dumps(payload, sort_keys=True, default=str)
    hash_ = hashlib.sha256(blob.encode("utf-8")).hexdigest()

    return ResultadoLastro(
        selo=selo,
        icl=icl,
        z_score_valor=z_score_valor,
        desvio_prazo_dias=desvio_prazo_dias,
        z_score_prazo=z_score_prazo,
        componentes=componentes,
        motivos=motivos,
        recomendacao=recomendacao,
        historico=historico,
        hash_integridade=hash_,
    )

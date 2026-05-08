"""
Classificador CNAE · API IBGE + fallback offline.

Dada uma string com código CNAE em QUALQUER formato usual no Brasil:

    "6201-5/01"       (subclasse formatada)
    "62.01-5-00"      (subclasse formatada alternativa)
    "6201501"         (subclasse sem pontuação — 7 dígitos)
    "62015"           (classe — 5 dígitos)
    "6201"            (classe sem DV — 4 dígitos)
    "62"              (divisão — 2 dígitos)

o módulo retorna uma :class:`CNAEClassificacao` com o caminho completo:
subclasse → classe → grupo → divisão → seção → segmento macro + cor.

Estratégia:
  1. **Cache em disco** (``data/cnae_cache.json``): amortiza chamadas à API
     entre execuções do Streamlit. TTL de 30 dias — CNAE é estável.
  2. **API IBGE** (``https://servicodados.ibge.gov.br/api/v2/cnae/``):
     fonte de verdade para descrições oficiais. Com timeout curto e retries.
  3. **Fallback offline** (tabelas de ``config.cnae_rules``): se a API
     estiver indisponível, classificamos pelos 2 primeiros dígitos e
     garantimos ao menos a SEÇÃO + segmento macro — suficiente para o
     dashboard macro da carteira.

Todas as funções são tolerantes a falhas — nunca levantam exceção para o
chamador. Em caso de erro, retornam ``CNAEClassificacao`` com ``nivel=None``
e descrição "Não classificado".
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

from config.cnae_rules import (
    CNAE_CACHE_PATH,
    CNAE_CACHE_TTL_HORAS,
    DIVISAO_DESCRICAO,
    DIVISAO_PARA_SECAO,
    IBGE_API_BASE,
    IBGE_API_RETRIES,
    IBGE_API_TIMEOUT_S,
    SECOES_CNAE,
    cor_do_segmento,
    segmento_da_secao,
)
from services.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Modelo
# =============================================================================
@dataclass
class CNAEClassificacao:
    """Resultado da classificação — todos os níveis preenchidos quando possível."""
    codigo_original: str
    codigo_normalizado: str
    nivel: Optional[str]           # 'subclasse' | 'classe' | 'divisao' | 'secao' | None
    descricao: str
    secao_letra: Optional[str]
    secao_nome: Optional[str]
    divisao: Optional[str]         # 2 dígitos
    divisao_desc: Optional[str]
    grupo: Optional[str]           # 3 dígitos
    classe: Optional[str]          # 5 dígitos
    subclasse: Optional[str]       # 7 dígitos
    segmento_macro: str
    cor: str
    fonte: str                     # 'api' | 'cache' | 'offline' | 'indefinido'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# =============================================================================
# Normalização do código
# =============================================================================
_LIMPEZA = re.compile(r"[^0-9]")


def normalizar_cnae(codigo: str) -> str:
    """Remove pontuação e zeros à esquerda espúrios — retorna só dígitos."""
    if codigo is None:
        return ""
    return _LIMPEZA.sub("", str(codigo))


def _detectar_nivel(codigo_num: str) -> Optional[str]:
    """Infere o nível a partir do tamanho dos dígitos.

    Tamanhos CNAE 2.3:
        7 -> subclasse (ex.: 6201501)
        5 -> classe     (ex.: 62015)
        4 -> classe sem DV (ex.: 6201) — tratado como classe
        3 -> grupo      (ex.: 620)
        2 -> divisão    (ex.: 62)
    """
    n = len(codigo_num)
    if n == 7:
        return "subclasse"
    if n == 5 or n == 4:
        return "classe"
    if n == 3:
        return "grupo"
    if n == 2:
        return "divisao"
    return None


# =============================================================================
# Cache em disco (JSON)
# =============================================================================
def _carregar_cache() -> dict[str, dict[str, Any]]:
    if not CNAE_CACHE_PATH.exists():
        return {}
    try:
        raw = json.loads(CNAE_CACHE_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        return raw
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache CNAE corrompido (%s) — recriando.", exc)
        return {}


def _salvar_cache(cache: dict[str, dict[str, Any]]) -> None:
    try:
        CNAE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CNAE_CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Falha ao persistir cache CNAE: %s", exc)


def _cache_get(codigo: str) -> Optional[dict[str, Any]]:
    cache = _carregar_cache()
    entry = cache.get(codigo)
    if not entry:
        return None
    # Verifica TTL
    ts = entry.get("_cached_at")
    if ts:
        try:
            when = datetime.fromisoformat(ts)
            if datetime.utcnow() - when > timedelta(hours=CNAE_CACHE_TTL_HORAS):
                return None
        except ValueError:
            return None
    return entry.get("data")


def _cache_put(codigo: str, data: dict[str, Any]) -> None:
    cache = _carregar_cache()
    cache[codigo] = {
        "_cached_at": datetime.utcnow().isoformat(timespec="seconds"),
        "data": data,
    }
    _salvar_cache(cache)


# =============================================================================
# Cliente API IBGE
# =============================================================================
def _chamar_ibge(endpoint: str) -> Optional[dict[str, Any]]:
    """GET em ``{IBGE_API_BASE}{endpoint}`` com timeout + retries.

    Retorna o JSON parseado ou None se falhar em todas as tentativas.
    ``requests`` é importado lazy — dessa forma o módulo permanece
    importável mesmo sem a biblioteca (cai direto no fallback offline).
    """
    try:
        import requests  # lazy
    except ImportError:
        logger.info("requests não disponível — usando fallback offline.")
        return None

    url = f"{IBGE_API_BASE}{endpoint}"
    for tentativa in range(1, IBGE_API_RETRIES + 2):
        try:
            resp = requests.get(url, timeout=IBGE_API_TIMEOUT_S)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                # Código inexistente — não adianta retentar
                return None
            logger.warning(
                "IBGE %s → HTTP %s (tentativa %d)", endpoint, resp.status_code, tentativa,
            )
        except Exception as exc:  # timeout, DNS, etc.
            logger.warning(
                "IBGE %s → erro %s (tentativa %d)", endpoint, exc, tentativa,
            )
        time.sleep(0.3 * tentativa)  # backoff simples
    return None


def _parse_resposta_subclasse(payload: dict[str, Any]) -> dict[str, Optional[str]]:
    """Extrai caminho completo da resposta de ``/subclasses/{id}``.

    Esperado (estrutura IBGE):
        {
          "id": "6201501",
          "descricao": "...",
          "classe": {
            "id": "62015", "descricao": "...",
            "grupo": {
              "id": "620", "descricao": "...",
              "divisao": {
                "id": "62", "descricao": "...",
                "secao": {"id": "J", "descricao": "..."}
              }
            }
          }
        }
    """
    classe = payload.get("classe") or {}
    grupo = classe.get("grupo") or {}
    divisao = grupo.get("divisao") or {}
    secao = divisao.get("secao") or {}

    return {
        "subclasse": str(payload.get("id") or ""),
        "subclasse_desc": payload.get("descricao"),
        "classe": str(classe.get("id") or "") or None,
        "classe_desc": classe.get("descricao"),
        "grupo": str(grupo.get("id") or "") or None,
        "divisao": str(divisao.get("id") or "") or None,
        "divisao_desc": divisao.get("descricao"),
        "secao_letra": (secao.get("id") or "").upper() or None,
        "secao_desc": secao.get("descricao"),
    }


def _parse_resposta_classe(payload: dict[str, Any]) -> dict[str, Optional[str]]:
    """Extrai caminho da resposta de ``/classes/{id}`` (sem subclasse)."""
    grupo = payload.get("grupo") or {}
    divisao = grupo.get("divisao") or {}
    secao = divisao.get("secao") or {}

    return {
        "subclasse": None,
        "subclasse_desc": None,
        "classe": str(payload.get("id") or "") or None,
        "classe_desc": payload.get("descricao"),
        "grupo": str(grupo.get("id") or "") or None,
        "divisao": str(divisao.get("id") or "") or None,
        "divisao_desc": divisao.get("descricao"),
        "secao_letra": (secao.get("id") or "").upper() or None,
        "secao_desc": secao.get("descricao"),
    }


# =============================================================================
# Fallback offline
# =============================================================================
def _classificar_offline(codigo_num: str, nivel: Optional[str]) -> dict[str, Optional[str]]:
    """Deriva SEÇÃO + descrição de divisão a partir das tabelas embutidas.

    Não retorna descrição da classe/subclasse — para isso precisaríamos da API.
    """
    divisao = codigo_num[:2] if len(codigo_num) >= 2 else None
    secao_letra = DIVISAO_PARA_SECAO.get(divisao) if divisao else None
    secao_desc = SECOES_CNAE.get(secao_letra, {}).get("descricao") if secao_letra else None
    divisao_desc = DIVISAO_DESCRICAO.get(divisao) if divisao else None

    return {
        "subclasse": codigo_num if nivel == "subclasse" else None,
        "subclasse_desc": None,
        "classe": codigo_num[:5] if len(codigo_num) >= 5 else None,
        "classe_desc": None,
        "grupo": codigo_num[:3] if len(codigo_num) >= 3 else None,
        "divisao": divisao,
        "divisao_desc": divisao_desc,
        "secao_letra": secao_letra,
        "secao_desc": secao_desc,
    }


# =============================================================================
# API pública
# =============================================================================
def classificar_cnae(codigo: str) -> CNAEClassificacao:
    """Classifica um CNAE completo. Nunca levanta exceção.

    Args:
        codigo: CNAE em qualquer formato (com ou sem pontuação).

    Returns:
        :class:`CNAEClassificacao` com descrições, níveis, segmento macro e cor.
    """
    original = str(codigo or "")
    num = normalizar_cnae(codigo)
    nivel = _detectar_nivel(num)

    # ---------------- Código inválido ----------------
    if not num or nivel is None:
        return CNAEClassificacao(
            codigo_original=original,
            codigo_normalizado=num,
            nivel=None,
            descricao="CNAE inválido",
            secao_letra=None,
            secao_nome=None,
            divisao=None,
            divisao_desc=None,
            grupo=None,
            classe=None,
            subclasse=None,
            segmento_macro="Não classificado",
            cor="#7C8CA8",
            fonte="indefinido",
        )

    # ---------------- Cache ----------------
    cached = _cache_get(num)
    if cached:
        return _montar_classificacao(original, num, cached, fonte="cache")

    # ---------------- API IBGE ----------------
    dados = _buscar_na_api(num, nivel)
    if dados:
        _cache_put(num, dados)
        return _montar_classificacao(original, num, dados, fonte="api")

    # ---------------- Fallback offline ----------------
    dados_off = _classificar_offline(num, nivel)
    return _montar_classificacao(original, num, dados_off, fonte="offline")


def _buscar_na_api(num: str, nivel: str) -> Optional[dict[str, Any]]:
    """Encaminha para o endpoint correto da API IBGE."""
    try:
        if nivel == "subclasse":
            payload = _chamar_ibge(f"/subclasses/{num}")
            if payload:
                return _parse_resposta_subclasse(payload)
        if nivel == "classe":
            # Garante 5 dígitos — alguns datasets vêm com 4 (sem DV)
            classe_id = num.ljust(5, "0") if len(num) == 4 else num[:5]
            payload = _chamar_ibge(f"/classes/{classe_id}")
            if payload:
                return _parse_resposta_classe(payload)
        # Para 'grupo' e 'divisao' não há endpoint direto oficial — cai offline
    except Exception as exc:  # defensivo
        logger.warning("Falha na chamada API IBGE (%s): %s", num, exc)
    return None


def _montar_classificacao(
    original: str,
    num: str,
    dados: dict[str, Optional[str]],
    fonte: str,
) -> CNAEClassificacao:
    """Constrói :class:`CNAEClassificacao` a partir do dict bruto + metadados."""
    secao_letra = (dados.get("secao_letra") or None)
    secao_info = SECOES_CNAE.get(secao_letra, {}) if secao_letra else {}
    secao_nome = dados.get("secao_desc") or secao_info.get("descricao")
    segmento = segmento_da_secao(secao_letra) if secao_letra else "Não classificado"
    cor = cor_do_segmento(segmento)

    # Descrição mais específica disponível
    descricao = (
        dados.get("subclasse_desc")
        or dados.get("classe_desc")
        or dados.get("divisao_desc")
        or secao_nome
        or "Não classificado"
    )

    # Nivel efetivamente resolvido
    if dados.get("subclasse"):
        nivel_efetivo = "subclasse"
    elif dados.get("classe"):
        nivel_efetivo = "classe"
    elif dados.get("divisao"):
        nivel_efetivo = "divisao"
    elif secao_letra:
        nivel_efetivo = "secao"
    else:
        nivel_efetivo = None

    return CNAEClassificacao(
        codigo_original=original,
        codigo_normalizado=num,
        nivel=nivel_efetivo,
        descricao=descricao,
        secao_letra=secao_letra,
        secao_nome=secao_nome,
        divisao=dados.get("divisao"),
        divisao_desc=dados.get("divisao_desc"),
        grupo=dados.get("grupo"),
        classe=dados.get("classe"),
        subclasse=dados.get("subclasse"),
        segmento_macro=segmento,
        cor=cor,
        fonte=fonte,
    )


# =============================================================================
# Enriquecimento em massa (para DataFrames)
# =============================================================================
def enriquecer_dataframe(
    df: pd.DataFrame,
    coluna_cnae: str = "cnae",
    prefixo: str = "cnae_",
) -> pd.DataFrame:
    """Adiciona colunas de segmento/seção a um DataFrame a partir do CNAE.

    Deduplica os CNAEs antes de classificar — se a carteira tem 10 mil
    sacados mas só 300 CNAEs únicos, chamamos a API 300 vezes (não 10 mil).

    Args:
        df: DataFrame com a coluna de CNAE.
        coluna_cnae: nome da coluna que contém o código CNAE.
        prefixo: prefixo para as colunas geradas.

    Returns:
        DataFrame com as colunas:
            <prefixo>segmento, <prefixo>secao, <prefixo>secao_nome,
            <prefixo>descricao, <prefixo>cor, <prefixo>fonte
        Se a coluna de CNAE não existir, devolve o DataFrame sem alterações.
    """
    if coluna_cnae not in df.columns:
        logger.info("enriquecer_dataframe: coluna '%s' ausente — ignorando.", coluna_cnae)
        return df

    codigos_unicos = (
        df[coluna_cnae].dropna().astype(str).map(str.strip).replace("", pd.NA).dropna().unique()
    )
    mapa: dict[str, CNAEClassificacao] = {
        c: classificar_cnae(c) for c in codigos_unicos
    }

    def _attr(codigo: Any, campo: str, default: Any = None) -> Any:
        if pd.isna(codigo) or codigo is None:
            return default
        c = str(codigo).strip()
        obj = mapa.get(c)
        return getattr(obj, campo, default) if obj else default

    df = df.copy()
    df[f"{prefixo}segmento"] = df[coluna_cnae].map(
        lambda c: _attr(c, "segmento_macro", "Não classificado")
    )
    df[f"{prefixo}secao"] = df[coluna_cnae].map(lambda c: _attr(c, "secao_letra"))
    df[f"{prefixo}secao_nome"] = df[coluna_cnae].map(lambda c: _attr(c, "secao_nome"))
    df[f"{prefixo}descricao"] = df[coluna_cnae].map(lambda c: _attr(c, "descricao"))
    df[f"{prefixo}cor"] = df[coluna_cnae].map(lambda c: _attr(c, "cor", "#7C8CA8"))
    df[f"{prefixo}fonte"] = df[coluna_cnae].map(lambda c: _attr(c, "fonte", "indefinido"))
    return df


def resumir_segmentos(
    df: pd.DataFrame,
    coluna_segmento: str = "cnae_segmento",
    coluna_valor: Optional[str] = None,
) -> pd.DataFrame:
    """Resumo da carteira por segmento econômico.

    Útil para a Visão Macro: barra de concentração por segmento.

    Args:
        df: DataFrame já enriquecido (via :func:`enriquecer_dataframe`).
        coluna_segmento: coluna com o segmento macro.
        coluna_valor: se fornecido, soma os valores por segmento além de contar.

    Returns:
        DataFrame com colunas ``segmento, sacados, share_sacados`` e, quando
        ``coluna_valor`` é informado, também ``volume`` e ``share_volume``.
    """
    if coluna_segmento not in df.columns:
        return pd.DataFrame(columns=["segmento", "sacados", "share_sacados"])

    grp = df.groupby(coluna_segmento, dropna=False)
    resumo = grp.size().reset_index(name="sacados")
    resumo = resumo.rename(columns={coluna_segmento: "segmento"})
    total_sacados = resumo["sacados"].sum()
    resumo["share_sacados"] = (
        resumo["sacados"] / total_sacados if total_sacados > 0 else 0.0
    )

    if coluna_valor and coluna_valor in df.columns:
        volumes = grp[coluna_valor].sum().reset_index(name="volume")
        volumes = volumes.rename(columns={coluna_segmento: "segmento"})
        resumo = resumo.merge(volumes, on="segmento", how="left")
        total_vol = resumo["volume"].sum()
        resumo["share_volume"] = (
            resumo["volume"] / total_vol if total_vol > 0 else 0.0
        )

    # Ordena do maior para o menor número de sacados
    return resumo.sort_values("sacados", ascending=False).reset_index(drop=True)


def classificar_varios(codigos: Iterable[str]) -> list[CNAEClassificacao]:
    """Classifica uma lista de códigos com deduplicação automática."""
    cache_local: dict[str, CNAEClassificacao] = {}
    resultados: list[CNAEClassificacao] = []
    for c in codigos:
        num = normalizar_cnae(c)
        if num not in cache_local:
            cache_local[num] = classificar_cnae(c)
        resultados.append(cache_local[num])
    return resultados

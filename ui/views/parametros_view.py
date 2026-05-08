"""
View · Parâmetros e Modelo · FIDC Insight (Governança).

Tela de governança simples e objetiva: dá transparência ao analista, gestor
e auditor sobre as premissas atualmente em uso pelo motor de score, pelo
motor de pricing e pelo enquadramento parametrizável da carteira.

Conteúdo:
  - Pesos das dimensões do score (qualidade, liquidez, inadimplência, regional)
  - Tabela de classificação rating ↔ prêmio ↔ PD
  - Limites internos de concentração (parametrizáveis conforme política do fundo)
  - Fator regional por UF
  - Premissas de cálculo (LGD, ATRASO_CAP_DIAS, divisor de prazo)
  - Selic em uso e origem
  - Versão / data dos parâmetros (lida do mtime do business_rules.py)

Os valores são lidos diretamente de ``config/business_rules.py`` — esta view
é apenas a janela de leitura. Para alterar parâmetros, editar o módulo de
configuração e versionar a mudança no controle de versão do projeto.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import config.business_rules as br
from services.bcb_api import buscar_selic, selic_origem_str
from ui.components import (
    render_callout,
    render_card_head,
    render_kpi_row,
    render_page_header,
    render_section_header,
    section_divider,
)
from utils.formatters import formatar_percentual


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _versao_parametros() -> str:
    """Versão do conjunto de parâmetros — usa mtime do business_rules.py.

    Se não conseguir ler o arquivo, retorna 'n/d'. Não é uma versão semântica;
    é apenas uma referência temporal auditável da última edição do módulo.
    """
    try:
        caminho = Path(br.__file__)
        ts = os.path.getmtime(caminho)
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    except Exception:  # noqa: BLE001 — UI defensiva, governança não pode quebrar
        return "n/d"


def _df_pesos() -> pd.DataFrame:
    """Pesos do score em tabela legível."""
    return pd.DataFrame(
        [
            {"Dimensão": "Qualidade creditícia", "Peso": br.PESOS["qualidade"]},
            {"Dimensão": "Liquidez",             "Peso": br.PESOS["liquidez"]},
            {"Dimensão": "Inadimplência (inv.)", "Peso": br.PESOS["inadimplencia"]},
            {"Dimensão": "Fator regional",       "Peso": br.PESOS["regional"]},
        ]
    )


def _df_classificacoes() -> pd.DataFrame:
    """Tabela rating → prêmio → PD."""
    return pd.DataFrame(
        [
            {
                "Score mín.": vmin,
                "Score máx.": vmax,
                "Rating":     rating,
                "Prêmio a.a.": premio,
                "PD anual":   pd_anual,
            }
            for (vmin, vmax, rating, premio, pd_anual) in br.CLASSIFICACOES
        ]
    )


def _df_fator_regional() -> pd.DataFrame:
    """Fator regional por UF — ordenado por risco (maior → menor)."""
    rows = [{"UF": uf, "Fator": fator} for uf, fator in br.FATOR_REGIONAL.items()]
    df = pd.DataFrame(rows).sort_values("Fator", ascending=False).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    """Renderiza a view de Parâmetros e Modelo."""

    render_page_header(
        kicker="Governança",
        titulo="Parâmetros e Modelo",
        subtitulo=(
            "Transparência sobre as premissas em uso pelo motor de score, pelo "
            "pricing e pelo enquadramento parametrizável da carteira."
        ),
    )

    versao = _versao_parametros()
    selic = buscar_selic()
    origem_selic = selic_origem_str(selic)

    # ------------------------------------------------------------------
    # 1. Painel de cabeçalho — versão + Selic em uso + LGD
    # ------------------------------------------------------------------
    render_kpi_row(
        [
            {
                "label": "Versão dos parâmetros",
                "value": versao,
                "sub": "última edição de business_rules.py",
                "variant": "ink",
            },
            {
                "label": "Selic em uso",
                "value": formatar_percentual(selic),
                "sub": origem_selic,
                "variant": "premium",
            },
            {
                "label": "LGD padrão",
                "value": formatar_percentual(br.LGD_PADRAO),
                "sub": "loss given default · IFRS 9",
                "variant": "accent",
            },
            {
                "label": "Cap de atraso",
                "value": f"{br.ATRASO_CAP_DIAS:.0f} dias",
                "sub": "normalização do componente de inadimplência",
                "variant": "cau",
            },
        ],
        cols=4,
    )

    section_divider()

    # ------------------------------------------------------------------
    # 2. Pesos do score
    # ------------------------------------------------------------------
    render_section_header(
        titulo="Pesos das dimensões do score",
        subtitulo=(
            "Score = (qualidade · w₁ + liquidez · w₂ + inadimplência · w₃ "
            "+ regional · w₄) × 1.000. Pesos somam 1,00."
        ),
    )

    df_pesos = _df_pesos()
    soma_pesos = float(df_pesos["Peso"].sum())

    col_tab, col_msg = st.columns([7, 5], gap="medium")
    with col_tab:
        render_card_head(
            kicker="Composição",
            titulo="Pesos por dimensão",
        )
        st.dataframe(
            df_pesos.style.format({"Peso": "{:.2%}"}),
            use_container_width=True,
            hide_index=True,
        )

    with col_msg:
        render_card_head(
            kicker="Sanidade",
            titulo="Verificação dos pesos",
        )
        if abs(soma_pesos - 1.0) < 1e-6:
            render_callout(
                f"✅ Soma dos pesos = **{soma_pesos:.2f}** — consistente.",
                tipo="destaque",
            )
        else:
            render_callout(
                f"⚠️ Soma dos pesos = **{soma_pesos:.4f}** — esperado 1,00. "
                "Revisar `config/business_rules.PESOS`.",
                tipo="alerta",
            )

    section_divider()

    # ------------------------------------------------------------------
    # 3. Classificação de rating
    # ------------------------------------------------------------------
    render_section_header(
        titulo="Tabela de rating, prêmio e probabilidade de default",
        subtitulo=(
            "Score numérico (0–1.000) é convertido em rating; cada rating define "
            "o prêmio cobrado sobre a Selic e a PD anual usada na ECL."
        ),
    )

    df_class = _df_classificacoes()
    st.dataframe(
        df_class.style.format(
            {"Prêmio a.a.": "{:.2%}", "PD anual": "{:.2%}"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    section_divider()

    # ------------------------------------------------------------------
    # 4. Limites internos parametrizáveis
    # ------------------------------------------------------------------
    render_section_header(
        titulo="Limites internos de concentração",
        subtitulo=(
            "Limites parametrizados (política/regulamento do fundo). "
            "Para alterar, editar `config/business_rules.py`."
        ),
    )

    df_limites = pd.DataFrame(
        [
            {
                "Parâmetro": "Limite por sacado",
                "Valor": br.LIMITE_POR_SACADO,
                "Descrição": "Máximo % do PL exposto a um único sacado",
            },
            {
                "Parâmetro": "Limite por UF",
                "Valor": br.LIMITE_POR_UF,
                "Descrição": "Máximo % do PL exposto a um estado",
            },
            {
                "Parâmetro": "Zona de alerta UF",
                "Valor": br.ZONA_ALERTA_UF,
                "Descrição": "Margem de alerta antes do limite estadual",
            },
        ]
    )
    st.dataframe(
        df_limites.style.format({"Valor": "{:.0%}"}),
        use_container_width=True,
        hide_index=True,
    )

    section_divider()

    # ------------------------------------------------------------------
    # 5. Premissas de cálculo (LGD, ECL, normalização, prazo)
    # ------------------------------------------------------------------
    render_section_header(
        titulo="Premissas de cálculo",
        subtitulo="Constantes usadas pelo motor de pricing e pelo motor de score.",
    )

    df_premissas = pd.DataFrame(
        [
            {
                "Premissa": "LGD padrão",
                "Valor": f"{br.LGD_PADRAO:.0%}",
                "Uso": "Loss Given Default na fórmula da ECL (IFRS 9)",
            },
            {
                "Premissa": "ATRASO_CAP_DIAS",
                "Valor": f"{br.ATRASO_CAP_DIAS:.0f} dias",
                "Uso": "Teto de normalização do componente de atraso no score",
            },
            {
                "Premissa": "PRAZO_DIVISOR_ANOS",
                "Valor": f"{br.PRAZO_DIVISOR_ANOS:.0f}",
                "Uso": "Conversão dias → anos (mercado BR usa 365)",
            },
            {
                "Premissa": "EWS · peso atraso",
                "Valor": f"{br.EWS_PESO_ATRASO:.2f}",
                "Uso": "Peso do atraso no Early Warning System",
            },
            {
                "Premissa": "EWS · peso inadimplência",
                "Valor": f"{br.EWS_PESO_INADIMPLENCIA:.2f}",
                "Uso": "Peso da inadimplência no EWS",
            },
            {
                "Premissa": "EWS · divisor atraso",
                "Valor": f"{br.EWS_DIVISOR_ATRASO_DIAS:.1f} dias",
                "Uso": "Normaliza atraso para escala 0–1 no EWS",
            },
        ]
    )
    st.dataframe(df_premissas, use_container_width=True, hide_index=True)

    section_divider()

    # ------------------------------------------------------------------
    # 6. Fator regional por UF (expansível para não poluir)
    # ------------------------------------------------------------------
    render_section_header(
        titulo="Fator regional por UF",
        subtitulo=(
            "Multiplicador de risco aplicado ao componente regional. "
            "Valores > 1,00 indicam UF com inadimplência histórica acima da média."
        ),
    )

    df_reg = _df_fator_regional()
    df_reg["Default"] = df_reg["UF"].apply(
        lambda uf: "—" if uf in br.FATOR_REGIONAL else f"{br.FATOR_REGIONAL_DEFAULT:.2f}"
    )

    with st.expander(f"Ver fatores regionais ({len(df_reg)} UFs)", expanded=False):
        st.dataframe(
            df_reg[["UF", "Fator"]].style.format({"Fator": "{:.2f}"}),
            use_container_width=True,
            hide_index=True,
            height=400,
        )
        render_callout(
            f"UFs sem mapeamento explícito recebem fator default **"
            f"{br.FATOR_REGIONAL_DEFAULT:.2f}**.",
            tipo="info",
        )

    section_divider()

    # ------------------------------------------------------------------
    # 7. Rodapé — orientação de governança
    # ------------------------------------------------------------------
    render_callout(
        "**Governança:** alterações nestes parâmetros impactam diretamente o "
        "score, o pricing e o enquadramento da carteira. Toda mudança deve ser "
        "registrada via controle de versão do projeto e validada pelo comitê "
        "de risco do fundo. Esta tela é somente leitura.",
        tipo="tip",
    )

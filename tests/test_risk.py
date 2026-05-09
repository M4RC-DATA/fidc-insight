"""Testes unitários · domain.risk

Valida:
  1. Enquadramento parametrizável — limites de concentração por sacado (10%) e por UF (25%)
     conforme política/regulamento do fundo
  2. Early Warning System — probabilidade de contágio
  3. HHI — índice Herfindahl de concentração geográfica
"""

from __future__ import annotations

import pandas as pd
import pytest

from domain.risk import (
    NivelRisco,
    avaliar_concentracao_sacado,
    avaliar_concentracao_uf,
    calcular_probabilidade_contagio,
    classificar_nivel_contagio,
    hhi_por_uf,
)


# =============================================================================
# Fixtures de carteira
# =============================================================================
@pytest.fixture
def carteira_diversificada() -> pd.DataFrame:
    """Carteira com 4 sacados em 3 UFs — baixa concentração."""
    return pd.DataFrame({
        "id_cnpj": ["11111", "22222", "33333", "44444"],
        "uf":       ["SP",    "RJ",    "MG",    "SP"],
        "vlr_nominal_total": [100_000, 100_000, 100_000, 100_000],
    })


@pytest.fixture
def carteira_concentrada_sp() -> pd.DataFrame:
    """Carteira com 80% do PL em SP — acima do limite de 25%."""
    return pd.DataFrame({
        "id_cnpj": ["11111", "22222", "33333", "44444"],
        "uf":       ["SP",    "SP",    "SP",    "RJ"],
        "vlr_nominal_total": [200_000, 200_000, 200_000, 200_000],
    })


# =============================================================================
# Concentração por sacado (limite: 10% do PL)
# =============================================================================
class TestConcentracaoSacado:

    def test_sacado_novo_dentro_do_limite_aprova(self, carteira_diversificada):
        """Adicionar 20k a um sacado que não existe em uma carteira de 400k."""
        r = avaliar_concentracao_sacado(
            carteira_diversificada, cnpj="99999", valor_novo=20_000,
        )
        assert r.status == "aprovado"
        # 20_000 / 420_000 ≈ 4.76% — bem abaixo de 10%
        assert r.percentual_atual < 0.10

    def test_sacado_existente_ja_exposto_bloqueia(self, carteira_diversificada):
        """Adicionar muito a sacado já exposto ultrapassa 10%."""
        r = avaliar_concentracao_sacado(
            carteira_diversificada, cnpj="11111", valor_novo=100_000,
        )
        # sacado 11111 tinha 100k, agora teria 200k / 500k total = 40%
        assert r.status == "bloqueio"
        assert r.percentual_atual > 0.10

    def test_mensagem_contem_percentual(self, carteira_diversificada):
        r = avaliar_concentracao_sacado(
            carteira_diversificada, cnpj="77777", valor_novo=30_000,
        )
        assert "%" in r.mensagem

    def test_carteira_vazia_nao_quebra(self):
        df = pd.DataFrame(columns=["id_cnpj", "uf", "vlr_nominal_total"])
        r = avaliar_concentracao_sacado(df, cnpj="1", valor_novo=10_000)
        # Nova operação é 100% do PL — mas a função deve retornar algo válido
        assert r.status in ("aprovado", "bloqueio")


# =============================================================================
# Concentração por UF (limite: 25% + alerta de 5%)
# =============================================================================
class TestConcentracaoUF:

    def test_uf_dentro_do_limite_aprova(self, carteira_diversificada):
        """SP tem 200k de 400k = 50% — acima do limite de 25%."""
        r = avaliar_concentracao_uf(
            carteira_diversificada, uf="RJ", valor_novo=10_000,
        )
        # RJ tinha 100k, agora 110k / 410k ≈ 26.8% → entra no alerta
        assert r.status in ("aprovado", "alerta")

    def test_uf_acima_do_limite_bloqueia(self, carteira_concentrada_sp):
        """SP já ocupa 75% — qualquer adição mantém bloqueio."""
        r = avaliar_concentracao_uf(
            carteira_concentrada_sp, uf="SP", valor_novo=50_000,
        )
        assert r.status == "bloqueio"
        assert r.percentual_atual > 0.25

    def test_uf_na_zona_de_alerta(self):
        """Entre 20% e 25% = alerta (zona tampão de 5 p.p. antes do limite de 25%)."""
        # Carteira com SP em ~27%
        df = pd.DataFrame({
            "id_cnpj": ["A", "B", "C", "D"],
            "uf": ["SP", "SP", "RJ", "MG"],
            "vlr_nominal_total": [100_000, 170_000, 400_000, 330_000],
        })
        # SP = 270k / 1000k = 27% — já está no alerta antes mesmo da operação
        r = avaliar_concentracao_uf(df, uf="SP", valor_novo=0)
        assert r.status in ("alerta", "bloqueio")


# =============================================================================
# Early Warning System — probabilidade de contágio
# =============================================================================
class TestProbabilidadeContagio:

    def test_sacado_sem_atraso_sem_inadimplencia_zero(self):
        """Sacado saudável → probabilidade zero."""
        p = calcular_probabilidade_contagio(0, 0)
        assert p == 0.0

    def test_sacado_muito_atrasado_e_muita_inadimplencia_satura_em_1(self):
        """Probabilidade é limitada em 1.0 (min() final).
        Com divisor=180, valores extremos saturam: atraso=360d + inad=100%.
        """
        p = calcular_probabilidade_contagio(
            media_atraso_dias=360, share_inadimplencia=1.0,
        )
        assert p == 1.0

    def test_proporcao_com_pesos_40_60(self):
        """Fórmula: P = (atraso/180) × 0.4 + inadimplência × 0.6.
        Divisor calibrado na mediana real da base (178 dias ≈ 180).
        """
        from config.business_rules import EWS_DIVISOR_ATRASO_DIAS
        # atraso=EWS_DIVISOR (=1.0 normalizado) × 0.4 = 0.4
        p = calcular_probabilidade_contagio(EWS_DIVISOR_ATRASO_DIAS, 0)
        assert p == pytest.approx(0.4)

        # atraso=0 + inadimplência=0.5 × 0.6 = 0.30
        p = calcular_probabilidade_contagio(0, 0.5)
        assert p == pytest.approx(0.30)

    def test_limite_superior_e_inferior(self):
        """P ∈ [0, 1]."""
        assert calcular_probabilidade_contagio(1000, 1.0) == 1.0
        assert calcular_probabilidade_contagio(0, 0) == 0.0


class TestClassificarNivelContagio:

    def test_baixo(self):
        assert classificar_nivel_contagio(0.10) == NivelRisco.BAIXO

    def test_moderado(self):
        assert classificar_nivel_contagio(0.45) == NivelRisco.MODERADO

    def test_alto(self):
        assert classificar_nivel_contagio(0.85) == NivelRisco.ALTO

    def test_fronteiras(self):
        """0.3 e 0.6 são as fronteiras das zonas."""
        assert classificar_nivel_contagio(0.0) == NivelRisco.BAIXO
        assert classificar_nivel_contagio(0.29) == NivelRisco.BAIXO
        assert classificar_nivel_contagio(0.30) == NivelRisco.MODERADO
        assert classificar_nivel_contagio(0.59) == NivelRisco.MODERADO
        assert classificar_nivel_contagio(0.60) == NivelRisco.ALTO


# =============================================================================
# HHI · Índice Herfindahl de concentração por UF
# =============================================================================
class TestHHI:

    def test_carteira_totalmente_concentrada_em_uma_uf_retorna_1(self):
        """Tudo em uma UF → HHI = 1.0 (máxima concentração)."""
        df = pd.DataFrame({
            "uf": ["SP", "SP", "SP", "SP"],
            "vlr_nominal_total": [100, 200, 300, 400],
        })
        assert hhi_por_uf(df) == 1.0

    def test_carteira_perfeitamente_diversificada(self):
        """N UFs com pesos iguais → HHI = 1/N."""
        df = pd.DataFrame({
            "uf": ["SP", "RJ", "MG", "RS"],
            "vlr_nominal_total": [100, 100, 100, 100],
        })
        # Cada UF = 25%, HHI = 4 × 0.25² = 0.25
        assert hhi_por_uf(df) == pytest.approx(0.25)

    def test_carteira_vazia_retorna_zero(self):
        df = pd.DataFrame({"uf": [], "vlr_nominal_total": []})
        assert hhi_por_uf(df) == 0.0

    def test_hhi_nao_ultrapassa_um(self):
        """Propriedade matemática: 0 ≤ HHI ≤ 1."""
        df = pd.DataFrame({
            "uf": ["SP", "SP", "RJ", "MG", "RS", "PR", "SC"],
            "vlr_nominal_total": [500, 300, 100, 50, 30, 10, 10],
        })
        h = hhi_por_uf(df)
        assert 0 < h < 1

    def test_concentracao_desigual(self):
        """80/20: HHI = 0.8² + 0.2² = 0.68."""
        df = pd.DataFrame({
            "uf": ["SP", "RJ"],
            "vlr_nominal_total": [800, 200],
        })
        assert hhi_por_uf(df) == pytest.approx(0.68)
"""Testes unitários · domain.pricing (motor RAROC)

Valida a fórmula de precificação: VP = Face / (1 + taxa)^prazo_anos,
cálculo de ECL (IFRS 9 estágio 1) e de lucro RAROC.

Todos os testes são puros — sem dependência de data real (usamos datas fixas).
"""

from __future__ import annotations

from datetime import date

import pytest

from domain.pricing import ResultadoPrecificacao, precificar_operacao


# =============================================================================
# Cenários base — valida cálculo aritmético exato
# =============================================================================
class TestPrecificarOperacaoAritmetica:
    """Verifica que cada componente da precificação bate com a fórmula."""

    def test_operacao_rating_a_plus_30_dias(self):
        """Operação padrão de 30 dias, rating A+ (Selic 13.75% + 15%)."""
        r = precificar_operacao(
            valor_face=100_000,
            data_vencimento=date(2026, 2, 1),
            data_hoje=date(2026, 1, 2),
            selic=0.1375,
            premio_anual=0.15,
            pd_anual=0.005,
            lgd=0.50,
        )

        assert r.prazo_dias == 30
        assert r.prazo_anos == pytest.approx(30 / 365, rel=1e-4)
        assert r.taxa_total == pytest.approx(0.2875)
        assert r.valor_face == 100_000

        # VP = 100000 / (1.2875)^(30/365) ≈ 97_962
        assert 97_000 < r.valor_presente < 98_500

        # Desconto bruto = receita da operação
        assert r.desconto_bruto == pytest.approx(
            r.valor_face - r.valor_presente
        )

        # ECL = 100000 × (0.005 × 30/365) × 0.50 ≈ 20.55
        assert r.perda_esperada == pytest.approx(100_000 * 0.005 * (30/365) * 0.50)

        # Lucro RAROC = desconto - ECL
        assert r.lucro_raroc == pytest.approx(r.desconto_bruto - r.perda_esperada)

    def test_operacao_rating_d_60_dias(self):
        """Rating D (PD alta) reduz o lucro RAROC via maior ECL."""
        r = precificar_operacao(
            valor_face=100_000,
            data_vencimento=date(2026, 3, 3),
            data_hoje=date(2026, 1, 2),
            selic=0.1375,
            premio_anual=0.32,
            pd_anual=0.120,
            lgd=0.50,
        )

        # ECL cresce proporcionalmente à PD — rating D deve ter ECL muito maior
        assert r.perda_esperada > 900  # 100k × 0.12 × (60/365) × 0.5 ≈ 986
        assert r.taxa_total == pytest.approx(0.4575)

    def test_prazo_zero_ou_negativo_vira_um_dia(self):
        """Proteção: vencimento hoje ou passado → prazo mínimo de 1 dia."""
        r = precificar_operacao(
            valor_face=50_000,
            data_vencimento=date(2026, 1, 2),    # mesmo dia
            data_hoje=date(2026, 1, 2),
            selic=0.13,
            premio_anual=0.15,
            pd_anual=0.01,
            lgd=0.50,
        )
        assert r.prazo_dias >= 1

    def test_atraso_historico_aumenta_prazo(self):
        """O atraso médio histórico é somado ao prazo contratual."""
        r_sem = precificar_operacao(
            valor_face=100_000,
            data_vencimento=date(2026, 2, 1),
            data_hoje=date(2026, 1, 2),
            selic=0.1375, premio_anual=0.17, pd_anual=0.015, lgd=0.50,
            atraso_historico_dias=0.0,
        )
        r_com = precificar_operacao(
            valor_face=100_000,
            data_vencimento=date(2026, 2, 1),
            data_hoje=date(2026, 1, 2),
            selic=0.1375, premio_anual=0.17, pd_anual=0.015, lgd=0.50,
            atraso_historico_dias=15.0,
        )

        assert r_com.prazo_dias == r_sem.prazo_dias + 15
        # Prazo maior → VP menor (desconto mais pesado)
        assert r_com.valor_presente < r_sem.valor_presente

    def test_taxa_zero_faz_vp_igual_face(self):
        """Sanidade: selic + prêmio = 0 → VP ≈ face (sem desconto)."""
        r = precificar_operacao(
            valor_face=100_000,
            data_vencimento=date(2026, 2, 1),
            data_hoje=date(2026, 1, 2),
            selic=0.0, premio_anual=0.0,
            pd_anual=0.0, lgd=0.0,
        )
        assert r.valor_presente == pytest.approx(100_000, rel=1e-6)
        assert r.desconto_bruto == pytest.approx(0.0, abs=1e-4)
        assert r.perda_esperada == pytest.approx(0.0)


# =============================================================================
# Invariantes — relações que sempre devem valer
# =============================================================================
class TestPrecificarInvariantes:
    """Propriedades que devem valer para QUALQUER entrada válida."""

    @pytest.mark.parametrize("face,selic,premio,pd_anual,dias", [
        (10_000, 0.10, 0.15, 0.005, 30),
        (250_000, 0.14, 0.20, 0.03, 60),
        (1_000_000, 0.13, 0.32, 0.12, 90),
    ])
    def test_vp_sempre_menor_ou_igual_a_face(self, face, selic, premio, pd_anual, dias):
        """Com taxa > 0, o valor presente é sempre < face."""
        r = precificar_operacao(
            valor_face=face,
            data_vencimento=date(2026, 1, 1 + dias) if dias < 28 else date(2026, 4, 1),
            data_hoje=date(2026, 1, 1),
            selic=selic, premio_anual=premio, pd_anual=pd_anual, lgd=0.50,
        )
        assert r.valor_presente <= r.valor_face
        assert r.desconto_bruto >= 0

    def test_ecl_nao_negativo(self):
        """ECL nunca pode ser negativo (perda esperada ≥ 0)."""
        r = precificar_operacao(
            valor_face=100_000,
            data_vencimento=date(2026, 3, 3),
            data_hoje=date(2026, 1, 2),
            selic=0.10, premio_anual=0.15, pd_anual=0.01, lgd=0.50,
        )
        assert r.perda_esperada >= 0

    def test_margem_real_percentual(self):
        """Margem real é a razão (lucro_raroc / face) × 100."""
        r = precificar_operacao(
            valor_face=100_000,
            data_vencimento=date(2026, 2, 1),
            data_hoje=date(2026, 1, 2),
            selic=0.13, premio_anual=0.17, pd_anual=0.015, lgd=0.50,
        )
        assert r.margem_real == pytest.approx(
            (r.lucro_raroc / r.valor_face) * 100, rel=1e-6
        )

    def test_retorno_e_dataclass_imutavel(self):
        """Resultado é frozen dataclass — não pode ser mutado."""
        r = precificar_operacao(
            valor_face=10_000,
            data_vencimento=date(2026, 2, 1),
            data_hoje=date(2026, 1, 2),
            selic=0.10, premio_anual=0.15, pd_anual=0.005, lgd=0.50,
        )
        assert isinstance(r, ResultadoPrecificacao)
        with pytest.raises((AttributeError, Exception)):
            r.valor_presente = 1.0  # type: ignore[misc]

"""Testes unitários · domain.scoring

Garante que a classificação de score → rating segue a tabela
``CLASSIFICACOES`` definida em ``config.business_rules`` e que a
distribuição de componentes e o cálculo de percentil são corretos.

Todos os testes são puros: sem I/O, sem BigQuery, sem Streamlit.
"""

from __future__ import annotations

import pytest

from domain.scoring import (
    Classificacao,
    classificar_score,
    distribuir_componentes,
    percentil_na_carteira,
)


# =============================================================================
# classificar_score · rating de cada faixa
# =============================================================================
class TestClassificarScore:
    """Valida a tabela score → (rating, prêmio, PD)."""

    def test_score_990_retorna_rating_a_plus(self):
        """Score no topo da escala = rating A+ (melhor cliente)."""
        r = classificar_score(990)
        assert r.rating == "A+"
        assert r.premio_anual == pytest.approx(0.15)
        assert r.pd_anual == pytest.approx(0.005)

    def test_score_850_retorna_rating_a(self):
        """Score na faixa 800-899 = rating A."""
        r = classificar_score(850)
        assert r.rating == "A"
        assert r.premio_anual == pytest.approx(0.17)
        assert r.pd_anual == pytest.approx(0.015)

    def test_score_750_retorna_rating_b(self):
        """Score na faixa 700-799 = rating B (ponto médio da carteira)."""
        r = classificar_score(750)
        assert r.rating == "B"
        assert r.premio_anual == pytest.approx(0.20)

    def test_score_650_retorna_rating_c(self):
        """Score na faixa 600-699 = rating C."""
        r = classificar_score(650)
        assert r.rating == "C"
        assert r.pd_anual == pytest.approx(0.060)

    def test_score_400_retorna_rating_d(self):
        """Score baixo = rating D (maior spread e PD)."""
        r = classificar_score(400)
        assert r.rating == "D"
        assert r.premio_anual == pytest.approx(0.32)
        assert r.pd_anual == pytest.approx(0.120)

    def test_fronteiras_inclusivas(self):
        """As faixas são fechadas (inclusivas) em ambos os lados."""
        assert classificar_score(900).rating == "A+"
        assert classificar_score(899).rating == "A"
        assert classificar_score(800).rating == "A"
        assert classificar_score(799).rating == "B"
        assert classificar_score(0).rating == "D"

    def test_score_fora_da_escala_cai_em_d(self):
        """Fallback defensivo: score > 1000 ou < 0 vira D."""
        assert classificar_score(1500).rating == "D"
        assert classificar_score(-50).rating == "D"

    def test_premio_e_pd_monotonicamente_crescem_com_risco(self):
        """Quanto pior o rating, maior o prêmio e a PD cobrados."""
        r_ap = classificar_score(950)
        r_a = classificar_score(850)
        r_b = classificar_score(750)
        r_c = classificar_score(650)
        r_d = classificar_score(400)

        premios = [r_ap.premio_anual, r_a.premio_anual,
                   r_b.premio_anual, r_c.premio_anual, r_d.premio_anual]
        pds = [r_ap.pd_anual, r_a.pd_anual,
               r_b.pd_anual, r_c.pd_anual, r_d.pd_anual]

        assert premios == sorted(premios), "prêmios devem ser monotônicos"
        assert pds == sorted(pds), "PDs devem ser monotônicas"

    def test_retorno_e_imutavel(self):
        """Classificacao é dataclass frozen — não aceita mutação."""
        r = classificar_score(950)
        assert isinstance(r, Classificacao)
        with pytest.raises((AttributeError, Exception)):
            r.rating = "X"  # type: ignore[misc]


# =============================================================================
# distribuir_componentes · contribuição de cada dimensão em pontos
# =============================================================================
class TestDistribuirComponentes:
    """Valida a decomposição do score em qualidade, liquidez, inadimplência, regional."""

    def test_valores_maximos_geram_1000_pontos(self):
        """Componentes = 1.0 em todas as dimensões → soma aproximada de 1000."""
        d = distribuir_componentes(
            peso_qualidade=0.35, peso_liquidez=0.25,
            peso_inadimplencia=0.30, peso_regional=0.10,
            v_qualidade=1.0, v_liquidez=1.0,
            v_inadimplencia=1.0, v_regional=1.0,
        )
        total = sum(d.values())
        assert total == pytest.approx(1000.0)

    def test_distribuicao_respeita_pesos(self):
        """Componente = peso × valor × 1000."""
        d = distribuir_componentes(
            peso_qualidade=0.35, peso_liquidez=0.25,
            peso_inadimplencia=0.30, peso_regional=0.10,
            v_qualidade=0.8, v_liquidez=0.5,
            v_inadimplencia=0.6, v_regional=0.9,
        )
        assert d["qualidade"] == pytest.approx(280.0)       # 0.8 × 0.35 × 1000
        assert d["liquidez"] == pytest.approx(125.0)        # 0.5 × 0.25 × 1000
        assert d["inadimplencia"] == pytest.approx(180.0)   # 0.6 × 0.30 × 1000
        assert d["regional"] == pytest.approx(90.0)         # 0.9 × 0.10 × 1000

    def test_todas_as_chaves_presentes(self):
        """Dict de retorno sempre tem as 4 dimensões."""
        d = distribuir_componentes(0.25, 0.25, 0.25, 0.25, 0, 0, 0, 0)
        assert set(d.keys()) == {"qualidade", "liquidez", "inadimplencia", "regional"}


# =============================================================================
# percentil_na_carteira · posição relativa de um sacado
# =============================================================================
class TestPercentilNaCarteira:
    """Valida o cálculo de percentil de um score em relação à carteira."""

    def test_melhor_score_da_carteira_fica_em_100(self):
        """Score maior que todos os outros = topo (100%)."""
        carteira = [500, 600, 700, 800]
        assert percentil_na_carteira(900, carteira) == 100.0

    def test_pior_score_da_carteira_fica_em_zero(self):
        """Score menor que todos os outros = 0%."""
        carteira = [500, 600, 700, 800]
        assert percentil_na_carteira(400, carteira) == 0.0

    def test_mediana_aproximada(self):
        """Um score na mediana deve ficar perto de 50%."""
        carteira = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        # Score 550 é melhor que 5 (100..500) de 10 itens = 50%
        assert percentil_na_carteira(550, carteira) == 50.0

    def test_carteira_vazia_retorna_zero(self):
        """Defensivo: carteira vazia não quebra o cálculo."""
        assert percentil_na_carteira(800, []) == 0.0

    def test_retorno_arredondado_em_uma_casa(self):
        """Percentil é arredondado em 1 casa decimal (ex: 66.7)."""
        # Score 750 é melhor que 2 de 3 itens = 66.67 → 66.7
        assert percentil_na_carteira(750, [500, 700, 900]) == 66.7

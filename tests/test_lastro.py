"""Testes unitários · domain.lastro (ICL — Índice de Confiança do Lastro)

Valida a detecção de:
  1. Ausência de histórico (primeira operação) → AMARELO
  2. Padrão saudável (recorrência + valor normal) → VERDE
  3. Outlier severo (Z-score > 3) → VERMELHO
  4. Normalização de histórico com nomes de colunas variados

Os valores nominais são escolhidos para acionar os componentes previsíveis
do ICL sem depender de comportamento estocástico.
"""

from __future__ import annotations

import pandas as pd
import pytest

from domain.lastro import (
    ResultadoLastro,
    SeloLastro,
    normalizar_historico,
    validar_lastro,
)


# =============================================================================
# validar_lastro · cenários base
# =============================================================================
class TestValidarLastroCenariosBase:

    def test_historico_vazio_retorna_amarelo_primeira_operacao(self):
        """Sem histórico Cedente × Sacado → selo AMARELO."""
        df = pd.DataFrame()
        r = validar_lastro(df, valor_proposto=50_000, prazo_proposto=30)

        assert r.selo == SeloLastro.AMARELO
        assert r.icl == 25.0
        assert "Primeira operação" in r.motivos[0]

    def test_historico_saudavel_consistente_retorna_verde(self):
        """Valor dentro da média + recorrência → selo VERDE."""
        # 12 operações mensais com valor estável
        df = pd.DataFrame({
            "valor_nominal": [50_000] * 12,
            "data_emissao": pd.date_range("2024-01-01", periods=12, freq="30D"),
            "prazo_du": [30] * 12,
        })
        r = validar_lastro(df, valor_proposto=51_000, prazo_proposto=30)

        assert r.selo == SeloLastro.VERDE
        assert r.icl > 50
        assert abs(r.z_score_valor) < 2.0

    def test_outlier_severo_de_valor_retorna_vermelho(self):
        """Valor muito acima da média histórica → selo VERMELHO."""
        df = pd.DataFrame({
            "valor_nominal": [50_000, 48_000, 52_000, 51_000, 49_500, 50_500],
            "data_emissao": pd.date_range("2024-01-01", periods=6, freq="30D"),
            "prazo_du": [30] * 6,
        })
        # Valor 10× a média — Z-score astronomicamente alto
        r = validar_lastro(df, valor_proposto=500_000, prazo_proposto=30)

        assert r.selo == SeloLastro.VERMELHO
        assert abs(r.z_score_valor) > 3.0
        assert any("outlier" in m.lower() or "σ" in m for m in r.motivos)

    def test_retorno_e_dataclass_frozen(self):
        """ResultadoLastro é imutável."""
        r = validar_lastro(pd.DataFrame(), valor_proposto=10_000, prazo_proposto=30)
        assert isinstance(r, ResultadoLastro)
        with pytest.raises((AttributeError, Exception)):
            r.icl = 99.0  # type: ignore[misc]


# =============================================================================
# Componentes do ICL · validação estrutural
# =============================================================================
class TestComponentesICL:

    def test_componentes_sao_quatro_dimensoes(self):
        """ICL decomposto em volume, recorrencia, frequencia, prazo."""
        df = pd.DataFrame({
            "valor_nominal": [50_000] * 6,
            "data_emissao": pd.date_range("2024-01-01", periods=6, freq="30D"),
            "prazo_du": [30] * 6,
        })
        r = validar_lastro(df, valor_proposto=50_000, prazo_proposto=30)
        assert set(r.componentes.keys()) == {
            "volume", "recorrencia", "frequencia", "prazo"
        }

    def test_componentes_sao_entre_0_e_100(self):
        """Cada componente é limitado em [0, 100]."""
        df = pd.DataFrame({
            "valor_nominal": [50_000] * 8,
            "data_emissao": pd.date_range("2024-01-01", periods=8, freq="30D"),
            "prazo_du": [30] * 8,
        })
        r = validar_lastro(df, valor_proposto=75_000, prazo_proposto=30)
        for nome, valor in r.componentes.items():
            assert 0.0 <= valor <= 100.0, f"{nome}={valor} fora de [0,100]"

    def test_icl_e_entre_0_e_100(self):
        """ICL final é limitado em [0, 100]."""
        df = pd.DataFrame({
            "valor_nominal": [50_000] * 6,
            "data_emissao": pd.date_range("2024-01-01", periods=6, freq="30D"),
            "prazo_du": [30] * 6,
        })
        r = validar_lastro(df, valor_proposto=999_999, prazo_proposto=30)
        assert 0.0 <= r.icl <= 100.0


# =============================================================================
# Hash de integridade · auditoria
# =============================================================================
class TestHashIntegridade:

    def test_gera_hash_sha256(self):
        """Cada resultado traz um hash de integridade (64 chars hex)."""
        r = validar_lastro(pd.DataFrame(), valor_proposto=10_000, prazo_proposto=30)
        assert r.hash_integridade
        assert len(r.hash_integridade) == 64
        assert all(c in "0123456789abcdef" for c in r.hash_integridade)

    def test_hash_muda_se_entrada_muda(self):
        """Entradas diferentes → hashes diferentes."""
        r1 = validar_lastro(pd.DataFrame(), valor_proposto=10_000, prazo_proposto=30)
        r2 = validar_lastro(pd.DataFrame(), valor_proposto=99_999, prazo_proposto=30)
        assert r1.hash_integridade != r2.hash_integridade


# =============================================================================
# Normalização de histórico · aceita nomes de colunas variados
# =============================================================================
class TestNormalizarHistorico:

    def test_aceita_nomes_alternativos_de_valor(self):
        """'valor' e 'vlr_nominal' também funcionam."""
        df1 = pd.DataFrame({
            "valor": [100, 200],
            "data_emissao": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        })
        out1 = normalizar_historico(df1)
        assert "valor" in out1.columns
        assert len(out1) == 2

    def test_aceita_data_emissao_ou_data(self):
        """'data' também é aceito como alias de 'data_emissao'."""
        df = pd.DataFrame({
            "valor_nominal": [100, 200],
            "data": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        })
        out = normalizar_historico(df)
        assert "data" in out.columns

    def test_df_vazio_nao_quebra(self):
        """DataFrame vazio volta vazio sem erro."""
        out = normalizar_historico(pd.DataFrame())
        assert len(out) == 0

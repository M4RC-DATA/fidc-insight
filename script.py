# =============================================================================
# SCRIPT DE ANÁLISE — FIDC Score Insight
# Para uso do gestor/cliente na análise de direitos creditórios
#
# O que este script faz:
#   1. Busca os dados tratados do CNPJ no BigQuery (resultado do ETL)
#   2. Recalcula o score com detalhamento de cada componente
#   3. Calcula o Valor Presente da operação
#   4. Compara o CNPJ com a carteira toda
#   5. Mostra visão geral da carteira e risco de concentração
#   6. Documenta o resultado no histórico
# =============================================================================
import pandas as pd
import numpy as np
import json
import requests
from datetime import datetime, date
import sys

# =============================================================================
# 1. CONFIGURAÇÕES
# =============================================================================
PROJECT_ID         = 'dataversenuclea'
BQ_DATASET         = 'fidc_dataset'
BQ_TABLE           = 'tb_score_consolidado'       # dados tratados pelo ETL
BQ_TABLE_HISTORICO = 'tb_historico_precificacoes'  # histórico de consultas

# Parâmetros da operação que o gestor quer analisar
CNPJ_BUSCA    = "c137becbf8aeb57d1cb29eafa0506837ae986c18e10ba4ea5c0b83a88f2f3926"
VALOR_INPUT   = 250000.00
DT_VENCIMENTO = "2027-03-24"

# Parâmetros do modelo de score — mesmos pesos do ETL
PESOS = {
    'qualidade'     : 0.35,
    'liquidez'      : 0.25,
    'inadimplencia' : 0.30,
    'regional'      : 0.10,
}
FATOR_REGIONAL = {
    'RO':1.30,'PR':1.25,'MT':1.22,'RS':1.20,'SC':1.20,'SP':1.15,'DF':1.15,
    'PI':1.12,'SE':1.10,'GO':1.10,'BA':1.10,'PE':1.08,'CE':1.08,'RN':1.08,
    'MA':1.12,'PA':1.15,'AM':1.18,'AL':1.10,'PB':1.10,'ES':1.05,'MG':1.05,
    'RJ':1.08,'MS':1.08,'TO':1.12,'AP':1.20,'RR':1.22,'AC':1.20,
}
FATOR_REGIONAL_DEFAULT = 1.10
CLASSIFICACOES = [
    (900, 1000, 'A+', 0.15),
    (800,  899, 'A',  0.17),
    (700,  799, 'B',  0.20),
    (600,  699, 'C',  0.25),
    (  0,  599, 'D',  0.32),
]

# Limiares de alerta de concentração
ALERTA_CONCENTRACAO_UF   = 0.30   # UF com mais de 30% do valor total
ALERTA_CONCENTRACAO_CNAE = 0.20   # CNAE com mais de 20% do valor total


# =============================================================================
# FUNÇÕES DE SUPORTE
# =============================================================================
def classificar_score(score):
    """Retorna (classificação, taxa_prêmio) para um score numérico."""
    for vmin, vmax, cls, taxa in CLASSIFICACOES:
        if vmin <= score <= vmax:
            return cls, taxa
    return 'D', 0.32


def buscar_selic():
    """Consulta a Meta Selic atual na API do Banco Central."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        resposta = requests.get(url, timeout=10)
        resposta.raise_for_status()
        valor = float(resposta.json()[0]['valor'])
        return valor / 100
    except Exception:
        return 0.1375  # fallback se a API estiver fora do ar


def separador(titulo):
    print(f"\n── {titulo} {'─' * (68 - len(titulo))}")


# =============================================================================
# 2. BUSCA OS DADOS TRATADOS DO CNPJ NO BIGQUERY
# =============================================================================
separador("BUSCANDO DADOS")
print(f"  CNPJ : {CNPJ_BUSCA[:20]}...")

query = f"""
    SELECT * FROM `{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}`
    WHERE id_cnpj = '{CNPJ_BUSCA}'
"""
try:
    df_cnpj = pd.read_gbq(query, project_id=PROJECT_ID)
except Exception as e:
    print(f"  Erro ao conectar no BigQuery: {e}")
    sys.exit(1)

if df_cnpj.empty:
    print("  CNPJ não encontrado na base. Verifique se o ETL já processou este registro.")
    sys.exit(1)

# Também carrega a carteira inteira para normalizar os componentes do score
# (a normalização do componente regional depende dos valores de toda a base)
query_carteira_completa = f"""
    SELECT * FROM `{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}`
"""
try:
    df_carteira = pd.read_gbq(query_carteira_completa, project_id=PROJECT_ID)
except Exception as e:
    print(f"  Erro ao carregar carteira: {e}")
    sys.exit(1)

print(f"  ✅ Dados carregados — {len(df_carteira)} devedores na carteira")


# =============================================================================
# 3. RECALCULO DO SCORE COM DETALHAMENTO DOS COMPONENTES
# =============================================================================
separador("SCORE DO DEVEDOR")

# Garante que as colunas numéricas estão no tipo certo
cols_num = [
    'sacado_indice_liquidez_1m', 'score_quantidade_v2', 'score_materialidade_v2',
    'media_atraso_dias', 'indicador_liquidez_quantitativo_3m', 'share_vl_inad_pag_bol_6_a_15d'
]
for col in cols_num:
    if col in df_carteira.columns:
        df_carteira[col] = pd.to_numeric(df_carteira[col], errors='coerce')
        df_carteira[col] = df_carteira[col].fillna(df_carteira[col].median())

row = df_carteira[df_carteira['id_cnpj'] == CNPJ_BUSCA].iloc[0]

# ── Componente 1: Qualidade Creditícia (35%) ─────────────────────────────────
# Média ponderada dos dois scores de comportamento de pagamento
comp_qualidade = (
    (row['score_quantidade_v2']    / 1000) * 0.5 +
    (row['score_materialidade_v2'] / 1000) * 0.5
)

# ── Componente 2: Liquidez (25%) ──────────────────────────────────────────────
# Combina liquidez de curto prazo (1 mês) e médio prazo (3 meses)
comp_liquidez = (
    row['sacado_indice_liquidez_1m']          * 0.6 +
    row['indicador_liquidez_quantitativo_3m'] * 0.4
)

# ── Componente 3: Inadimplência Histórica (30%) ───────────────────────────────
# Inverte as métricas: mais atraso = componente menor
max_atraso        = df_carteira['media_atraso_dias'].max()
atraso_inv        = 1 - (row['media_atraso_dias'] / (max_atraso + 1e-9))
inad_inv          = 1 - row['share_vl_inad_pag_bol_6_a_15d']
comp_inadimplencia = atraso_inv * 0.6 + inad_inv * 0.4

# ── Componente 4: Risco Regional (10%) ────────────────────────────────────────
# Estados com maior risco recebem componente menor
_fi_carteira = 1.0 / df_carteira['uf'].map(FATOR_REGIONAL).fillna(FATOR_REGIONAL_DEFAULT)
fi_min, fi_max = _fi_carteira.min(), _fi_carteira.max()
fi_cnpj        = 1.0 / FATOR_REGIONAL.get(str(row['uf']), FATOR_REGIONAL_DEFAULT)
comp_regional  = (fi_cnpj - fi_min) / (fi_max - fi_min + 1e-9)

# ── Score Final ───────────────────────────────────────────────────────────────
score_fidc = (
    comp_qualidade     * PESOS['qualidade']     +
    comp_liquidez      * PESOS['liquidez']      +
    comp_inadimplencia * PESOS['inadimplencia'] +
    comp_regional      * PESOS['regional']
) * 1000
score_fidc = round(min(max(score_fidc, 0), 1000), 2)

classificacao, taxa_premio = classificar_score(score_fidc)

# Exibe o score e cada componente de forma clara para o gestor
print(f"\n  Score FIDC        : {score_fidc:.2f} / 1000")
print(f"  Classificação     : {classificacao}")
print(f"  UF do devedor     : {row['uf']}")

print(f"\n  Detalhamento dos componentes:")
print(f"  {'Componente':<35} {'Peso':>6}   {'Valor (0–1)':>12}   {'Contribuição':>12}")
print(f"  {'─'*35} {'─'*6}   {'─'*12}   {'─'*12}")
print(f"  {'Qualidade Creditícia':<35} {'35%':>6}   {comp_qualidade:>12.4f}   {comp_qualidade * PESOS['qualidade'] * 1000:>11.2f}p")
print(f"  {'Liquidez':<35} {'25%':>6}   {comp_liquidez:>12.4f}   {comp_liquidez * PESOS['liquidez'] * 1000:>11.2f}p")
print(f"  {'Inadimplência Histórica':<35} {'30%':>6}   {comp_inadimplencia:>12.4f}   {comp_inadimplencia * PESOS['inadimplencia'] * 1000:>11.2f}p")
print(f"  {'Risco Regional':<35} {'10%':>6}   {comp_regional:>12.4f}   {comp_regional * PESOS['regional'] * 1000:>11.2f}p")
print(f"  {'─'*35} {'─'*6}   {'─'*12}   {'─'*12}")
print(f"  {'TOTAL':<35} {'100%':>6}   {'':>12}   {score_fidc:>11.2f}p")

# Variáveis brutas usadas no cálculo — para o gestor entender a origem
print(f"\n  Variáveis brutas do devedor:")
print(f"    Score quantidade (v2)     : {row['score_quantidade_v2']:.2f}")
print(f"    Score materialidade (v2)  : {row['score_materialidade_v2']:.2f}")
print(f"    Liquidez 1m               : {row['sacado_indice_liquidez_1m']:.4f}")
print(f"    Liquidez 3m               : {row['indicador_liquidez_quantitativo_3m']:.4f}")
print(f"    Média de atraso (dias)    : {row['media_atraso_dias']:.1f}")
print(f"    Share inadimplência 6-15d : {row['share_vl_inad_pag_bol_6_a_15d']:.4f}")


# =============================================================================
# 4. VALOR PRESENTE DA OPERAÇÃO
# =============================================================================
separador("PRECIFICAÇÃO — VALOR PRESENTE")

taxa_selic     = buscar_selic()
taxa_total     = round(taxa_selic + taxa_premio, 4)

hoje               = date.today()
vencimento         = datetime.strptime(DT_VENCIMENTO, "%Y-%m-%d").date()
prazo_base_dias    = max((vencimento - hoje).days, 1)
atraso_historico   = round(float(row['media_atraso_real']) if 'media_atraso_real' in row and pd.notna(row['media_atraso_real']) else 0.0, 1)
prazo_ajustado_dias = prazo_base_dias + atraso_historico
prazo_anos          = prazo_ajustado_dias / 365

# VP = Valor Nominal / (1 + taxa_anual) ^ prazo
vp_sugerido = round(VALOR_INPUT / (1 + taxa_total) ** prazo_anos, 2)
margem      = round((VALOR_INPUT - vp_sugerido) / VALOR_INPUT * 100, 2)

print(f"\n  Valor informado          : R$ {VALOR_INPUT:>12,.2f}")
print(f"  Vencimento               : {DT_VENCIMENTO}")
print(f"  Prazo base               : {prazo_base_dias} dias")
print(f"  Atraso histórico médio   : {atraso_historico} dias")
print(f"  Prazo ajustado           : {prazo_ajustado_dias:.1f} dias ({prazo_anos:.4f} anos)")
print(f"\n  Selic atual (Bacen)      : {taxa_selic*100:.2f}%")
print(f"  Prêmio de risco ({classificacao})    : {taxa_premio*100:.2f}%")
print(f"  Taxa total anual         : {taxa_total*100:.2f}%")
print(f"\n  VP Sugerido              : R$ {vp_sugerido:>12,.2f}")
print(f"  Margem de segurança      : {margem:.2f}%")
print(f"  Desconto aplicado        : R$ {VALOR_INPUT - vp_sugerido:>12,.2f}")


# =============================================================================
# 5. COMPARAÇÃO DO CNPJ COM A CARTEIRA
# =============================================================================
separador("COMPARAÇÃO COM A CARTEIRA")

# Recalcula score para toda a carteira para posicionar o CNPJ
scores_carteira = df_carteira['score_fidc'] if 'score_fidc' in df_carteira.columns else pd.Series([score_fidc])
total_carteira  = len(scores_carteira)

devedores_abaixo = (scores_carteira < score_fidc).sum()
percentil        = round(devedores_abaixo / total_carteira * 100, 1)

score_medio  = round(scores_carteira.mean(), 2)
score_min    = round(scores_carteira.min(), 2)
score_max    = round(scores_carteira.max(), 2)

if score_fidc > score_medio:
    posicao_relativa = f"ACIMA da média da carteira (+{score_fidc - score_medio:.2f} pontos)"
else:
    posicao_relativa = f"ABAIXO da média da carteira ({score_fidc - score_medio:.2f} pontos)"

print(f"\n  Score deste devedor      : {score_fidc:.2f}  ({classificacao})")
print(f"  Score médio da carteira  : {score_medio:.2f}")
print(f"  Score mínimo             : {score_min:.2f}")
print(f"  Score máximo             : {score_max:.2f}")
print(f"\n  Posição relativa         : {posicao_relativa}")
print(f"  Percentil na carteira    : melhor que {percentil}% dos devedores")

# Distribuição de classificações na carteira
dist = df_carteira['classificacao_risco'].value_counts() if 'classificacao_risco' in df_carteira.columns else pd.Series()
print(f"\n  Distribuição de risco na carteira:")
for cls in ['A+', 'A', 'B', 'C', 'D']:
    qtd = int(dist.get(cls, 0))
    pct = qtd / total_carteira * 100
    barra = '█' * int(pct / 2)
    destaque = " ◄ este devedor" if cls == classificacao else ""
    print(f"    {cls:<4} {barra:<25} {qtd:>4} devedores ({pct:.1f}%){destaque}")


# =============================================================================
# 6. VISÃO GERAL DA CARTEIRA
# =============================================================================
separador("VISÃO GERAL DA CARTEIRA")

valor_total_carteira = df_carteira['vlr_nominal_total'].sum() if 'vlr_nominal_total' in df_carteira.columns else 0
liq_media    = df_carteira['taxa_liquidacao'].mean()    if 'taxa_liquidacao'    in df_carteira.columns else 0
inad_media   = df_carteira['taxa_inadimplencia'].mean() if 'taxa_inadimplencia' in df_carteira.columns else 0
atraso_medio = df_carteira['media_atraso_real'].mean()  if 'media_atraso_real'  in df_carteira.columns else 0

print(f"\n  Total de devedores       : {total_carteira}")
print(f"  Valor total da carteira  : R$ {valor_total_carteira:,.2f}")
print(f"  Score médio              : {score_medio:.2f}")
print(f"  Taxa de liquidação média : {liq_media*100:.1f}%")
print(f"  Taxa de inadimplência    : {inad_media*100:.1f}%")
print(f"  Atraso médio             : {atraso_medio:.1f} dias")


# =============================================================================
# 7. RISCO DE CONCENTRAÇÃO
# =============================================================================
separador("RISCO DE CONCENTRAÇÃO")

if 'vlr_nominal_total' in df_carteira.columns and valor_total_carteira > 0:

    # ── Por UF ────────────────────────────────────────────────────────────────
    conc_uf = (
        df_carteira.groupby('uf')['vlr_nominal_total']
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    conc_uf['share'] = conc_uf['vlr_nominal_total'] / valor_total_carteira

    print(f"\n  Concentração por UF:")
    print(f"  {'UF':<6} {'Valor Exposto':>16}   {'% Carteira':>10}   {'Alerta'}")
    print(f"  {'─'*6} {'─'*16}   {'─'*10}   {'─'*8}")
    for _, u in conc_uf.head(8).iterrows():
        alerta = "⚠️  ALTO" if u['share'] > ALERTA_CONCENTRACAO_UF else ""
        print(f"  {u['uf']:<6} R$ {u['vlr_nominal_total']:>12,.2f}   {u['share']*100:>9.1f}%   {alerta}")

    # ── Por CNAE ──────────────────────────────────────────────────────────────
    if 'cd_cnae_prin' in df_carteira.columns:
        conc_cnae = (
            df_carteira.groupby('cd_cnae_prin')['vlr_nominal_total']
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        conc_cnae['share'] = conc_cnae['vlr_nominal_total'] / valor_total_carteira

        print(f"\n  Concentração por CNAE (setor):")
        print(f"  {'CNAE':<10} {'Valor Exposto':>16}   {'% Carteira':>10}   {'Alerta'}")
        print(f"  {'─'*10} {'─'*16}   {'─'*10}   {'─'*8}")
        for _, cn in conc_cnae.head(8).iterrows():
            alerta = "⚠️  ALTO" if cn['share'] > ALERTA_CONCENTRACAO_CNAE else ""
            print(f"  {str(cn['cd_cnae_prin']):<10} R$ {cn['vlr_nominal_total']:>12,.2f}   {cn['share']*100:>9.1f}%   {alerta}")

    # ── Índice HHI ────────────────────────────────────────────────────────────
    # Mede a concentração geral: 0 = diversificada | 1 = tudo em um lugar só
    hhi = round((conc_uf['share'] ** 2).sum(), 4)
    if hhi < 0.15:
        nivel_hhi = "DIVERSIFICADA ✅"
    elif hhi < 0.25:
        nivel_hhi = "MODERADAMENTE CONCENTRADA ⚠️"
    else:
        nivel_hhi = "CONCENTRADA 🚨"

    print(f"\n  Índice HHI por UF : {hhi:.4f} — {nivel_hhi}")
    print(f"  (referência: < 0.15 diversificada | 0.15–0.25 moderada | > 0.25 concentrada)")


# =============================================================================
# 8. TENDÊNCIA DE SCORE (HISTÓRICO DE CONSULTAS)
# =============================================================================
separador("TENDÊNCIA DE SCORE — HISTÓRICO")

try:
    query_hist = f"""
        SELECT data_consulta, score_fidc, classificacao_risco, vp_sugerido
        FROM `{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_HISTORICO}`
        WHERE id_cnpj = '{CNPJ_BUSCA}'
        ORDER BY data_consulta ASC
    """
    df_hist = pd.read_gbq(query_hist, project_id=PROJECT_ID)

    if df_hist.empty:
        print("\n  Nenhuma consulta anterior — este será o primeiro registro no histórico.")
    else:
        print(f"\n  {'Data':<22} {'Score':>8}   {'Classe':<6}   {'VP Sugerido':>14}")
        print(f"  {'─'*22} {'─'*8}   {'─'*6}   {'─'*14}")
        for _, h in df_hist.iterrows():
            print(f"  {str(h['data_consulta']):<22} {h['score_fidc']:>8.2f}   {h['classificacao_risco']:<6}   R$ {h['vp_sugerido']:>10,.2f}")

        variacao = df_hist.iloc[-1]['score_fidc'] - df_hist.iloc[0]['score_fidc']
        if variacao > 0:
            tendencia = f"↑ MELHORANDO (+{variacao:.2f} pontos)"
        elif variacao < 0:
            tendencia = f"↓ PIORANDO ({variacao:.2f} pontos)"
        else:
            tendencia = "→ ESTÁVEL"

        print(f"\n  Tendência geral  : {tendencia}")
        print(f"  Mínimo histórico : {df_hist['score_fidc'].min():.2f}")
        print(f"  Máximo histórico : {df_hist['score_fidc'].max():.2f}")
        print(f"  Médio histórico  : {df_hist['score_fidc'].mean():.2f}")

except Exception as e:
    print(f"\n  Não foi possível carregar o histórico: {e}")


# =============================================================================
# 9. DOCUMENTA O RESULTADO NO BIGQUERY
# =============================================================================
separador("DOCUMENTANDO RESULTADO")

df_registro = pd.DataFrame([{
    "data_consulta"       : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "id_cnpj"             : CNPJ_BUSCA,
    "uf"                  : str(row['uf']),
    "score_fidc"          : score_fidc,
    "classificacao_risco" : classificacao,
    "comp_qualidade"      : round(comp_qualidade, 4),
    "comp_liquidez"       : round(comp_liquidez, 4),
    "comp_inadimplencia"  : round(comp_inadimplencia, 4),
    "comp_regional"       : round(comp_regional, 4),
    "valor_informado"     : VALOR_INPUT,
    "dt_vencimento"       : DT_VENCIMENTO,
    "prazo_ajustado_dias" : round(prazo_ajustado_dias, 1),
    "selic_utilizada"     : taxa_selic,
    "taxa_premio_risco"   : taxa_premio,
    "taxa_total_anual"    : taxa_total,
    "vp_sugerido"         : vp_sugerido,
    "margem_seguranca_pct": margem,
}])

try:
    df_registro.to_gbq(
        destination_table=f"{BQ_DATASET}.{BQ_TABLE_HISTORICO}",
        project_id=PROJECT_ID,
        if_exists="append",
    )
    print(f"\n  ✅ Resultado salvo em {BQ_DATASET}.{BQ_TABLE_HISTORICO}")
except Exception as e:
    print(f"\n  ⚠️  Erro ao salvar no BigQuery: {e}")


# =============================================================================
# 10. RESUMO FINAL
# =============================================================================
separador("RESUMO FINAL DA OPERAÇÃO")
print(f"""
  CNPJ (hash)    : {CNPJ_BUSCA[:20]}...
  UF             : {row['uf']}
  Score FIDC     : {score_fidc:.2f} / 1000  →  Classificação {classificacao}
  Percentil      : melhor que {percentil}% da carteira

  Valor          : R$ {VALOR_INPUT:,.2f}
  VP Sugerido    : R$ {vp_sugerido:,.2f}
  Margem         : {margem:.2f}%
  Taxa Total     : {taxa_total*100:.2f}% a.a.  (Selic {taxa_selic*100:.2f}% + Prêmio {taxa_premio*100:.2f}%)
""")
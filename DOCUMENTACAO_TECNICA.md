# Documentação Técnica — FIDC Insight

> Data Verse · Grupo de Data Science — FIAP · TCC 2026

---

## 1. Arquitetura

O projeto segue uma arquitetura em 5 camadas com separação clara de responsabilidades:

```
app.py                    ← Entry point · autenticação · roteamento
  │
  ├── ui/                 ← Interface (Streamlit + CSS)
  │   ├── views/          ← Telas da aplicação
  │   ├── components.py   ← Blocos reutilizáveis (KPIs, callouts, logo)
  │   ├── charts.py       ← Gráficos Plotly com keys únicas
  │   └── styles.py       ← CSS global · identidade Data Verse
  │
  ├── domain/             ← Regras de negócio puras (sem Streamlit, sem BQ)
  │   ├── scoring.py      ← Motor de score 0-1000
  │   ├── pricing.py      ← VP · ECL · RAROC
  │   ├── risk.py         ← HHI · EWS · concentração
  │   └── lastro.py       ← ICL anti-fraude
  │
  ├── services/           ← Acesso a dados e integrações
  │   ├── database.py     ← BigQuery (local + Streamlit Cloud)
  │   ├── auth.py         ← Login · bcrypt · sessão
  │   ├── bcb_api.py      ← Selic via API BCB
  │   └── audit.py        ← Trilha de acessos
  │
  └── infraestrutura
      ├── BigQuery (GCP)  ← tb_score_consolidado
      ├── SQLite local    ← auth.db (usuários)
      └── Airflow DAG     ← ETL boletos → score
```

### Decisões de arquitetura

**Uma fonte da verdade entre app e ETL**
O DAG Airflow importa `PESOS`, `FATOR_REGIONAL` e `ATRASO_CAP_DIAS`
diretamente de `config/business_rules.py`. Qualquer mudança nas regras
afeta os dois lados simultaneamente.

**Credentials agnósticas ao ambiente**
`services/database.py` detecta automaticamente:
- Streamlit Cloud → lê de `st.secrets["gcp_service_account"]`
- Local → usa `GOOGLE_APPLICATION_CREDENTIALS`

**Navegação sem sidebar**
O app esconde a sidebar via CSS e roteia via `session_state["pagina"]`.
Cada tela é autocontida — sem dependência de estado de sidebar.

**Gráficos com key única**
Todos os `st.plotly_chart()` têm `key=` explícito para evitar
`StreamlitDuplicateElementId` quando o mesmo gráfico aparece em múltiplas abas.

---

## 2. Motor de Score

### Fórmula

```
score = (v_qualidade×0,35 + v_liquidez×0,25 + v_inadimplencia×0,30 + v_regional×0,10) × 1000
```

Todos os componentes `v_*` são clipados em `[0, 1]` antes da soma.

### Componentes

**Qualidade (35%)**
```
v_qualidade = (score_quantidade_v2/1000 + score_materialidade_v2/1000) / 2
```

**Liquidez (25%)**
```
v_liquidez = clip(sacado_indice_liquidez_1m × 0,6 + indicador_liquidez_3m × 0,4, 0, 1)
```

**Inadimplência (30%)**
```
v_atraso_inv = max(0, 1 - media_atraso_dias / 247)
v_inad       = max(0, 1 - share_vl_inad_pag_bol_6_a_15d)
v_inadimplencia = (v_atraso_inv + v_inad) / 2
```

`ATRASO_CAP_DIAS = 247` dias = p90 da distribuição real (mediana = 178 dias).
Um teto de 60 dias zeraria 91% da carteira — tornando o componente inútil.

**Regional (10%)**
Fator multiplicativo por UF calibrado nos dados históricos.
Bounds fixos do dicionário `FATOR_REGIONAL` — não variam entre execuções.

### Imputação de nulos

Moda por UF → preserva padrões regionais.
Fallback: mediana global para UFs sem observações suficientes.

---

## 3. Precificação RAROC / IFRS 9

```
prazo_total = (data_vencimento - hoje) + round(atraso_historico_do_sacado)
taxa_total  = Selic + premio_do_rating
prazo_anos  = prazo_total / 365

VP   = Face / (1 + taxa_total)^prazo_anos
ECL  = Face × PD_anual × prazo_anos × LGD
Lucro RAROC = (Face - VP) - ECL
Margem real = Lucro / Face × 100
```

**LGD = 50%** — benchmark Basel II para FIDCs sem garantia real.

**ECL simplificado (IFRS 9 Stage 1):** PD escalando linearmente com o tempo.
Para boletos de 30–360 dias a diferença para modelos de sobrevivência é < 0,5%.

### Escala de ratings

| Rating | Score | PD anual | Prêmio s/ Selic |
|---|---|---|---|
| A+ | 900–1000 | 0,5% | +1,5% a.a. |
| A | 800–899 | 1,5% | +1,7% a.a. |
| B | 700–799 | 3,0% | +2,0% a.a. |
| C | 600–699 | 6,0% | +2,5% a.a. |
| D | 0–599 | 12,0% | +3,2% a.a. |

---

## 4. Análise de Risco

### HHI Geográfico

```
HHI = Σ (participação_da_UF_no_PL)²
```

| HHI | Classificação |
|---|---|
| < 0,15 | Diversificado |
| 0,15–0,25 | Concentração moderada |
| > 0,25 | Concentração crítica |

Limites CVM parametrizados: máx 10% por sacado · máx 25% por UF.

### EWS — Early Warning System

Probabilidade de contágio em rede:

```
P = min( (atraso_medio/15)×0,4 + share_inadimplencia×0,6 , 1,0 )
```

| P | Nível |
|---|---|
| < 0,30 | Baixo |
| 0,30–0,60 | Moderado |
| > 0,60 | Alto |

### Lastro (ICL — Anti-fraude)

Compara a operação proposta com o histórico do sacado via z-score:
```
ICL = f(z_score_valor, z_score_prazo, recorrencia, aderencia_cnae)
```

| ICL | Selo |
|---|---|
| ≥ 70 | Verde — dentro do padrão |
| 40–69 | Amarelo — desvio, revisar |
| < 40 | Vermelho — anomalia |

---

## 5. Dados

### Identificadores

Os sacados são identificados por hashes SHA-256 de 64 chars hexadecimais.
Exibição: `id_curto()` mostra `c137becb…3926` (8 primeiros + 4 últimos).

A função `buscar_sacados_por_cnpjs()` em `database.py` normaliza:
- 64 chars hex → SHA-256, preserva intacto
- Apenas dígitos → CNPJ bruto, zero-pad para 14 chars

### Pipeline ETL (Airflow)

```
base_boletos_fiap.csv
base_auxiliar_fiap.csv
        ↓
   fidc_score_etl.py (DAG)
   - Join por id_pagador = id_cnpj
   - Imputação por UF
   - Normalização [0,1]
   - Cálculo do score composto
        ↓
   BigQuery: tb_score_consolidado
```

---

## 6. Segurança

**Autenticação:** bcrypt (custo 12) · SQLite local `data/auth.db`

**RBAC:**
| Papel | home | individual | carteira | Núclea | auditoria | admin |
|---|---|---|---|---|---|---|
| admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gestor | ✓ | ✓ | ✓ | ✓ | – | – |
| analista | ✓ | ✓ | – | ✓ | – | – |
| auditor | ✓ | – | – | ✓ | ✓ | – |

**Dossiê PDF:** payload assinado com SHA-256 para rastreabilidade.
Hash do payload: `sha256(cnpj + valor + vp + rating + timestamp)`.

**Secrets:** nunca subir `secrets.toml` ou `auth.db` para o GitHub
(ambos no `.gitignore`).

---

## 7. Identidade Visual — Data Verse

| Token | Valor | Uso |
|---|---|---|
| `DV_CYAN` | `#00BCD4` | Cor primária · ícones · foco de inputs |
| `DV_PURPLE` | `#7C3AED` | Cor secundária |
| Gradiente | `135deg, #00BCD4 → #7C3AED` | Botões primários · linha sidebar |
| `BG_APP` | `#F8FAFC` | Fundo do app |
| `INK` | `#0F172A` | Texto primário |
| `SLATE` | `#475569` | Texto secundário |
| Fonte | DM Sans (Google Fonts) | Todo o sistema |

Logo: V em SVG com traço ciano (lado esquerdo) e roxo (lado direito).

---

## 8. Deploy — Streamlit Cloud

Ver seção no `README.md`.

O `database.py` usa `_get_credentials()` que:
1. Tenta `st.secrets["gcp_service_account"]` (Streamlit Cloud)
2. Fallback: Application Default Credentials (local)

---

*Data Verse · Grupo de Data Science — FIAP · TCC 2026*
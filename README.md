# FIDC Insight · Data Verse

> TCC 2026 · Grupo de Data Science — FIAP  
> Parceria: **Núclea Dataverse**

Plataforma de análise de crédito para gestores de FIDC. Usa dados reais
da Núclea Dataverse para calcular score de risco, precificar recebíveis
com metodologia RAROC/IFRS 9 e emitir pareceres auditáveis com hash SHA-256.

---

## Telas

| Tela | O que responde |
|---|---|
| **Home** | O que você quer fazer? |
| **Consulta Individual** | Este sacado é um bom pagador? Qual o preço justo? |
| **Minha Carteira** | Como está o meu portfólio? (abas: Resumo · Valoração · Exportar · Benchmark) |
| **Auditoria** | Quem consultou o quê e quando? |
| **Administração** | Gerenciar usuários e papéis |

Navegação sem sidebar — tudo pela tela principal com `session_state["pagina"]`.

---

## Stack

```
Interface:   Python 3.13 · Streamlit · Plotly
Dados:       pandas · numpy · pandas-gbq
BigQuery:    google-cloud-bigquery · google-auth
ETL:         Apache Airflow (Docker)
Exportação:  fpdf2 (PDF + SHA-256) · openpyxl (Excel)
Auth:        bcrypt · SQLite local
```

---

## Estrutura

```
pf/
├── app.py                        ← Entry point · autenticação · roteamento
├── config/
│   ├── settings.py               ← BigQuery IDs · TTL de cache
│   ├── business_rules.py         ← Pesos score · ratings · ATRASO_CAP_DIAS=247 · LGD
│   ├── auth_rules.py             ← RBAC · permissões por papel
│   └── theme.py                  ← Paleta Data Verse · tipografia
├── domain/                       ← Regras de negócio puras (sem Streamlit/BQ)
│   ├── scoring.py                ← Score 0-1000 → rating A+ a D
│   ├── pricing.py                ← VP · ECL · lucro RAROC
│   ├── risk.py                   ← HHI geográfico · EWS · concentração CVM
│   └── lastro.py                 ← ICL · anti-fraude
├── services/
│   ├── database.py               ← BigQuery (local + Streamlit Cloud)
│   ├── auth.py                   ← Login · sessão · bcrypt
│   ├── bcb_api.py                ← Selic em tempo real
│   └── audit.py                  ← Trilha de acessos
├── exports/
│   ├── pdf_generator.py          ← Dossiê PDF + resumo carteira (SHA-256)
│   └── excel_generator.py
├── ui/
│   ├── styles.py                 ← CSS global · identidade Data Verse
│   ├── components.py             ← KPI cards · callouts · logo SVG
│   ├── charts.py                 ← Gráficos Plotly
│   └── views/
│       ├── home_view.py          ← Tela inicial · dois cards · extras por papel
│       ├── login_view.py         ← Login · identidade Data Verse
│       ├── individual_view.py    ← Consulta individual · abas: Saiba mais | Contexto Núclea
│       ├── carteira_upload_view.py ← Upload · abas: Resumo | Valoração | Exportar | Benchmark
│       ├── macro_view.py         ← Visão geral da carteira carregada
│       ├── carteira_view.py      ← Valoração RAROC consolidada
│       ├── nuclea_base_view.py   ← Benchmark carteira vs base Núclea
│       ├── audit_view.py
│       └── admin_users_view.py
├── dags/fidc_score_etl.py        ← Airflow ETL · boletos + auxiliar → BigQuery
├── .streamlit/
│   └── secrets.toml.example      ← Template de credenciais GCP para Streamlit Cloud
├── seed_users.py                 ← Cria usuários iniciais
└── requirements.txt
```

---

## Como rodar localmente

```bash
# 1. Criar e ativar venv
python3 -m venv venv
source venv/bin/activate          # Mac/Linux
.\venv\Scripts\Activate.ps1       # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Autenticar no BigQuery
gcloud auth application-default login
gcloud config set project dataversenuclea
gcloud auth application-default set-quota-project dataversenuclea

# 4. Criar usuários
python seed_users.py

# 5. Rodar
streamlit run app.py
```

Acessa em **http://localhost:8501**

### Credenciais padrão

| Usuário | Senha | Papel |
|---|---|---|
| `admin` | `Admin@2025` | Acesso total |
| `gestor` | `Gestor@2025` | Consultas + carteira |
| `analista` | `Analista@2025` | Só consulta individual |
| `auditor` | `Auditor@2025` | Só auditoria |

---

## Deploy

Ver `COMO_RODAR.md` para instruções completas de deploy local e no Streamlit Cloud.

O `database.py` detecta automaticamente o ambiente (local vs Streamlit Cloud).

---

## Metodologia

### Score Núclea (0–1.000)

```
score = (qualidade×0,35 + liquidez×0,25 + inadimplência×0,30 + regional×0,10) × 1000
```

Teto de atraso `ATRASO_CAP_DIAS = 247` dias (p90 da base real).
Um teto de 60 dias zeraria 91% da carteira.

### Rating e Precificação RAROC

| Rating | Score | PD anual | Prêmio |
|---|---|---|---|
| A+ | 900–1000 | 0,5% | +1,5% a.a. |
| A | 800–899 | 1,5% | +1,7% a.a. |
| B | 700–799 | 3,0% | +2,0% a.a. |
| C | 600–699 | 6,0% | +2,5% a.a. |
| D | 0–599 | 12,0% | +3,2% a.a. |

```
VP   = Face / (1 + Selic + prêmio)^(prazo_anos)
ECL  = Face × PD × prazo_anos × LGD(50%)   ← IFRS 9 lifetime
Lucro = (Face − VP) − ECL
```

### Controle de acesso (RBAC)

| Papel | home | individual | carteira | Núclea | auditoria | admin |
|---|---|---|---|---|---|---|
| admin    | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| gestor   | ✓ | ✓ | ✓ | ✓ | – | – |
| analista | ✓ | ✓ | – | ✓ | – | – |
| auditor  | ✓ | – | – | ✓ | ✓ | – |


### Identificadores

Sacados identificados por hashes SHA-256 de 64 chars. Exibidos como `c137becb…3926` via `id_curto()`.

---

*Data Verse · Grupo de Data Science — FIAP · TCC 2026*
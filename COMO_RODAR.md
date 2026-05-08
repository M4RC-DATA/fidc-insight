# Como rodar o FIDC Insight

---

## Pré-requisitos

- Python 3.10+
- Google Cloud CLI (para autenticação BigQuery local)
- Credenciais GCP com roles: `BigQuery Data Viewer` + `BigQuery Job User`

---

## Execução local

```bash
# 1. Clonar / descompactar o projeto e entrar na pasta
cd pf

# 2. Criar e ativar ambiente virtual
python3 -m venv venv
source venv/bin/activate          # Mac/Linux
.\venv\Scripts\Activate.ps1       # Windows PowerShell

# Se o PowerShell bloquear scripts:
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Autenticar no BigQuery
gcloud auth application-default login
gcloud config set project dataversenuclea
gcloud auth application-default set-quota-project dataversenuclea

# 5. Criar usuários do sistema
python seed_users.py

# 6. Rodar
streamlit run app.py
# Acessa em http://localhost:8501
```

### Próximas vezes

```bash
source venv/bin/activate && streamlit run app.py   # Mac/Linux
.\venv\Scripts\Activate.ps1; streamlit run app.py  # Windows
```

---

## Credenciais padrão

| Usuário | Senha | Papel |
|---|---|---|
| `admin` | `Admin@2025` | Acesso total |
| `gestor` | `Gestor@2025` | Consultas + upload de carteira |
| `analista` | `Analista@2025` | Só consulta individual |
| `auditor` | `Auditor@2025` | Só auditoria |

---

## Alternativa: Service Account JSON (sem gcloud)

```bash
# 1. Salve o JSON da service account como credentials.json na raiz
# 2. Exporte a variável:
export GOOGLE_APPLICATION_CREDENTIALS="credentials.json"  # Mac/Linux
$env:GOOGLE_APPLICATION_CREDENTIALS="credentials.json"    # Windows PowerShell

# 3. Rodar normalmente
streamlit run app.py
```

---

## Solução de problemas

| Erro | Causa | Solução |
|---|---|---|
| `ModuleNotFoundError: streamlit` | venv não ativo | Ativar com `source venv/bin/activate` |
| `DefaultCredentialsError` | Sem autenticação | Rodar `gcloud auth application-default login` |
| `SSLCertVerificationError` | Certificados Mac ausentes | `/Applications/Python\ 3.13/Install\ Certificates.command` |
| `403 Forbidden` BigQuery | Sem permissão | Roles: `BigQuery Data Viewer` + `BigQuery Job User` |
| `ModuleNotFoundError: config` | Terminal na pasta errada | Entrar na pasta `pf/` antes de rodar |
| `:8501 already in use` | Outra instância rodando | `streamlit run app.py --server.port 8502` |
| `fpdf` ImportError | Versão antiga | `pip install fpdf2` (com "2") |

---

## ETL Airflow (opcional)

O app funciona sem o Airflow — ele lê scores já calculados do BigQuery.
O Airflow é necessário apenas para recalcular scores em batch.

```bash
# Requer Docker Desktop instalado e rodando
docker compose up -d

# Interface web: http://localhost:8080
# Login: airflow / airflow

docker compose down  # para encerrar
```

---

*Data Verse · Grupo de Data Science — FIAP · TCC 2026*

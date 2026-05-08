<div align="center">

<img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
<img src="https://img.shields.io/badge/BigQuery-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white"/>
<img src="https://img.shields.io/badge/Apache_Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white"/>

# FIDC Insight

**Plataforma de análise de crédito com dados Núclea Dataverse**

*Data Verse · Grupo de Data Science — FIAP · TCC 2026*

🔗 **[Acessar a plataforma](https://fidc-insight.streamlit.app)**

</div>

---

## O problema que identificamos

O mercado de FIDCs (Fundos de Investimento em Direitos Creditórios) movimenta
mais de **R$ 400 bilhões** em ativos no Brasil. Gestores precisam decidir
diariamente se vale comprar um recebível, a que preço e com qual risco.

O problema: **essa decisão ainda é feita de forma manual**, sem padronização,
sem dados históricos e sem metodologia auditável.

A **Núclea Dataverse** — principal infraestrutura de dados do mercado financeiro
brasileiro — possui dados reais de comportamento de pagamento de milhares de
sacados. Esses dados existiam, mas não estavam sendo usados de forma estruturada
para apoiar as decisões de crédito.

---

## O que construímos

Uma plataforma que transforma os dados da Núclea em decisões estruturadas,
precificadas e auditáveis. Em vez de intuição, o gestor passa a ter:

- **Score de risco** calculado com 4 dimensões: qualidade, liquidez, inadimplência e fator regional
- **Preço justo** para cada operação usando metodologia RAROC e ECL padrão IFRS 9
- **Parecer automático** — Aprovado, Revisar ou Bloqueado — com justificativa clara
- **Análise de carteira** inteira após upload de uma planilha
- **Dossiê auditável** exportado em PDF assinado com hash SHA-256

---

## Como funciona por dentro

### Score Núclea (0–1.000)

```
score = (qualidade×0,35 + liquidez×0,25 + inadimplência×0,30 + regional×0,10) × 1000
```

Calibrado nos dados reais — o teto de atraso usa o p90 da distribuição
(247 dias). Um teto menor zeraria 91% da carteira, tornando o componente inútil.

### Precificação RAROC / IFRS 9

```
VP    = Face / (1 + Selic + prêmio_do_rating) ^ (prazo / 365)
ECL   = Face × PD × prazo_anos × LGD(50%)
Lucro = (Face − VP) − ECL
```

O prazo inclui o atraso histórico do sacado — se ele costuma atrasar 30 dias,
o fundo fica exposto por 30 dias a mais. O preço reflete esse risco.

### Análise de Risco

- **HHI geográfico** — detecta concentração excessiva por estado
- **EWS (Early Warning System)** — estima probabilidade de contágio na rede do sacado
- **ICL (Índice de Confiança do Lastro)** — detecta operações com volume ou prazo
  discrepante do histórico, reduzindo risco de fraude

---

## Stack

| Camada | Tecnologia |
|---|---|
| Interface | Python 3.13 · Streamlit · Plotly |
| Dados | pandas · numpy · pandas-gbq |
| BigQuery | google-cloud-bigquery · google-auth |
| ETL | Apache Airflow (Docker) |
| Exportação | fpdf2 · openpyxl |
| Segurança | bcrypt · SQLite · RBAC por papel |

---

## Sobre

Desenvolvido como Trabalho de Conclusão de Curso do programa de
**Data Science** da **FIAP**, em parceria com a **Núclea Dataverse**.

O projeto foi construído com a premissa de que ciência de dados aplicada
ao mercado financeiro precisa ser **explicável, auditável e calibrada
em dados reais** — não em suposições.

---

<div align="center">

**Data Verse · Grupo de Data Science — FIAP · TCC 2026**

*Feito com dados reais · metodologia financeira · e muito Python*

</div>

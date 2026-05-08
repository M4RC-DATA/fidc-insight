"""Suíte de testes unitários · FIDC Insight.

Cobre o domínio puro (scoring, pricing, risk, lastro). Todos os testes
são determinísticos e não dependem de BigQuery, APIs externas ou UI.

Execução:
    pytest tests/              # todos os testes
    pytest tests/ -v           # verboso
    pytest tests/ -k scoring   # só os testes de scoring
"""

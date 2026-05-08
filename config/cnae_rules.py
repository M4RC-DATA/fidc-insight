"""
Regras e tabelas CNAE (Classificação Nacional de Atividades Econômicas v2.3).

Este módulo concentra:
  * Tabelas embutidas das 21 SEÇÕES CNAE (A–U) e das 88 DIVISÕES (2 dígitos)
    — usadas como fallback offline quando a API do IBGE não estiver disponível.
  * Mapeamento de SEÇÃO → SEGMENTO MACRO consolidado (18 grupos) usado nos
    dashboards e na Visão Macro da carteira do FIDC Insight.
  * Cores oficiais de cada segmento para manter consistência visual nos
    gráficos e pills da aplicação.
  * Configurações do cliente da API IBGE (URL base, timeout, TTL de cache).

Fontes:
  * Estrutura CNAE 2.3 — ConCla/IBGE
  * API servicodados: https://servicodados.ibge.gov.br/api/v2/cnae/
"""

from __future__ import annotations

from pathlib import Path

from config.settings import PROJECT_ROOT


# =============================================================================
# API IBGE
# =============================================================================
IBGE_API_BASE = "https://servicodados.ibge.gov.br/api/v2/cnae"
IBGE_API_TIMEOUT_S = 6.0       # timeout por request (segundos)
IBGE_API_RETRIES = 2           # número de retries em erros de rede

# Cache persistente em disco (JSON) — amortiza chamadas repetidas entre reruns
CNAE_CACHE_PATH: Path = PROJECT_ROOT / "data" / "cnae_cache.json"
CNAE_CACHE_TTL_HORAS = 24 * 30  # 30 dias — CNAE é estável


# =============================================================================
# SEÇÕES CNAE (21 letras A–U) — fallback offline garantido
# =============================================================================
# Cada seção agrupa um conjunto de divisões. Aqui mapeamos:
#   letra -> (descricao oficial IBGE, segmento_macro simplificado, cor hex)
SECOES_CNAE: dict[str, dict[str, str]] = {
    "A": {
        "descricao": "Agricultura, pecuária, produção florestal, pesca e aquicultura",
        "segmento": "Agronegócio",
        "cor": "#6B8E23",
    },
    "B": {
        "descricao": "Indústrias extrativas",
        "segmento": "Extrativismo",
        "cor": "#8B4513",
    },
    "C": {
        "descricao": "Indústrias de transformação",
        "segmento": "Indústria",
        "cor": "#4682B4",
    },
    "D": {
        "descricao": "Eletricidade e gás",
        "segmento": "Utilidades",
        "cor": "#20B2AA",
    },
    "E": {
        "descricao": "Água, esgoto, atividades de gestão de resíduos e descontaminação",
        "segmento": "Utilidades",
        "cor": "#20B2AA",
    },
    "F": {
        "descricao": "Construção",
        "segmento": "Construção",
        "cor": "#CD853F",
    },
    "G": {
        "descricao": "Comércio; reparação de veículos automotores e motocicletas",
        "segmento": "Comércio",
        "cor": "#FF8C00",
    },
    "H": {
        "descricao": "Transporte, armazenagem e correio",
        "segmento": "Transporte & Logística",
        "cor": "#4169E1",
    },
    "I": {
        "descricao": "Alojamento e alimentação",
        "segmento": "Hospedagem & Alimentação",
        "cor": "#DAA520",
    },
    "J": {
        "descricao": "Informação e comunicação",
        "segmento": "TI & Comunicação",
        "cor": "#1F9BCF",
    },
    "K": {
        "descricao": "Atividades financeiras, de seguros e serviços relacionados",
        "segmento": "Financeiro",
        "cor": "#800080",
    },
    "L": {
        "descricao": "Atividades imobiliárias",
        "segmento": "Imobiliário",
        "cor": "#556B2F",
    },
    "M": {
        "descricao": "Atividades profissionais, científicas e técnicas",
        "segmento": "Serviços Profissionais",
        "cor": "#708090",
    },
    "N": {
        "descricao": "Atividades administrativas e serviços complementares",
        "segmento": "Serviços Administrativos",
        "cor": "#778899",
    },
    "O": {
        "descricao": "Administração pública, defesa e seguridade social",
        "segmento": "Setor Público",
        "cor": "#36454F",
    },
    "P": {
        "descricao": "Educação",
        "segmento": "Educação",
        "cor": "#32CD32",
    },
    "Q": {
        "descricao": "Saúde humana e serviços sociais",
        "segmento": "Saúde",
        "cor": "#DC143C",
    },
    "R": {
        "descricao": "Artes, cultura, esporte e recreação",
        "segmento": "Artes & Lazer",
        "cor": "#FF1493",
    },
    "S": {
        "descricao": "Outras atividades de serviços",
        "segmento": "Outros Serviços",
        "cor": "#9370DB",
    },
    "T": {
        "descricao": "Serviços domésticos",
        "segmento": "Outros Serviços",
        "cor": "#9370DB",
    },
    "U": {
        "descricao": "Organismos internacionais e outras instituições extraterritoriais",
        "segmento": "Outros Serviços",
        "cor": "#9370DB",
    },
}


# =============================================================================
# DIVISÕES CNAE (88 códigos de 2 dígitos) → letra da SEÇÃO
# =============================================================================
# Com este mapa, conseguimos classificar offline qualquer CNAE brasileiro
# tirando os 2 primeiros dígitos do código. Fonte: ConCla/IBGE CNAE 2.3.
DIVISAO_PARA_SECAO: dict[str, str] = {
    # Seção A — Agronegócio
    "01": "A", "02": "A", "03": "A",
    # Seção B — Extrativas
    "05": "B", "06": "B", "07": "B", "08": "B", "09": "B",
    # Seção C — Transformação
    "10": "C", "11": "C", "12": "C", "13": "C", "14": "C",
    "15": "C", "16": "C", "17": "C", "18": "C", "19": "C",
    "20": "C", "21": "C", "22": "C", "23": "C", "24": "C",
    "25": "C", "26": "C", "27": "C", "28": "C", "29": "C",
    "30": "C", "31": "C", "32": "C", "33": "C",
    # Seção D — Eletricidade e gás
    "35": "D",
    # Seção E — Água, esgoto, resíduos
    "36": "E", "37": "E", "38": "E", "39": "E",
    # Seção F — Construção
    "41": "F", "42": "F", "43": "F",
    # Seção G — Comércio
    "45": "G", "46": "G", "47": "G",
    # Seção H — Transporte
    "49": "H", "50": "H", "51": "H", "52": "H", "53": "H",
    # Seção I — Alojamento/alimentação
    "55": "I", "56": "I",
    # Seção J — Informação e comunicação
    "58": "J", "59": "J", "60": "J", "61": "J", "62": "J", "63": "J",
    # Seção K — Financeiro
    "64": "K", "65": "K", "66": "K",
    # Seção L — Imobiliário
    "68": "L",
    # Seção M — Profissionais
    "69": "M", "70": "M", "71": "M", "72": "M", "73": "M", "74": "M", "75": "M",
    # Seção N — Administrativos
    "77": "N", "78": "N", "79": "N", "80": "N", "81": "N", "82": "N",
    # Seção O — Administração pública
    "84": "O",
    # Seção P — Educação
    "85": "P",
    # Seção Q — Saúde
    "86": "Q", "87": "Q", "88": "Q",
    # Seção R — Artes
    "90": "R", "91": "R", "92": "R", "93": "R",
    # Seção S — Outros serviços
    "94": "S", "95": "S", "96": "S",
    # Seção T — Serviços domésticos
    "97": "T",
    # Seção U — Organismos internacionais
    "99": "U",
}


# =============================================================================
# Descrições curtas das divisões (para fallback quando API indisponível)
# =============================================================================
DIVISAO_DESCRICAO: dict[str, str] = {
    "01": "Agricultura, pecuária e serviços relacionados",
    "02": "Produção florestal",
    "03": "Pesca e aquicultura",
    "05": "Extração de carvão mineral",
    "06": "Extração de petróleo e gás natural",
    "07": "Extração de minerais metálicos",
    "08": "Extração de minerais não metálicos",
    "09": "Atividades de apoio à extração de minerais",
    "10": "Fabricação de produtos alimentícios",
    "11": "Fabricação de bebidas",
    "12": "Fabricação de produtos do fumo",
    "13": "Fabricação de produtos têxteis",
    "14": "Confecção de artigos do vestuário e acessórios",
    "15": "Preparação de couros e fabricação de artefatos",
    "16": "Fabricação de produtos de madeira",
    "17": "Fabricação de celulose, papel e produtos de papel",
    "18": "Impressão e reprodução de gravações",
    "19": "Fabricação de coque e derivados de petróleo",
    "20": "Fabricação de produtos químicos",
    "21": "Fabricação de produtos farmoquímicos e farmacêuticos",
    "22": "Fabricação de produtos de borracha e plástico",
    "23": "Fabricação de produtos de minerais não metálicos",
    "24": "Metalurgia",
    "25": "Fabricação de produtos de metal",
    "26": "Fabricação de produtos de informática e eletrônicos",
    "27": "Fabricação de máquinas e materiais elétricos",
    "28": "Fabricação de máquinas e equipamentos",
    "29": "Fabricação de veículos automotores",
    "30": "Fabricação de outros equipamentos de transporte",
    "31": "Fabricação de móveis",
    "32": "Fabricação de produtos diversos",
    "33": "Manutenção, reparação e instalação de máquinas",
    "35": "Eletricidade, gás e outras utilidades",
    "36": "Captação, tratamento e distribuição de água",
    "37": "Esgoto e atividades relacionadas",
    "38": "Coleta, tratamento e disposição de resíduos",
    "39": "Descontaminação e gestão de resíduos",
    "41": "Construção de edifícios",
    "42": "Obras de infraestrutura",
    "43": "Serviços especializados para construção",
    "45": "Comércio e reparação de veículos automotores",
    "46": "Comércio por atacado",
    "47": "Comércio varejista",
    "49": "Transporte terrestre",
    "50": "Transporte aquaviário",
    "51": "Transporte aéreo",
    "52": "Armazenamento e atividades auxiliares do transporte",
    "53": "Correio e outras atividades de entrega",
    "55": "Alojamento",
    "56": "Alimentação",
    "58": "Edição e edição integrada à impressão",
    "59": "Atividades cinematográficas e produção de vídeos",
    "60": "Atividades de rádio e televisão",
    "61": "Telecomunicações",
    "62": "Serviços de tecnologia da informação",
    "63": "Prestação de serviços de informação",
    "64": "Atividades de serviços financeiros",
    "65": "Seguros, resseguros e previdência complementar",
    "66": "Atividades auxiliares dos serviços financeiros",
    "68": "Atividades imobiliárias",
    "69": "Atividades jurídicas, de contabilidade e auditoria",
    "70": "Atividades de sedes de empresas e consultoria",
    "71": "Serviços de arquitetura e engenharia",
    "72": "Pesquisa e desenvolvimento científico",
    "73": "Publicidade e pesquisa de mercado",
    "74": "Outras atividades profissionais, científicas e técnicas",
    "75": "Atividades veterinárias",
    "77": "Aluguéis não imobiliários e gestão de ativos",
    "78": "Seleção, agenciamento e locação de mão de obra",
    "79": "Agências de viagens e operadores turísticos",
    "80": "Atividades de vigilância, segurança e investigação",
    "81": "Serviços para edifícios e atividades paisagísticas",
    "82": "Serviços de escritório e apoio administrativo",
    "84": "Administração pública, defesa e seguridade social",
    "85": "Educação",
    "86": "Atividades de atendimento hospitalar",
    "87": "Atenção à saúde humana integrada",
    "88": "Serviços de assistência social sem alojamento",
    "90": "Atividades artísticas, criativas e de espetáculos",
    "91": "Atividades ligadas ao patrimônio cultural",
    "92": "Atividades de exploração de jogos de azar e apostas",
    "93": "Atividades esportivas e de recreação",
    "94": "Atividades de organizações associativas",
    "95": "Reparação e manutenção de equipamentos",
    "96": "Outras atividades de serviços pessoais",
    "97": "Serviços domésticos",
    "99": "Organismos internacionais",
}


# =============================================================================
# Helpers
# =============================================================================
def segmento_da_secao(secao: str) -> str:
    """Retorna o segmento macro correspondente à letra da seção.

    Se a letra não existir, retorna 'Não classificado'.
    """
    info = SECOES_CNAE.get((secao or "").upper())
    return info["segmento"] if info else "Não classificado"


def cor_do_segmento(segmento: str) -> str:
    """Retorna a cor hex associada a um segmento macro."""
    for info in SECOES_CNAE.values():
        if info["segmento"] == segmento:
            return info["cor"]
    return "#7C8CA8"  # cinza neutro para não classificado

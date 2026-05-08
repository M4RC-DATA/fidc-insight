"""
Dossiê de Auditoria · PDF (Institutional Research style).

Estética de research note de banco de investimento:
  - Cabeçalho minimalista com logotipo textual e hairline abaixo.
  - Tipografia Helvetica (sans) para títulos, Times (serif) para corpo.
  - Sem fundos coloridos. Apenas uma linha-acento dourada em headers.
  - Hash SHA-256 em monospaced para integridade de auditoria.
  - Seção 4 · Verificação de Lastro (quando presente) inclui selo ICL
    e hash próprio do payload, compondo a trilha anti-fraude.
"""

import hashlib
import io
from typing import Optional

from fpdf import FPDF

from config import theme as t
from domain.lastro import ResultadoLastro
from domain.pricing import ResultadoPrecificacao
from utils.formatters import formatar_cnpj, formatar_moeda, formatar_percentual


# =============================================================================
# Paleta convertida para RGB
# =============================================================================
def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


INK_RGB      = _hex_to_rgb(t.INK)
GRAPHITE_RGB = _hex_to_rgb(t.GRAPHITE)
ACCENT_RGB   = _hex_to_rgb(t.ACCENT)
SLATE_RGB    = _hex_to_rgb(t.SLATE)
MUTED_RGB    = _hex_to_rgb(t.MUTED)
HAIRLINE_RGB = _hex_to_rgb(t.HAIRLINE)
POSITIVE_RGB = _hex_to_rgb(t.POSITIVE)
CAUTION_RGB  = _hex_to_rgb(t.CAUTION)
NEGATIVE_RGB = _hex_to_rgb(t.NEGATIVE)

# Mapa selo → cor RGB para chips coloridos no PDF
_SELO_RGB = {
    "VERDE":    POSITIVE_RGB,
    "AMARELO":  CAUTION_RGB,
    "VERMELHO": NEGATIVE_RGB,
}


# =============================================================================
# PDF class com header/footer institucional
# =============================================================================
class DossiePDF(FPDF):
    """FPDF customizado com cabeçalho e rodapé minimalistas."""

    def header(self):
        # Logo textual à esquerda
        self.set_xy(15, 10)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*INK_RGB)
        self.cell(0, 5, "FIDC  INSIGHT", ln=0, align="L")

        # Tipo de documento à direita
        self.set_xy(0, 10)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED_RGB)
        self.cell(-15, 5, "RESEARCH NOTE  ·  DOSSIE DE AUDITORIA", ln=0, align="R")

        # Hairline abaixo do header
        self.set_draw_color(*HAIRLINE_RGB)
        self.set_line_width(0.2)
        self.line(15, 18, 195, 18)

        self.ln(12)
        self.set_text_color(*INK_RGB)

    def footer(self):
        self.set_y(-15)

        # Hairline acima do rodapé
        self.set_draw_color(*HAIRLINE_RGB)
        self.set_line_width(0.2)
        self.line(15, self.get_y(), 195, self.get_y())

        # Texto do rodapé
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED_RGB)
        self.cell(0, 4, "Nucleo Dataverse  ·  Documento gerado automaticamente", align="L")
        self.set_y(-12)
        self.cell(0, 4, f"p. {self.page_no()} / {{nb}}", align="R")


def gerar_pdf_auditoria(
    cnpj: str,
    valor: float,
    resultado: ResultadoPrecificacao,
    rating: str,
    risco_rede: str,
    data_hora: str,
    resultado_lastro: Optional[ResultadoLastro] = None,
) -> bytes:
    """Gera o dossiê de auditoria em PDF (institutional research note).

    Args:
        cnpj: CNPJ ou ID do sacado.
        valor: Valor de face da operação.
        resultado: Resultado da precificação.
        rating: Rating atribuído (A+, A, B, C, D).
        risco_rede: Nível EWS (BAIXO/MODERADO/ALTO).
        data_hora: Timestamp formatado.
        resultado_lastro: Resultado do ``validar_lastro`` (opcional).
            Quando fornecido, adiciona a Seção 4 · Verificação de Lastro
            e compõe o hash de assinatura com o payload anti-fraude.

    Returns:
        Bytes do PDF.
    """
    # Hash de integridade — compõe lastro quando disponível
    texto_base = (
        f"{cnpj}|{valor}|{resultado.valor_presente}|"
        f"{resultado.taxa_total}|{rating}|{data_hora}"
    )
    if resultado_lastro is not None:
        texto_base += (
            f"|LASTRO:{resultado_lastro.selo.value}|"
            f"ICL:{resultado_lastro.icl}|"
            f"{resultado_lastro.hash_integridade}"
        )
    hash_assinatura = hashlib.sha256(texto_base.encode("utf-8")).hexdigest()

    pdf = DossiePDF(format="A4", unit="mm")
    pdf.alias_nb_pages()
    pdf.set_margins(left=15, top=22, right=15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    # =========================================================================
    # KICKER + TITLE
    # =========================================================================
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED_RGB)
    pdf.cell(0, 4, f"PARECER  ·  {data_hora.upper()}", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(0, 9, "Analise Individual do Sacado", ln=True)

    # Linha de identidade do sacado (CNPJ + rating inline)
    pdf.ln(1)
    pdf.set_font("Courier", "", 10)
    pdf.set_text_color(*GRAPHITE_RGB)
    pdf.cell(80, 6, formatar_cnpj(cnpj), ln=0)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*ACCENT_RGB)
    pdf.cell(0, 6, f"RATING  {rating}", ln=True, align="R")

    # Hairline
    pdf.ln(2)
    pdf.set_draw_color(*HAIRLINE_RGB)
    pdf.set_line_width(0.2)
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(6)

    # =========================================================================
    # HERO · Valor Presente Sugerido
    # =========================================================================
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTED_RGB)
    pdf.cell(0, 4, "VALOR PRESENTE SUGERIDO (DESEMBOLSO)", ln=True)

    pdf.set_font("Courier", "B", 26)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(0, 12, formatar_moeda(resultado.valor_presente, casas=0), ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SLATE_RGB)
    hero_meta = (
        f"sobre face de {formatar_moeda(valor, casas=0)}  ·  "
        f"margem real {resultado.margem_real:.2f}%  ·  "
        f"lucro RAROC {formatar_moeda(resultado.lucro_raroc, casas=0)}"
    )
    pdf.cell(0, 5, hero_meta, ln=True)
    pdf.ln(6)

    # =========================================================================
    # SEÇÃO 1 · Parâmetros da Operação
    # =========================================================================
    _secao(pdf, "1   Parametros da Operacao")
    _kv(pdf, "Valor de face",               formatar_moeda(valor))
    _kv(pdf, "Valor presente (VP)",         formatar_moeda(resultado.valor_presente))
    _kv(pdf, "Receita bruta (face - VP)",   formatar_moeda(resultado.desconto_bruto))
    _kv(pdf, "Taxa total a.a.",             formatar_percentual(resultado.taxa_total))
    _kv(pdf, "Prazo ajustado",              f"{resultado.prazo_dias} dias  ({resultado.prazo_anos:.2f} anos)")
    pdf.ln(4)

    # =========================================================================
    # SEÇÃO 2 · Parecer de Risco
    # =========================================================================
    _secao(pdf, "2   Parecer de Risco")
    _kv(pdf, "Rating atribuido",            rating)
    _kv(pdf, "Perda esperada (ECL)",        formatar_moeda(resultado.perda_esperada))
    _kv(pdf, "Lucro economico (RAROC)",     formatar_moeda(resultado.lucro_raroc))
    _kv(pdf, "Margem real ajustada",        f"{resultado.margem_real:.2f}%")
    _kv(pdf, "Early Warning System",        risco_rede)
    pdf.ln(4)

    # =========================================================================
    # SEÇÃO 3 · Verificação de Lastro (anti-fraude) — opcional
    # =========================================================================
    if resultado_lastro is not None:
        _secao(pdf, "3   Verificacao de Lastro (anti-fraude)")
        _selo_chip(pdf, resultado_lastro.selo.value, resultado_lastro.icl)
        pdf.ln(2)

        _kv(pdf, "Selo de autenticidade",      resultado_lastro.selo.value)
        _kv(pdf, "Indice de Confianca (ICL)",  f"{resultado_lastro.icl:.1f}%")
        _kv(pdf, "Z-score do valor",           f"{resultado_lastro.z_score_valor:+.2f} sigma")
        _kv(pdf, "Operacoes historicas",       str(resultado_lastro.historico.n_operacoes))
        _kv(pdf, "Meses de relacionamento",    f"{resultado_lastro.historico.meses_relacionamento:.1f} meses")
        _kv(pdf, "Frequencia mensal",          f"{resultado_lastro.historico.frequencia_mensal:.2f} ops/mes")
        _kv(pdf, "Valor medio historico",      formatar_moeda(resultado_lastro.historico.valor_medio, casas=0))
        _kv(pdf, "Desvio padrao historico",    formatar_moeda(resultado_lastro.historico.valor_desvio, casas=0))
        pdf.ln(2)

        # Motivos em Times serif, leve indentação
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*GRAPHITE_RGB)
        pdf.cell(0, 5, "Motivos:", ln=True)
        pdf.set_font("Times", "", 9.5)
        pdf.set_text_color(*INK_RGB)

        # Largura útil já descontando indent — multi_cell com w explícito
        # evita o erro "Not enough horizontal space" do fpdf2 que ocorre
        # quando a largura residual (a partir do X atual) fica abaixo da
        # largura de um único caractere da fonte.
        indent_mm = 4
        largura_util = pdf.w - pdf.l_margin - pdf.r_margin - indent_mm
        for motivo in resultado_lastro.motivos:
            pdf.set_x(pdf.l_margin + indent_mm)
            # Remove caracteres que FPDF latin-1 nao aceita (e.g. sigma)
            txt_safe = _sanitizar_latin1(f"- {motivo}")
            pdf.multi_cell(largura_util, 4.5, txt_safe)
        pdf.ln(1)

        # Recomendação
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*GRAPHITE_RGB)
        pdf.cell(0, 5, "Recomendacao:", ln=True)
        pdf.set_font("Times", "I", 9.5)
        pdf.set_text_color(*INK_RGB)
        pdf.set_x(pdf.l_margin)
        largura_total = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.multi_cell(largura_total, 4.5, _sanitizar_latin1(resultado_lastro.recomendacao))
        pdf.ln(2)

        # Hash próprio do payload de lastro — integridade anti-fraude
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*MUTED_RGB)
        pdf.cell(0, 4, "HASH DO PAYLOAD DE LASTRO", ln=True)
        pdf.set_font("Courier", "", 7.5)
        pdf.set_text_color(*GRAPHITE_RGB)
        pdf.cell(0, 4, f"SHA-256   {resultado_lastro.hash_integridade}", ln=True)
        pdf.ln(4)

        secao_num_metodologia = "4"
    else:
        secao_num_metodologia = "3"

    # =========================================================================
    # SEÇÃO Metodologia (número depende de haver ou não lastro acima)
    # =========================================================================
    _secao(pdf, f"{secao_num_metodologia}   Metodologia")
    pdf.set_font("Times", "", 10)
    pdf.set_text_color(*INK_RGB)
    metodologia = (
        "O score creditico e calculado por media ponderada de quatro dimensoes: "
        "Qualidade Creditica (35%), Liquidez (25%), Inadimplencia Historica (30%) "
        "e Fator Regional (10%). A precificacao segue o padrao RAROC, combinando "
        "Selic Meta (via API do Banco Central) e premio de risco do rating. A "
        "perda esperada (ECL) segue IFRS 9: ECL = Face x PD x LGD x Prazo em "
        "Anos, adotando LGD de 50% (benchmark de FIDCs brasileiros). O Early "
        "Warning System estima a probabilidade de contagio de inadimplencia na "
        "rede do sacado combinando atraso medio e share de inadimplencia."
    )
    if resultado_lastro is not None:
        metodologia += (
            " O Indice de Confianca do Lastro (ICL) combina Z-score do valor "
            "proposto (40%), tempo de relacionamento Cedente x Sacado (30%), "
            "frequencia mensal de transacoes (15%) e consistencia de prazo (15%), "
            "atribuindo um selo semaforico para mitigar risco de boletos frios."
        )
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, metodologia)
    pdf.ln(5)

    # =========================================================================
    # Assinatura digital (hash)
    # =========================================================================
    pdf.set_draw_color(*HAIRLINE_RGB)
    pdf.set_line_width(0.2)
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTED_RGB)
    pdf.cell(0, 4, "ASSINATURA DIGITAL  ·  INTEGRIDADE DO DOCUMENTO", ln=True)
    pdf.ln(1)

    pdf.set_font("Courier", "", 7.5)
    pdf.set_text_color(*GRAPHITE_RGB)
    pdf.cell(0, 4, f"SHA-256   {hash_assinatura}", ln=True)
    pdf.ln(3)

    # =========================================================================
    # Disclaimer
    # =========================================================================
    pdf.set_font("Times", "I", 8)
    pdf.set_text_color(*SLATE_RGB)
    disclaimer = (
        "Este documento foi gerado de forma automatizada pela plataforma FIDC "
        "Insight. O hash SHA-256 acima permite validar a integridade dos dados "
        "registrados. Trata-se de um parecer de apoio a decisao e nao substitui "
        "a avaliacao do Comite de Credito do gestor do fundo. Em caso de "
        "divergencia entre o arquivo original e copias eletronicas, prevalece "
        "o hash registrado no historico de auditoria."
    )
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 4, disclaimer)

    # =========================================================================
    # Exportação
    # =========================================================================
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


# =============================================================================
# Helpers de layout
# =============================================================================
def _secao(pdf: FPDF, titulo: str) -> None:
    """Título de seção — sans serif, caixa alta leve, linha-acento dourada curta."""
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(0, 6, titulo.upper(), ln=True)

    # Barra-acento dourada curta
    pdf.set_draw_color(*ACCENT_RGB)
    pdf.set_line_width(0.6)
    y = pdf.get_y()
    pdf.line(15, y, 35, y)
    pdf.ln(4)


def _kv(pdf: FPDF, label: str, valor: str) -> None:
    """Linha chave-valor com dot-leader sutil."""
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*SLATE_RGB)
    pdf.cell(70, 5.5, label, ln=0)

    pdf.set_font("Courier", "", 10)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(0, 5.5, valor, ln=True, align="R")

    # Hairline de separação
    pdf.set_draw_color(*HAIRLINE_RGB)
    pdf.set_line_width(0.1)
    y = pdf.get_y()
    pdf.line(15, y, 195, y)
    pdf.ln(0.5)


def _selo_chip(pdf: FPDF, selo: str, icl: float) -> None:
    """Chip colorido do selo de lastro (retângulo com fill semântico)."""
    cor = _SELO_RGB.get(selo, CAUTION_RGB)
    x0 = pdf.get_x()
    y0 = pdf.get_y()

    # Retângulo colorido (fundo)
    pdf.set_fill_color(*cor)
    pdf.rect(x0, y0, 44, 7, style="F")

    # Texto "SELO VERDE" em branco
    pdf.set_xy(x0, y0 + 0.8)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(44, 5.5, f"SELO  {selo}", align="C")

    # ICL à direita em Courier
    pdf.set_xy(x0 + 48, y0 + 1)
    pdf.set_font("Courier", "B", 11)
    pdf.set_text_color(*cor)
    pdf.cell(0, 5.5, f"ICL {icl:.1f}%", ln=True)
    pdf.ln(2)


def _sanitizar_latin1(texto: str) -> str:
    """Substitui caracteres fora do Latin-1 por equivalentes ASCII.

    FPDF com fonte core (Helvetica/Times/Courier) só aceita Latin-1.
    Mapeamos sigma, setas e outros símbolos usados nas mensagens do
    módulo de lastro para equivalentes compatíveis.
    """
    substituicoes = {
        "σ": "sigma",
        "μ": "mu",
        "±": "+/-",
        "×": "x",
        "→": "->",
        "▲": "^",
        "▼": "v",
        "≥": ">=",
        "≤": "<=",
        "…": "...",
        "—": "-",
        "–": "-",
        "•": "-",
    }
    for k, v in substituicoes.items():
        texto = texto.replace(k, v)
    # Fallback: força latin-1 com replace
    return texto.encode("latin-1", errors="replace").decode("latin-1")


# =============================================================================
# PDF Resumo Executivo da Carteira
# =============================================================================

def gerar_pdf_carteira(
    n_sacados: int,
    face_total: float,
    vp_total: float,
    ecl_total: float,
    lucro_total: float,
    margem: float,
    score_medio: float,
    rating_dom: str,
    hhi: float,
    pct_a: float,
    data_hora: str,
    nome_arquivo: str = "carteira",
) -> bytes:
    """Gera resumo executivo da carteira em PDF."""

    payload = f"{n_sacados}|{face_total}|{vp_total}|{ecl_total}|{margem}|{data_hora}"
    hash_doc = hashlib.sha256(payload.encode()).hexdigest()

    pdf = DossiePDF()
    pdf.add_page()

    # Titulo
    pdf.set_xy(15, 28)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*INK_RGB)
    pdf.cell(0, 8, "Resumo Executivo da Carteira", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*SLATE_RGB)
    pdf.cell(0, 5, f"Gerado em {data_hora}  |  Arquivo: {_sanitizar_latin1(nome_arquivo)}", ln=True)
    pdf.ln(4)

    # Secao 1 — Consolidado
    _secao(pdf, "1. Consolidado Financeiro")
    _kv(pdf, "Sacados analisados",      f"{n_sacados}")
    _kv(pdf, "Face total",              formatar_moeda(face_total))
    _kv(pdf, "Valor Presente (VP)",     formatar_moeda(vp_total))
    _kv(pdf, "Perda Esperada (ECL)",    formatar_moeda(ecl_total))
    _kv(pdf, "Lucro RAROC",             formatar_moeda(lucro_total))
    _kv(pdf, "Margem real ponderada",   formatar_percentual(margem / 100))
    pdf.ln(4)

    # Secao 2 — Qualidade
    _secao(pdf, "2. Qualidade da Carteira")
    _kv(pdf, "Score Nuclea medio (pond.)", f"{score_medio:.0f} / 1.000")
    _kv(pdf, "Rating dominante",           rating_dom)
    _kv(pdf, "Grau de investimento (A+/A)",formatar_percentual(pct_a / 100))
    _kv(pdf, "HHI geografico",             f"{hhi:.4f}  {'(diversificado)' if hhi < 0.15 else '(moderado)' if hhi < 0.25 else '(concentrado)'}")
    pdf.ln(4)

    # Hash
    _secao(pdf, "3. Integridade do Documento")
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(*MUTED_RGB)
    pdf.multi_cell(0, 4.5, f"SHA-256: {hash_doc}")

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

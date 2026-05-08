"""
Sidebar · Executive Dashboard (v3).

Fundo escuro institucional. Navegação em pílulas grandes. Controles de
simulação aparecem contextualmente quando a view ativa é "Parecer Individual".
Topo da sidebar exibe chip do usuário logado com papel e botão de logout.
Navegação é filtrada de acordo com as permissões do papel (RBAC).
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional

import streamlit as st

from config.auth_rules import PAPEIS_DESCRICAO, Papel, PERMISSOES_VIEWS
from services.auth import Usuario, logout
from ui.components import render_brand


Pagina = Literal[
    "home", "macro", "individual", "carteira", "carteira_upload", "nuclea_base",
    "parametros", "auditoria", "admin",
]


@dataclass
class EstadoSidebar:
    """Estado atual selecionado na sidebar."""
    pagina: Pagina
    cnpj: str
    valor: float
    data_vencimento: Optional[date]
    executar_parecer: bool


# Ordem canônica de exibição — views são filtradas pelo papel do usuário
# Reposicionada como cockpit decisório:
#   Análise        → cockpit + parecer + valoração
#   Exploração     → explorador + benchmark
#   Governança     → parâmetros + auditoria + admin
_OPCOES_ORDENADAS = [
    ("📂 Upload de Carteira",  "carteira_upload"),
    ("Cockpit",                "macro"),
    ("Parecer Individual",     "individual"),
    ("Valoração",              "carteira"),
    ("Explorador",             "filtros"),
    ("Benchmark",              "nuclea_base"),
    ("Parâmetros e Modelo",    "parametros"),
    ("Auditoria",              "auditoria"),
    ("Administração",          "admin"),
]


def _label(texto: str) -> None:
    """Kicker de seção dentro da sidebar (fundo escuro)."""
    st.markdown(
        f'<div class="kicker-light" style="margin: 0.65rem 0 0.6rem 0;">{texto}</div>',
        unsafe_allow_html=True,
    )


def _divisor(margin_top: str = "1.25rem", margin_bottom: str = "0.6rem") -> None:
    st.markdown(
        '<div style="height: 1px; background: rgba(255,255,255,0.08); '
        f'margin: {margin_top} 0 {margin_bottom} 0;"></div>',
        unsafe_allow_html=True,
    )


def _render_user_chip(usuario: Usuario) -> None:
    """Chip com avatar-inicial + nome + papel + botão de logout."""
    iniciais = "".join(part[0].upper() for part in usuario.nome.split()[:2])
    desc_papel = PAPEIS_DESCRICAO.get(Papel(usuario.papel), "")

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:0.7rem;
                    padding:0.7rem 0.75rem;margin-top:0.2rem;
                    background:rgba(255,255,255,0.04);
                    border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;">
            <div style="width:34px;height:34px;border-radius:50%;
                        background:#1F9BCF;color:#FFFFFF;
                        display:flex;align-items:center;justify-content:center;
                        font-family:'JetBrains Mono',monospace;font-weight:700;
                        font-size:0.82rem;letter-spacing:0.02em;">
                {iniciais or "·"}
            </div>
            <div style="flex:1;min-width:0;">
                <div style="color:#E5ECF7;font-weight:600;font-size:0.85rem;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {usuario.nome}
                </div>
                <div style="color:#7C8CA8;font-family:'JetBrains Mono',monospace;
                            font-size:0.68rem;text-transform:uppercase;
                            letter-spacing:0.08em;margin-top:0.08rem;">
                    {usuario.papel}
                </div>
            </div>
        </div>
        <div style="color:#7C8CA8;font-size:0.72rem;line-height:1.45;
                    margin:0.45rem 0.15rem 0 0.15rem;">
            {desc_papel}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Sair", key="logout_btn", use_container_width=True):
        logout()
        st.rerun()


def render(usuario: Usuario) -> EstadoSidebar:
    """Renderiza a sidebar e retorna o estado selecionado."""

    with st.sidebar:
        render_brand()
        _divisor(margin_top="1.25rem", margin_bottom="0.6rem")

        _label("Sessão")
        _render_user_chip(usuario)
        _divisor(margin_top="1.25rem", margin_bottom="0.6rem")

        # Badge de carteira ativa — só aparece quando há upload
        df_upload = st.session_state.get("df_carteira_upload")
        modo_upload = df_upload is not None and not df_upload.empty

        if modo_upload:
            upload_info = st.session_state.get("df_carteira_upload_info", {})
            n_sac = upload_info.get("n_sacados", len(df_upload))
            nome  = upload_info.get("nome_arquivo", "carteira.xlsx")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:8px 10px;'
                f'border-radius:6px;background:var(--positive-soft,#F0FDF4);'
                f'border:1px solid var(--positive,#16A34A);margin-bottom:6px;">'
                f'<span style="font-size:14px">📂</span>'
                f'<div style="font-size:12px;line-height:1.4;">'
                f'<span style="font-weight:500;color:var(--color-text-success,#16A34A)">Carteira ativa</span><br>'
                f'<span style="color:var(--color-text-secondary)">{nome} · {n_sac} sacados</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if st.button("🗑 Limpar carteira", use_container_width=True, type="secondary"):
                st.session_state.pop("df_carteira_upload", None)
                st.session_state.pop("df_carteira_upload_info", None)
                st.rerun()
            _divisor(margin_top="1rem", margin_bottom="0.6rem")

        # Navegação com grupos — labels são só texto, só itens são clicáveis
        permitidas = PERMISSOES_VIEWS.get(Papel(usuario.papel), set())

        _GRUPOS = [
            ("", [
                ("Início",              "home"),
            ]),
            ("Analisar", [
                ("Consulta Individual", "individual"),
                ("Minha Carteira",      "carteira_upload"),
            ]),
            ("Minha carteira", [
                ("Visão Geral",         "macro"),
                ("Valoração",           "carteira"),
            ]),
            ("Referência", [
                ("Núclea",              "nuclea_base"),
            ]),
            ("Sistema", [
                ("Auditoria",           "auditoria"),
                ("Administração",       "admin"),
            ]),
        ]

        # Página padrão na primeira visita
        if "pagina_nav" not in st.session_state:
            st.session_state["pagina_nav"] = "home"

        # Garantir que a página salva ainda é permitida para este papel
        if st.session_state["pagina_nav"] not in permitidas:
            st.session_state["pagina_nav"] = "home" if "home" in permitidas else next(iter(permitidas))

        pagina: Pagina = st.session_state["pagina_nav"]  # type: ignore

        cnpj     = ""
        valor    = 0.0
        dt_venc: Optional[date] = None
        executar = False

        # Renderiza botões de navegação; controles aparecem inline
        # logo abaixo do botão da página ativa (sem scroll até o final).
        alguma_view = False
        for grupo_label, itens in _GRUPOS:
            itens_perm = [(lbl, view) for lbl, view in itens if view in permitidas]
            if not itens_perm:
                continue
            alguma_view = True

            if grupo_label:
                st.markdown(
                    f'<span class="nav-group-label">{grupo_label}</span>',
                    unsafe_allow_html=True,
                )

            for lbl, view in itens_perm:
                ativo = pagina == view
                css_classe = "nav-btn-ativo" if ativo else "nav-btn"
                st.markdown(f'<div class="{css_classe}">', unsafe_allow_html=True)
                if st.button(lbl, key=f"nav_btn_{view}", use_container_width=True):
                    st.session_state["pagina_nav"] = view
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                # Controles contextuais — aparecem logo abaixo do botão ativo
                if ativo and view == "individual":
                    st.markdown(
                        '<div style="border-left:2px solid rgba(255,255,255,.1);'
                        'margin:4px 0 8px 12px;padding:10px 10px 4px;">',
                        unsafe_allow_html=True,
                    )
                    cnpj = st.text_input(
                        "Sacado",
                        value="",
                        placeholder="CNPJ ou hash",
                        label_visibility="visible",
                    )
                    valor = st.number_input(
                        "Volume nominal (R$)",
                        min_value=0.0, value=0.0,
                        step=5_000.0, format="%.2f",
                    )
                    dt_venc = st.date_input(
                        "Vencimento",
                        value=None,
                        min_value=date.today(),
                    )
                    habilitado = bool(cnpj.strip()) and valor > 0 and dt_venc is not None
                    if st.button(
                        "Executar parecer",
                        type="primary",
                        use_container_width=True,
                        disabled=not habilitado,
                        key="btn_exec_parecer",
                    ):
                        executar = True
                    st.markdown('</div>', unsafe_allow_html=True)

                elif ativo and view == "carteira":
                    st.markdown(
                        '<div style="border-left:2px solid rgba(255,255,255,.1);'
                        'margin:4px 0 8px 12px;padding:10px 10px 4px;">',
                        unsafe_allow_html=True,
                    )
                    dt_venc = st.date_input(
                        "Vencimento do Fundo",
                        value=None,
                        min_value=date.today(),
                    )
                    valor = st.number_input(
                        "Valor total (R$)",
                        min_value=0.0, value=0.0,
                        step=100_000.0, format="%.2f",
                        help="Opcional — 0 usa os valores reais do BigQuery.",
                    )
                    habilitado = dt_venc is not None
                    if st.button(
                        "Calcular valoração",
                        type="primary",
                        use_container_width=True,
                        disabled=not habilitado,
                        key="btn_exec_carteira",
                    ):
                        executar = True
                    st.markdown('</div>', unsafe_allow_html=True)

        if not alguma_view:
            st.warning("Seu papel não tem views habilitadas. Procure o administrador.")
            st.stop()

                # ------------ rodapé · fonte de dados ------------
        _divisor(margin_top="2rem", margin_bottom="0.75rem")
        st.markdown(
            """
            <div class="kicker-light">Fonte de Dados</div>
            <div style="color: #E5ECF7; font-family: 'JetBrains Mono', monospace;
                        font-size: 0.78rem; margin-top: 0.35rem; line-height: 1.5;">
                Data Verse<br>
                <span style="color: #7C8CA8; font-size: 0.7rem;">Grupo de Data Science — FIAP</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return EstadoSidebar(
        pagina=pagina,
        cnpj=cnpj.strip(),
        valor=valor,
        data_vencimento=dt_venc,
        executar_parecer=executar,
    )
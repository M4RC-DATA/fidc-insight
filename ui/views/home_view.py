"""
View · Home · FIDC Insight — Data Verse.
Tela de entrada sem sidebar. Visual com identidade Data Verse.
"""
import streamlit as st
from services.auth import logout


_EXTRAS = {
    "admin":   [
        ("Auditoria",     "auditoria", "📋", "Trilha de acessos e pareceres"),
        ("Administração", "admin",     "⚙️", "Gerenciar usuarios e papeis"),
    ],
    "gestor":   [],
    "analista": [],
    "auditor":  [
        ("Auditoria", "auditoria", "📋", "Trilha de acessos e pareceres"),
    ],
}


def render(usuario) -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
    section[data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    #MainMenu, footer, header { display: none !important; }
    .stApp {
        background: #F8FAFC !important;
        background-image:
            radial-gradient(ellipse at 10% 60%, rgba(0,188,212,.06) 0%, transparent 55%),
            radial-gradient(ellipse at 90% 20%, rgba(124,58,237,.05) 0%, transparent 55%) !important;
        font-family: 'DM Sans', 'Inter', sans-serif !important;
    }
    .block-container { padding-top: 0 !important; max-width: 820px; margin: 0 auto; }

    .dv-topbar {
        display: flex; justify-content: space-between; align-items: center;
        padding: 1.75rem 0 1.25rem; border-bottom: 1px solid #F1F5F9;
        margin-bottom: 2.75rem;
    }
    .dv-logo { display: flex; align-items: center; gap: 12px; }
    .dv-logo-name { font-weight: 700; color: #0F172A; font-size: 1rem; letter-spacing: -.015em; }
    .dv-logo-sub { color: #94A3B8; font-size: .7rem; margin-top: 2px; }
    .dv-user-info { text-align: right; font-size: .78rem; color: #64748B; }
    .dv-user-info strong { color: #0F172A; }

    .dv-headline { margin-bottom: 2rem; }
    .dv-headline h2 {
        font-size: 1.5rem; font-weight: 600; color: #0F172A;
        letter-spacing: -.025em; margin: 0 0 .35rem;
    }
    .dv-headline p { font-size: .88rem; color: #64748B; margin: 0; }

    .dv-card {
        background: white; border: 1.5px solid #E8EDF5;
        border-radius: 14px; padding: 1.75rem 1.5rem 1.25rem;
        position: relative; overflow: hidden;
        transition: border-color .18s, box-shadow .18s, transform .15s;
    }
    .dv-card::after {
        content: ''; position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #00BCD4 0%, #7C3AED 100%);
        opacity: 0; transition: opacity .18s;
        border-radius: 14px 14px 0 0;
    }
    .dv-card:hover {
        border-color: rgba(0,188,212,.4);
        box-shadow: 0 8px 32px rgba(0,188,212,.1), 0 2px 8px rgba(0,0,0,.04);
        transform: translateY(-2px);
    }
    .dv-card:hover::after { opacity: 1; }
    .dv-icon {
        width: 44px; height: 44px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.25rem; margin-bottom: 1rem;
    }
    .dv-icon-a { background: #E0F7FA; }
    .dv-icon-b { background: #EDE9FE; }
    .dv-card-title { font-size: .98rem; font-weight: 600; color: #0F172A; margin: 0 0 .4rem; }
    .dv-card-desc { font-size: .8rem; color: #64748B; line-height: 1.6; margin: 0 0 1.1rem; }
    .dv-cta { font-size: .78rem; font-weight: 600; }
    .dv-cta-a { color: #0891B2; }
    .dv-cta-b { color: #7C3AED; }

    .dv-extras-label {
        font-size: .68rem; font-weight: 700; letter-spacing: .1em;
        text-transform: uppercase; color: #CBD5E1; margin: 2rem 0 .75rem;
    }
    .dv-extra {
        background: white; border: 1px solid #E8EDF5; border-radius: 8px;
        padding: .85rem .75rem; text-align: center;
        transition: border-color .15s, box-shadow .15s;
    }
    .dv-extra:hover { border-color: #00BCD4; box-shadow: 0 4px 12px rgba(0,188,212,.07); }
    .dv-extra-icon { font-size: 1.1rem; margin-bottom: .3rem; }
    .dv-extra-title { font-size: .78rem; font-weight: 500; color: #0F172A; margin: 0 0 .15rem; }
    .dv-extra-desc { font-size: .68rem; color: #94A3B8; margin: 0; }

    .dv-footer {
        text-align: center; margin-top: 3rem; padding-top: 1.25rem;
        border-top: 1px solid #F1F5F9;
        font-size: .68rem; color: #CBD5E1; letter-spacing: .02em;
    }
    </style>
    """, unsafe_allow_html=True)

    # Topbar
    st.markdown(
        f'''<div class="dv-topbar">
          <div class="dv-logo">
            <svg width="26" height="26" viewBox="0 0 32 32" fill="none">
              <path d="M4 4 L16 28 L28 4" stroke="#00BCD4" stroke-width="5"
                    stroke-linecap="round" stroke-linejoin="round" fill="none"/>
              <path d="M4 4 L16 28" stroke="#7C3AED" stroke-width="5"
                    stroke-linecap="round" fill="none"/>
            </svg>
            <div>
              <div class="dv-logo-name">Data Verse</div>
              <div class="dv-logo-sub">FIDC Insight · Grupo de Data Science — FIAP</div>
            </div>
          </div>
          <div class="dv-user-info">{usuario.nome}<br><strong>{usuario.papel.upper()}</strong></div>
        </div>''',
        unsafe_allow_html=True,
    )

    # Headline
    st.markdown(
        '''<div class="dv-headline">
          <h2>O que você quer fazer?</h2>
          <p>Selecione uma das opções abaixo</p>
        </div>''',
        unsafe_allow_html=True,
    )

    # Cards principais
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown(
            '''<div class="dv-card">
              <div class="dv-icon dv-icon-a">🔍</div>
              <div class="dv-card-title">Consulta Individual</div>
              <div class="dv-card-desc">Analise um sacado da base Núclea.
                Rating, precificação RAROC e recomendação de decisão.</div>
              <div class="dv-cta dv-cta-a">Consultar sacado →</div>
            </div>''',
            unsafe_allow_html=True,
        )
        if st.button("Consultar →", use_container_width=True,
                     type="primary", key="btn_individual"):
            st.session_state["pagina"] = "individual"
            st.rerun()

    with c2:
        st.markdown(
            '''<div class="dv-card">
              <div class="dv-icon dv-icon-b">📂</div>
              <div class="dv-card-title">Minha Carteira</div>
              <div class="dv-card-desc">Faça upload de uma lista de sacados
                e explore a análise completa do seu portfólio.</div>
              <div class="dv-cta dv-cta-b">Carregar carteira →</div>
            </div>''',
            unsafe_allow_html=True,
        )
        if st.button("Carregar →", use_container_width=True,
                     type="primary", key="btn_carteira"):
            st.session_state["pagina"] = "carteira_upload"
            st.rerun()

    # Extras por papel
    extras = _EXTRAS.get(usuario.papel, [])
    if extras:
        st.markdown('<div class="dv-extras-label">Mais opções</div>', unsafe_allow_html=True)
        cols = st.columns(len(extras), gap="small")
        for col, (label, pagina, icone, desc) in zip(cols, extras):
            with col:
                st.markdown(
                    f'''<div class="dv-extra">
                      <div class="dv-extra-icon">{icone}</div>
                      <div class="dv-extra-title">{label}</div>
                      <div class="dv-extra-desc">{desc}</div>
                    </div>''',
                    unsafe_allow_html=True,
                )
                if st.button(label, key=f"btn_{pagina}",
                             use_container_width=True, type="secondary"):
                    st.session_state["pagina"] = pagina
                    st.rerun()

    # Footer
    st.markdown(
        '<div class="dv-footer">Data Verse · Grupo de Data Science — FIAP · TCC 2026</div>',
        unsafe_allow_html=True,
    )

    # Sair
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_m, _ = st.columns([4, 1, 4])
    with col_m:
        if st.button("Sair", use_container_width=True,
                     type="secondary", key="btn_sair"):
            logout()
            st.rerun()

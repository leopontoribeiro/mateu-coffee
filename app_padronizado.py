# ☕ MATEU BARISTA v1.1 - COFFEE CONTROL
# Aplicação Padronizada com Design System Completo

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from design_system import (
    apply_theme, COLORS, TYPOGRAPHY, SPACING, SHADOWS,
    header_component, stat_card, success_button, secondary_button,
    info_box, separator, labeled_metric, format_number, get_status_color,
    toast_message
)

# ═══════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ═══════════════════════════════════════════════════════════════

apply_theme()

# Estado da sessão
if "grains" not in st.session_state:
    st.session_state.grains = [
        {"id": 1, "nome": "Ethiopian AA", "origem": "Etiópia", "torra": "Médio", "quantidade": 2.5, "criado_em": "2024-06-01"},
        {"id": 2, "nome": "Colombian Geisha", "origem": "Colômbia", "torra": "Claro", "quantidade": 1.8, "criado_em": "2024-06-02"},
    ]

if "brewsession" not in st.session_state:
    st.session_state.brewsession = []

if "current_user" not in st.session_state:
    st.session_state.current_user = "Leandro Ribeiro"

# Timezone
tz = pytz.timezone('America/Sao_Paulo')

# ═══════════════════════════════════════════════════════════════
# SIDEBAR - NAVEGAÇÃO
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(f"""
    <div style='text-align: center; padding: {SPACING.xl} {SPACING.lg};'>
        <h2 style='margin: 0; color: {COLORS.primary}; font-size: 24px;'>☕</h2>
        <h3 style='margin: {SPACING.sm} 0 {SPACING.xs} 0; color: {COLORS.primary}; font-weight: bold;'>MATEU</h3>
        <p style='margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>BARISTA</p>
        <p style='margin: {SPACING.xs} 0 0 0; color: {COLORS.text_tertiary}; font-size: 11px;'>Coffee Control</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Menu de navegação
    st.markdown(f"<p style='color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>MENU</p>",
               unsafe_allow_html=True)

    tab_selection = st.radio(
        "Navegação",
        ["📊 Dashboard", "📦 Grãos", "☕ Preparos", "📈 Histórico", "⚙️ Config"],
        label_visibility="collapsed"
    )

    st.divider()

    # Perfil
    st.markdown(f"""
    <div style='padding: {SPACING.lg} {SPACING.md}; background-color: {COLORS.bg_light};
                border-radius: {SPACING.radius_default}; border: 1px solid {COLORS.border};'>
        <p style='margin: 0; color: {COLORS.text_secondary}; font-size: 11px; font-weight: 600;'>USUÁRIO</p>
        <p style='margin: {SPACING.xs} 0 0 0; color: {COLORS.text_primary}; font-size: 14px; font-weight: bold;'>
            👤 {st.session_state.current_user}
        </p>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

if "📊 Dashboard" in tab_selection:
    header_component("Dashboard", "Visão geral do seu sistema de extrações", "📊")

    # Estatísticas principais
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        stat_card("Grãos Cadastrados", f"{len(st.session_state.grains)}", icon="📦", color=COLORS.primary)

    with col2:
        total_estoque = sum(g["quantidade"] for g in st.session_state.grains)
        stat_card("Estoque Total", f"{total_estoque:.1f}kg", icon="⚖️", color=COLORS.info)

    with col3:
        preparos_hoje = len(st.session_state.brewsession)
        stat_card("Preparos Hoje", f"{preparos_hoje}", icon="☕", color=COLORS.success)

    with col4:
        stat_card("Taxa Capacidade", f"{min(100, int((total_estoque / 10) * 100))}%",
                 icon="📈", color=COLORS.warning if total_estoque < 2 else COLORS.success)

    separator()

    # Seção de ações rápidas
    st.markdown(f"<h3 style='color: {COLORS.text_primary};'>Ações Rápidas</h3>",
               unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if success_button("➕ Novo Grão", key="btn_novo_grao"):
            st.session_state.page = "new_grain"
            toast_message("Abrindo formulário de novo grão", "success")

    with col2:
        if success_button("☕ Registrar Preparo", key="btn_novo_preparo"):
            st.session_state.page = "new_brew"
            toast_message("Abrindo registro de preparo", "success")

    with col3:
        if secondary_button("📊 Ver Relatório", key="btn_relatorio"):
            toast_message("Abrindo relatório", "info")

    separator()

    # Últimos preparos
    if st.session_state.brewsession:
        st.markdown(f"<h3 style='color: {COLORS.text_primary};'>Últimos Preparos</h3>",
                   unsafe_allow_html=True)

        for brew in st.session_state.brewsession[-3:]:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"<p style='margin: 0; color: {COLORS.text_primary}; font-weight: 600;'>"
                           f"☕ {brew['grain']}</p>",
                           unsafe_allow_html=True)
            with col2:
                st.markdown(f"<p style='margin: 0; color: {COLORS.text_secondary}; font-size: 12px;'>"
                           f"{brew['ratio']}</p>",
                           unsafe_allow_html=True)
            with col3:
                st.markdown(f"<p style='margin: 0; color: {COLORS.text_tertiary}; font-size: 12px;'>"
                           f"{brew['time']}</p>",
                           unsafe_allow_html=True)
            separator()
    else:
        info_box("Nenhum preparo registrado",
                "Comece registrando seu primeiro preparo para acompanhar as extrações!",
                "📝", "info")

# ═══════════════════════════════════════════════════════════════
# GRÃOS
# ═══════════════════════════════════════════════════════════════

elif "📦 Grãos" in tab_selection:
    header_component("Cadastro de Grãos", "Gerencie seus grãos de café", "📦")

    # Botão novo grão
    if success_button("➕ Novo Grão", key="btn_novo_grao_page"):
        st.session_state.new_grain_form = True

    if st.session_state.get("new_grain_form", False):
        separator()
        st.markdown(f"<h3 style='color: {COLORS.primary};'>Novo Grão de Café</h3>",
                   unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Grão *", placeholder="Ex: Ethiopian AA")
            origem = st.selectbox("Origem *", ["Etiópia", "Colômbia", "Brasil", "Quênia", "Vietnã", "Outro"])

        with col2:
            torra = st.radio("Grau de Torra", ["Claro", "Médio", "Escuro"], horizontal=True)
            quantidade = st.number_input("Quantidade (kg) *", min_value=0.0, step=0.1)

        col1, col2 = st.columns(2)

        with col1:
            if success_button("✓ Salvar Grão", key="btn_salvar_grao"):
                if nome and origem:
                    novo_grao = {
                        "id": len(st.session_state.grains) + 1,
                        "nome": nome,
                        "origem": origem,
                        "torra": torra,
                        "quantidade": quantidade,
                        "criado_em": datetime.now(tz).strftime("%Y-%m-%d %H:%M")
                    }
                    st.session_state.grains.append(novo_grao)
                    st.session_state.new_grain_form = False
                    toast_message(f"Grão '{nome}' adicionado com sucesso!", "success")
                    st.rerun()
                else:
                    toast_message("Preencha os campos obrigatórios (*)", "error")

        with col2:
            if secondary_button("← Cancelar", key="btn_cancelar_grao"):
                st.session_state.new_grain_form = False
                st.rerun()

    separator()

    # Lista de grãos
    if st.session_state.grains:
        st.markdown(f"<h3 style='color: {COLORS.text_primary};'>Grãos Cadastrados ({len(st.session_state.grains)})</h3>",
                   unsafe_allow_html=True)

        for grain in st.session_state.grains:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 0.5])

                with col1:
                    st.markdown(f"<p style='margin: 0; color: {COLORS.text_primary}; font-weight: 600;'>"
                               f"📦 {grain['nome']}</p>",
                               unsafe_allow_html=True)
                    st.markdown(f"<p style='margin: {SPACING.xs} 0 0 0; color: {COLORS.text_secondary}; font-size: 12px;'>"
                               f"Origem: {grain['origem']} • Torra: {grain['torra']}</p>",
                               unsafe_allow_html=True)

                with col2:
                    st.markdown(f"<p style='text-align: center; margin: 0; color: {COLORS.primary}; font-weight: bold;'>"
                               f"{grain['quantidade']:.1f}kg</p>",
                               unsafe_allow_html=True)

                with col3:
                    percentual = min(100, int((grain['quantidade'] / 3) * 100))
                    cor_estoque = get_status_color(percentual)
                    st.markdown(f"<p style='text-align: center; margin: 0; color: {cor_estoque}; font-size: 12px;'>"
                               f"{percentual}%</p>",
                               unsafe_allow_html=True)

                with col4:
                    if st.button("✕", key=f"del_grain_{grain['id']}", help="Remover"):
                        st.session_state.grains = [g for g in st.session_state.grains if g['id'] != grain['id']]
                        toast_message(f"Grão removido", "success")
                        st.rerun()

                separator()
    else:
        info_box("Nenhum grão cadastrado",
                "Clique em 'Novo Grão' para começar a adicionar seus grãos de café!",
                "📦", "info")

# ═══════════════════════════════════════════════════════════════
# PREPAROS
# ═══════════════════════════════════════════════════════════════

elif "☕ Preparos" in tab_selection:
    header_component("Registrar Preparo", "Controle suas extrações de café", "☕")

    if st.session_state.grains:
        col1, col2 = st.columns(2)

        with col1:
            grain_names = [g["nome"] for g in st.session_state.grains]
            selected_grain = st.selectbox("Selecione o Grão *", grain_names)
            grain_obj = next(g for g in st.session_state.grains if g["nome"] == selected_grain)

            st.markdown(f"""
            <div style='background-color: {COLORS.primary_bg}; border: 2px solid {COLORS.primary};
                        border-radius: {SPACING.radius_default}; padding: {SPACING.lg}; margin: {SPACING.lg} 0;'>
                <p style='margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>INFORMAÇÕES DO GRÃO</p>
                <p style='margin: {SPACING.xs} 0 0 0; color: {COLORS.primary}; font-weight: bold;'>
                    {grain_obj['nome']}
                </p>
                <p style='margin: {SPACING.xs} 0 0 0; color: {COLORS.text_secondary}; font-size: 13px;'>
                    🌍 {grain_obj['origem']} • 🔥 {grain_obj['torra']} • ⚖️ {grain_obj['quantidade']:.1f}kg
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            dose = st.number_input("Peso da Dose (g) *", min_value=10.0, max_value=50.0, value=18.0, step=0.5)
            tempo_extracao = st.number_input("Tempo de Extração (s) *", min_value=15, max_value=60, value=28, step=1)
            liquido = st.number_input("Resultado Líquido (g) *", min_value=20.0, max_value=100.0, value=36.0, step=0.5)

        # Cálculo do ratio
        ratio = liquido / dose

        st.markdown(f"""
        <div style='background-color: {COLORS.bg_light}; border-radius: {SPACING.radius_default}; padding: {SPACING.lg};
                    border: 1px solid {COLORS.border}; margin: {SPACING.lg} 0;'>
            <p style='margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>RATIO CALCULADO</p>
            <p style='margin: {SPACING.xs} 0 0 0; color: {COLORS.success}; font-size: 24px; font-weight: bold;'>
                1:{ratio:.2f}
            </p>
            <p style='margin: {SPACING.xs} 0 0 0; color: {COLORS.text_secondary}; font-size: 12px;'>
                Dose {dose:.1f}g → Resultado {liquido:.1f}g
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            if success_button("✓ Registrar Preparo", key="btn_registrar"):
                novo_brew = {
                    "grain": selected_grain,
                    "dose": dose,
                    "time": tempo_extracao,
                    "yield": liquido,
                    "ratio": f"1:{ratio:.2f}",
                    "timestamp": datetime.now(tz).strftime("%H:%M:%S"),
                    "data": datetime.now(tz).strftime("%Y-%m-%d")
                }
                st.session_state.brewsession.append(novo_brew)
                toast_message(f"Preparo registrado! Ratio: 1:{ratio:.2f}", "success")
                st.rerun()

        with col2:
            if secondary_button("← Limpar Formulário", key="btn_limpar"):
                st.rerun()

    else:
        info_box("Nenhum grão cadastrado",
                "Você precisa cadastrar grãos antes de registrar preparos. Vá para 'Grãos' e adicione seus grãos!",
                "⚠️", "warning")

# ═══════════════════════════════════════════════════════════════
# HISTÓRICO
# ═══════════════════════════════════════════════════════════════

elif "📈 Histórico" in tab_selection:
    header_component("Histórico & Métricas", "Acompanhe suas extrações", "📈")

    if st.session_state.brewsession:
        # Resumo do dia
        col1, col2, col3 = st.columns(3)

        with col1:
            total_hoje = len(st.session_state.brewsession)
            st.markdown(f"<p style='text-align: center; margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>TOTAL HOJE</p>",
                       unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; margin: {SPACING.sm} 0 0 0; color: {COLORS.primary}; font-size: 28px; font-weight: bold;'>{total_hoje}</p>",
                       unsafe_allow_html=True)

        with col2:
            ratios = [float(b["ratio"].split(":")[1]) for b in st.session_state.brewsession]
            avg_ratio = sum(ratios) / len(ratios) if ratios else 0
            st.markdown(f"<p style='text-align: center; margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>RATIO MÉDIO</p>",
                       unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; margin: {SPACING.sm} 0 0 0; color: {COLORS.primary}; font-size: 28px; font-weight: bold;'>1:{avg_ratio:.2f}</p>",
                       unsafe_allow_html=True)

        with col3:
            total_massa = sum(b["dose"] for b in st.session_state.brewsession)
            st.markdown(f"<p style='text-align: center; margin: 0; color: {COLORS.text_secondary}; font-size: 12px; font-weight: 600;'>MASSA TOTAL</p>",
                       unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; margin: {SPACING.sm} 0 0 0; color: {COLORS.primary}; font-size: 28px; font-weight: bold;'>{total_massa:.1f}g</p>",
                       unsafe_allow_html=True)

        separator()

        # Tabela de preparos
        st.markdown(f"<h3 style='color: {COLORS.text_primary};'>Preparos Registrados</h3>",
                   unsafe_allow_html=True)

        df = pd.DataFrame(st.session_state.brewsession)
        df_display = df[["timestamp", "grain", "dose", "yield", "ratio"]].copy()
        df_display.columns = ["Hora", "Grão", "Dose (g)", "Resultado (g)", "Ratio"]

        st.dataframe(df_display, use_container_width=True, hide_index=True)

    else:
        info_box("Nenhum preparo registrado",
                "Comece registrando seus preparos em 'Preparos' para ver o histórico aqui!",
                "📊", "info")

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════

elif "⚙️ Config" in tab_selection:
    header_component("Configurações", "Ajuste suas preferências", "⚙️")

    st.markdown(f"<h3 style='color: {COLORS.text_primary};'>Perfil do Usuário</h3>",
               unsafe_allow_html=True)

    novo_nome = st.text_input("Nome do Usuário", value=st.session_state.current_user)
    if novo_nome != st.session_state.current_user:
        st.session_state.current_user = novo_nome
        toast_message(f"Nome atualizado para {novo_nome}", "success")

    separator()

    st.markdown(f"<h3 style='color: {COLORS.text_primary};'>Preferências de Exibição</h3>",
               unsafe_allow_html=True)

    tema_opcoes = st.radio("Tema", ["Claro", "Escuro (em breve)"], horizontal=True)

    separator()

    st.markdown(f"<h3 style='color: {COLORS.text_primary};'>Dados</h3>",
               unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Exportar Dados", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento")

    with col2:
        if st.button("🔄 Resetar Dados", use_container_width=True):
            if st.checkbox("Tenho certeza que desejo resetar todos os dados", key="confirm_reset"):
                st.session_state.grains = []
                st.session_state.brewsession = []
                toast_message("Dados resetados", "warning")
                st.rerun()

    separator()

    info_box("Versão da Aplicação",
            "Mateu Barista v1.1 | Coffee Control System | Build 2024-06",
            "📌", "info")

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════

st.divider()
st.markdown(f"""
<div style='text-align: center; padding: {SPACING.xl} {SPACING.lg}; color: {COLORS.text_tertiary}; font-size: 12px;'>
    <p style='margin: 0;'>☕ Mateu Barista v1.1 | Coffee Control System</p>
    <p style='margin: {SPACING.xs} 0 0 0;'>Desenvolvido com ❤️ para baristas</p>
    <p style='margin: {SPACING.xs} 0 0 0;'>© 2024 • Todos os direitos reservados</p>
</div>
""", unsafe_allow_html=True)

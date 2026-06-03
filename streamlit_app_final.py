import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 0. CONFIGURAÇÃO DA PÁGINA
# Aplicativo: https://mateu-coffee-production.up.railway.app/
# ==============================================================================
st.set_page_config(
    page_title="Mateu Coffee Production",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
        h1, h2, h3 { font-family: 'monospace', sans-serif; font-weight: 700; color: #F3F4F6; }
        .stMetric { background-color: #1F2937; padding: 12px; border-radius: 8px; border: 1px solid #374151; }
        div[data-testid="stMetricValue"] { font-size: 20pt; font-family: 'monospace'; color: #10B981; }
        .block-kbd { background-color: #374151; padding: 2px 6px; border-radius: 4px; font-size: 9pt; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. CORE ENGINE
# ==============================================================================
class CoffeeEngine:
    @staticmethod
    def calculate_metrics(coffee_g, water_g, tds=None, time_s=0):
        if coffee_g <= 0:
            return {}

        ratio = water_g / coffee_g
        metrics = {
            "ratio_text": f"1 : {ratio:.1f}",
            "yield_pct": 0.0,
            "status": "Aguardando TDS",
            "delta_color": "off",
        }

        if tds and tds > 0:
            estimated_beverage_g = max(water_g - (2.0 * coffee_g), 0)
            ey = (estimated_beverage_g * tds) / coffee_g
            metrics["yield_pct"] = ey

            if ey < 18.0:
                metrics["status"] = "Subextraído (Under)"
                metrics["delta_color"] = "inverse"   # vermelho
            elif ey <= 22.0:
                metrics["status"] = "Ideal (Sweet Spot)"
                metrics["delta_color"] = "off"        # neutro
            else:
                metrics["status"] = "Superextraído (Over)"
                metrics["delta_color"] = "inverse"   # vermelho

        return metrics

# ==============================================================================
# 2. CACHING
# ==============================================================================
@st.cache_data(ttl=3600)
def get_coffee_wheel_data():
    return {
        "atributos": ["Doçura", "Acidez", "Corpo", "Amargor", "Finalização"],
        "ideal": [8, 7, 7, 4, 8],
    }

# ==============================================================================
# 3. GRÁFICO SENSORIAL
# ==============================================================================
def render_sensory_chart(current_profile=None):
    data = get_coffee_wheel_data()
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=data["ideal"],
        theta=data["atributos"],
        fill='toself',
        name='Target de Torra',
        line_color='#4B5563',
        opacity=0.5,
    ))

    if current_profile:
        fig.add_trace(go.Scatterpolar(
            r=current_profile,
            theta=data["atributos"],
            fill='toself',
            name='Extração Atual',
            line_color='#10B981',
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        showlegend=True,
        margin=dict(l=20, r=20, t=20, b=20),
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9CA3AF', size=11),
    )
    return fig

# ==============================================================================
# 4. INTERFACE
# ==============================================================================
def main():
    st.title("☕ MATEU COFFEE PRODUCTION")
    st.caption("Controle de Extração & Performance de Produção | Railway Pro")

    col_input, col_metrics, col_chart = st.columns([1.2, 1.2, 1.6])

    with col_input:
        st.subheader("Entradas Rápidas")
        coffee   = st.number_input("Pó de Café (g)",        min_value=5.0,  max_value=50.0,   value=18.0,  step=0.1,  help="Precisão de balança")
        water    = st.number_input("Água Alvo (g)",          min_value=50.0, max_value=1000.0, value=300.0, step=5.0)
        tds      = st.number_input("TDS Medido (%)",         min_value=0.0,  max_value=5.0,    value=1.35,  step=0.01, help="Opcional. Deixe 0 se não usar refratômetro")
        time_sec = st.number_input("Tempo de Extração (s)",  min_value=1,    max_value=600,    value=150,   step=1)

    metrics = CoffeeEngine.calculate_metrics(coffee, water, tds if tds > 0 else None, time_sec)
    ey_val = metrics.get("yield_pct", 0.0)

    with col_metrics:
        st.subheader("Análise de Extração")
        if metrics:
            st.metric(label="Brew Ratio Real", value=metrics["ratio_text"])

            ey_text = f"{ey_val:.2f} %" if ey_val > 0 else "---"
            st.metric(
                label="Extraction Yield (EY)",
                value=ey_text,
                delta=metrics["status"] if ey_val > 0 else None,
                delta_color=metrics["delta_color"],
            )

            fluxo = water / time_sec
            st.caption(f"Taxa Média de Fluxo: **{fluxo:.2f} g/s**")

    with col_chart:
        st.subheader("Perfil Sensorial")
        if ey_val < 18.0 and ey_val > 0:
            base_sensory = [4, 9, 4, 3, 5]
        elif ey_val > 22.0:
            base_sensory = [3, 4, 8, 9, 4]
        elif ey_val > 0:
            base_sensory = [9, 8, 8, 4, 9]
        else:
            base_sensory = [7, 7, 7, 5, 7]

        st.plotly_chart(render_sensory_chart(base_sensory), use_container_width=True, config={'displayModeBar': False})

if __name__ == "__main__":
    main()

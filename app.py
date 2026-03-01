import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Flash Decision Terminal", layout="wide", page_icon="🎯")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 2px solid #30363d; border-radius: 12px; padding: 20px; }
    .verdict-box { padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 25px; border: 4px solid; }
    .buy-zone { background-color: #052111; border-color: #3fb950; color: #3fb950; }
    .wait-zone { background-color: #211d05; border-color: #d29922; color: #d29922; }
    .danger-zone { background-color: #210505; border-color: #f85149; color: #f85149; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE CÁLCULO DIRECTO ---
def get_decision_metrics(df):
    # Z-Score de Precio (¿Está cara o barata respecto a su historia reciente?)
    df['MA20'] = df['Close'].rolling(20).mean()
    df['STD20'] = df['Close'].rolling(20).std()
    df['Z_Price'] = (df['Close'] - df['MA20']) / df['STD20']
    
    # Momentum (Velocidad de subida en los últimos 10 días)
    df['Momentum'] = (df['Close'] / df['Close'].shift(10) - 1) * 100
    
    # Volatilidad (Riesgo de latigazo)
    df['Returns'] = df['Close'].pct_change()
    df['Volatilidad'] = df['Returns'].rolling(20).std() * np.sqrt(252) * 100
    
    return df

@st.cache_data(ttl=300)
def load_data(ticker):
    try:
        s = yf.Ticker(ticker)
        h = s.history(period="6mo")
        return h if not h.empty else None
    except: return None

# --- 3. INTERFAZ DE DECISIÓN ---
st.title("🎯 Flash Decision: ¿Comprar o Evitar?")
ticker = st.sidebar.text_input("Introduce Ticker", "NVDA").upper()
df = load_data(ticker)

if df is not None:
    df = get_decision_metrics(df)
    current = df.iloc[-1]
    
    # --- SECCIÓN 1: EL VEREDICTO (LO QUE IMPORTA) ---
    z = current['Z_Price']
    m = current['Momentum']
    v = current['Volatilidad']
    
    # Lógica de decisión
    if z < 1.0 and m > 2.0:
        clase, titulo, desc = "buy-zone", "🚀 COMPRA: LUZ VERDE", "La acción tiene inercia alcista y no está cara estadísticamente. Buen momento para acelerar."
    elif z > 2.0:
        clase, titulo, desc = "danger-zone", "🚨 PELIGRO: RIESGO DE CAÍDA", "La acción está muy 'estirada'. Históricamente, cuando llega aquí, suele caer al pozo pronto. No entres ahora."
    elif m < 0:
        clase, titulo, desc = "wait-zone", "⚖️ ESPERA: SIN GASOLINA", "La acción está perdiendo fuerza. Tu dinero se quedará atrapado sin moverse. Busca otra con más momentum."
    else:
        clase, titulo, desc = "wait-zone", "⚖️ NEUTRAL", "El mercado está indeciso. No hay una ventaja clara para operar con apalancamiento."

    st.markdown(f"<div class='verdict-box {clase}'><h1>{titulo}</h1><h3>{desc}</h3></div>", unsafe_allow_html=True)

    # --- SECCIÓN 2: MÉTRICAS DE APOYO ---
    st.subheader("🔍 Análisis de los 3 Pilares")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Z-Score (Precio)", f"{z:.2f}", help="Indica desviaciones del precio. >2 es peligro de burbuja local.")
        st.write("**Interpretación:**")
        if z > 2: st.error("Extremadamente cara")
        elif z < -1.5: st.success("Oportunidad de rebote")
        else: st.info("Rango normal")
        

    with col2:
        st.metric("Momentum (10d)", f"{m:.1f}%", help="Velocidad del precio en las últimas 2 semanas.")
        st.write("**Interpretación:**")
        if m > 5: st.success("Fuerza brutal")
        elif m > 0: st.info("Subida constante")
        else: st.error("Perdiendo fuelle")

    with col3:
        st.metric("Volatilidad Anual", f"{v:.1f}%", help="Mide cuánto 'salta' la acción. A más volatilidad, más riesgo de que te echen del mercado.")
        st.write("**Interpretación:**")
        if v > 40: st.warning("Riesgo Alto (Latigazos)")
        else: st.success("Movimiento Sano")
        

    # --- SECCIÓN 3: GRÁFICO DE TENSIÓN ---
    st.divider()
    st.subheader("📈 Gráfico de Tensión de Precio")
    # Mostramos el precio vs su media para ver el "elástico"
    st.line_chart(df[['Close', 'MA20']].tail(50))
    st.caption("Cuando el precio (línea azul) se separa mucho de la media (línea roja), el elástico se rompe y la acción cae al pozo.")

else:
    st.error("Ticker no válido o sin datos.")

# --- SIDEBAR: CALCULADORA RÁPIDA ---
st.sidebar.divider()
st.sidebar.subheader("🧮 Calculadora de 'Fuego'")
cap = st.sidebar.number_input("Dinero disponible", value=1000)
risk = st.sidebar.slider("Riesgo (%)", 1, 10, 2)
# Stop loss automático a 2 desviaciones estándar
stop_dist = current['STD20'] * 2 if df is not None else 1
if df is not None:
    lotes = (cap * (risk/100)) / stop_dist
    st.sidebar.write(f"Compra máxima recomendada:")
    st.sidebar.code(f"{int(lotes)} acciones")

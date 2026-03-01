import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. ESTILO Y CONFIGURACIÓN ---
st.set_page_config(page_title="Decision Terminal + RoboInsights", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .metric-card { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .status-alert { padding: 20px; border-radius: 10px; font-weight: bold; text-align: center; font-size: 20px; }
    .go { border: 2px solid #3fb950; color: #3fb950; background-color: #052111; }
    .stop { border: 2px solid #f85149; color: #f85149; background-color: #210505; }
    .warn { border: 2px solid #d29922; color: #d29922; background-color: #211d05; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CÁLCULOS DE ALTA VELOCIDAD ---
def get_live_metrics(df):
    # Z-Score de Precio (Distancia a la media de 20 días)
    df['MA20'] = df['Close'].rolling(20).mean()
    df['Z_Price'] = (df['Close'] - df['MA20']) / df['Close'].rolling(20).std()
    
    # Momentum de 5 días (Aceleración pura)
    df['Mom5'] = (df['Close'] / df['Close'].shift(5) - 1) * 100
    
    # ATR % (Volatilidad relativa al precio)
    high_low = df['High'] - df['Low']
    df['ATR_Pct'] = (high_low.rolling(14).mean() / df['Close']) * 100
    
    return df

# --- 3. INTERFAZ ---
st.title("⚡ Terminal de Ejecución Rápida")
ticker = st.sidebar.text_input("Ticker", "TSLA").upper()

try:
    data = yf.Ticker(ticker).history(period="3mo")
    df = get_live_metrics(data)
    curr = df.iloc[-1]
    
    # --- SEMÁFORO DE DECISIÓN ---
    # Combinamos Z-Score (Peligro de techo) con Momentum (Gasolina)
    z = curr['Z_Price']
    m = curr['Mom5']
    v = curr['ATR_Pct']

    if z > 2.0:
        msg, style = "🚨 PELIGRO: SOBRECOMPRA. No entres, va a caer al pozo.", "stop"
    elif z < 0 and m > 1.0:
        msg, style = "🚀 MOMENTO IDEAL: Rebote con fuerza desde la media.", "go"
    elif m > 3.0:
        msg, style = "🔥 COMPRA MOMENTUM: Aceleración confirmada.", "go"
    else:
        msg, style = "⚖️ ESPERA: El mercado está lateral o sin dirección.", "warn"

    st.markdown(f"<div class='status-alert {style}'>{msg}</div>", unsafe_allow_html=True)

    # --- PANELES DE APOYO ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.subheader("📍 Posición (Z-Score)")
        st.metric("Desviación", f"{z:.2f}")
        st.caption("Si es >2, el precio está 'hinchado'. Si es < -2, está en liquidación.")
        

    with c2:
        st.subheader("🏎️ Velocidad (Momentum)")
        st.metric("Variación 5d", f"{m:.2f}%")
        st.caption("Buscamos +2% para confirmar que hay dinero entrando de verdad.")

    with c3:
        st.subheader("🌪️ Volatilidad (ATR %)")
        st.metric("Riesgo Movimiento", f"{v:.2f}%")
        st.caption("Cruza esto con RoboForex: si allí marca 'Alta', reduce tu apalancamiento.")
        

    # --- GRÁFICO DE TENSIÓN ---
    st.divider()
    st.subheader("Visualización del 'Pozo'")
    st.line_chart(df[['Close', 'MA20']].tail(40))
    st.info("💡 TIP: Si la línea azul (Precio) está muy lejos de la roja (Media), el riesgo de 'caída al pozo' aumenta por regresión a la media.")

except:
    st.error("Introduce un Ticker válido.")

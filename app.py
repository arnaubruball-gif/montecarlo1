import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Z-Diff & Z-Eff Sniper v6", layout="wide")

# Estilo para el parpadeo de alerta
st.markdown("""
    <style>
    @keyframes blinker {  50% { opacity: 0; } }
    .blink-alert {
        animation: blinker 1s linear infinite;
        background-color: #ff4b4b; color: white;
        padding: 20px; border-radius: 10px; text-align: center; font-weight: bold;
    }
    .blink-buy {
        animation: blinker 1s linear infinite;
        background-color: #00ffcc; color: black;
        padding: 20px; border-radius: 10px; text-align: center; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

ASSET_MAP = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "ORO (XAU/USD)": "GC=F",
    "S&P 500": "ES=F",
    "NASDAQ 100": "NQ=F"
}

@st.cache_data(ttl=15)
def get_institutional_data(ticker):
    try:
        df = yf.download(ticker, period='7d', interval='15m', progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # --- CÁLCULO Z-EFF (TU FÓRMULA) ---
        W = 20
        df['Spread'] = abs(df['High'] - df['Low'])
        # Protegemos el volumen para evitar divisiones por cero
        vol_ma = df['Volume'].rolling(5).mean().replace(0, np.nan).ffill().fillna(1)
        df['V_Eff'] = df['Spread'] / (vol_ma + 1e-10)
        
        v_eff_mean = df['V_Eff'].rolling(W).mean()
        v_eff_std = df['V_Eff'].rolling(W).std()
        df['Z_Eff'] = (df['V_Eff'] - v_eff_mean) / (v_eff_std + 1e-10)
        
        # --- CÁLCULO Z-DIFF (PRESIÓN) ---
        df['Ret'] = df['Close'].pct_change().fillna(0)
        df['RMF'] = (df['Close'] * df['Spread'] * 1000).fillna(0)
        diff = df['Ret'].rolling(14).sum() - df['RMF'].pct_change().rolling(14).sum()
        df['Z_Diff'] = (diff - diff.rolling(14).mean()) / (diff.rolling(14).std() + 1e-10)
        
        # VWAP para contexto visual
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * df['Volume']).rolling(30).sum() / (df['Volume'].rolling(30).sum() + 1e-10)

        return df.fillna(0)
    except: return None

# --- 2. INTERFAZ ---
st.title("🎯 Sniper V6: Divergencia Z-Diff / Z-Eff")

selected = st.selectbox("Activo:", list(ASSET_MAP.keys()))
df = get_institutional_data(ASSET_MAP[selected])

if df is not None:
    curr = df.iloc[-1]
    z_diff = float(curr['Z_Diff'])
    z_eff = float(curr['Z_Eff'])
    
    # --- LÓGICA DE DIVERGENCIA DE ABSORCIÓN ---
    # Divergencia Alcista: Presión vendedora alta (Z-Diff < -1.5) + Eficiencia muy baja (Z-Eff < -1.0)
    div_alcista = z_diff < -1.5 and z_eff < -1.0
    # Divergencia Bajista: Presión compradora alta (Z-Diff > 1.5) + Eficiencia muy baja (Z-Eff < -1.0)
    div_bajista = z_diff > 1.5 and z_eff < -1.0

    # PANEL SUPERIOR
    c1, c2, c3 = st.columns(3)
    c1.metric("Z-Diff (Presión de Flujo)", f"{z_diff:.2f}")
    c2.metric("Z-Eff (Eficiencia/Esfuerzo)", f"{z_eff:.2f}")
    
    with c3:
        if div_alcista:
            st.markdown('<div class="blink-buy">🔥 DIVERGENCIA: ABSORCIÓN COMPRA</div>', unsafe_allow_html=True)
        elif div_bajista:
            st.markdown('<div class="blink-alert">🚨 DIVERGENCIA: ABSORCIÓN VENTA</div>', unsafe_allow_html=True)
        else:
            st.info("Estado: Flujo de Mercado Normal")

    # --- GRÁFICO ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                 low=df['Low'], close=df['Close'], name="Precio"))
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='orange', width=2), name="VWAP"))

    # Anotaciones automáticas en el gráfico cuando hay divergencia
    if div_alcista:
        fig.add_annotation(x=df.index[-1], y=df['Low'].iloc[-1], text="DIVERGENCIA COMPRA",
                           showarrow=True, arrowhead=2, bgcolor="#00ffcc", font=dict(color="black"))
    if div_bajista:
        fig.add_annotation(x=df.index[-1], y=df['High'].iloc[-1], text="DIVERGENCIA VENTA",
                           showarrow=True, arrowhead=2, bgcolor="#ff4b4b", font=dict(color="white"))

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Info técnica rápida
    with st.expander("📖 Cómo leer esta Divergencia"):
        st.write("""
        **Z-Diff:** Mide quién tiene el control del flujo (positivo = compradores, negativo = vendedores).
        **Z-Eff:** Mide cuánto se mueve el precio por cada unidad de volumen (negativo = el volumen no mueve el precio).
        
        **DIVERGENCIA:** Ocurre cuando el Z-Diff es extremo pero el Z-Eff es bajo. 
        Esto indica que el 'Esfuerzo' (volumen) no está dando 'Resultado' (precio), señal clara de que una institución está absorbiendo la liquidez para girar el mercado.
        """)

else:
    st.error("Esperando conexión con el mercado...")

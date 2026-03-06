import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Z-Sniper v8: Indicator History", layout="wide")

st.markdown("""
    <style>
    @keyframes blinker { 50% { opacity: 0; } }
    .blink-buy { animation: blinker 1s linear infinite; background-color: #00ffcc; color: black; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; }
    .blink-sell { animation: blinker 1s linear infinite; background-color: #ff4b4b; color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; }
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
def get_data(ticker):
    try:
        df = yf.download(ticker, period='5d', interval='15m', progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # CÁLCULOS Z-EFF
        W = 20
        df['Spread'] = abs(df['High'] - df['Low'])
        vol_ma = df['Volume'].rolling(5).mean().replace(0, np.nan).ffill().fillna(1)
        df['V_Eff'] = df['Spread'] / (vol_ma + 1e-10)
        df['Z_Eff'] = (df['V_Eff'] - df['V_Eff'].rolling(W).mean()) / (df['V_Eff'].rolling(W).std() + 1e-10)
        
        # CÁLCULOS Z-DIFF
        df['Ret'] = df['Close'].pct_change().fillna(0)
        df['RMF'] = (df['Close'] * df['Spread'] * 1000).fillna(0)
        diff = df['Ret'].rolling(14).sum() - df['RMF'].pct_change().rolling(14).sum()
        df['Z_Diff'] = (diff - diff.rolling(14).mean()) / (diff.rolling(14).std() + 1e-10)
        
        # VWAP
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * df['Volume']).rolling(30).sum() / (df['Volume'].rolling(30).sum() + 1e-10)
        
        return df.fillna(0)
    except: return None

# --- 2. INTERFAZ ---
st.title("🏹 Z-Sniper v8: Monitor de Absorción")

selected_label = st.sidebar.selectbox("Activo:", list(ASSET_MAP.keys()))
df = get_data(ASSET_MAP[selected_label])

if df is not None:
    curr = df.iloc[-1]
    z_d, z_e = float(curr['Z_Diff']), float(curr['Z_Eff'])
    
    # PANEL DE ALERTAS
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Z-Diff Actual", f"{z_d:.2f}")
    c2.metric("Z-Eff Actual", f"{z_e:.2f}")
    
    with c3:
        if z_d < -1.5 and z_e < -1.0:
            st.markdown('<div class="blink-buy">🔥 ABSORCIÓN COMPRA</div>', unsafe_allow_html=True)
        elif z_d > 1.5 and z_e < -1.0:
            st.markdown('<div class="blink-sell">🚨 ABSORCIÓN VENTA</div>', unsafe_allow_html=True)
        else:
            st.info("Buscando anomalías de flujo institucional...")

    # --- GRÁFICO 1: PRECIO ---
    fig_p = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="M15")])
    fig_p.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='orange', width=2), name="VWAP"))
    fig_p.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, title="Gráfico Operativo 15m")
    st.plotly_chart(fig_p, use_container_width=True)

    # --- GRÁFICO 2: HISTÓRICO DE INDICADORES (SUBPLOTS) ---
    st.subheader("📊 Historial de Flujo y Eficiencia")
    
    fig_ind = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=("Presión de Flujo (Z-Diff)", "Eficiencia de Volumen (Z-Eff)"))
    
    # Z-Diff History
    fig_ind.add_trace(go.Scatter(x=df.index, y=df['Z_Diff'], name="Z-Diff", fill='tozeroy', line=dict(color='#00d4ff')), row=1, col=1)
    fig_ind.add_hline(y=1.5, line_dash="dash", line_color="red", row=1, col=1)
    fig_ind.add_hline(y=-1.5, line_dash="dash", line_color="green", row=1, col=1)
    
    # Z-Eff History
    fig_ind.add_trace(go.Scatter(x=df.index, y=df['Z_Eff'], name="Z-Eff", fill='tozeroy', line=dict(color='#ffcc00')), row=2, col=1)
    fig_ind.add_hline(y=-1.0, line_dash="dot", line_color="white", row=2, col=1)
    
    fig_ind.update_layout(template="plotly_dark", height=500, showlegend=False)
    st.plotly_chart(fig_ind, use_container_width=True)

else:
    st.error("Esperando datos del mercado...")

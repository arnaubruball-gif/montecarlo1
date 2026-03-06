import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Z-Diff Sniper v4", layout="wide")

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
        df = yf.download(ticker, period='5d', interval='15m', progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # VWAP y Bandas
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * df['Volume']).rolling(30).sum() / df['Volume'].rolling(30).sum()
        std = tp.rolling(30).std()
        df['Up'] = df['VWAP'] + (std * 2)
        df['Low'] = df['VWAP'] - (std * 2)

        # Z-DIFF
        df['Ret'] = df['Close'].pct_change()
        df['RMF'] = df['Close'] * (df['High'] - df['Low']) * 1000
        diff = df['Ret'].rolling(14).sum() - df['RMF'].pct_change().rolling(14).sum()
        df['Z_Diff'] = (diff - diff.rolling(14).mean()) / (diff.rolling(14).std() + 1e-10)
        
        # VOLUMEN RELATIVO (Para Absorción)
        df['Rel_Vol'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        return df
    except: return None

# --- 2. INTERFAZ ---
st.title("🎯 Sniper V4: Detector de Absorción Institucional")

selected = st.selectbox("Selecciona Activo:", list(ASSET_MAP.keys()))
df = get_institutional_data(ASSET_MAP[selected])

if df is not None:
    curr = df.iloc[-1]
    z_val = float(curr['Z_Diff'])
    rvol = float(curr['Rel_Vol'])
    
    # --- LÓGICA DE ABSORCIÓN ---
    # Absorción de Venta: Precio en banda baja + Z-Diff negativo + Volumen alto
    abs_compra = curr['Close'] <= curr['Low'] and z_val < -1.5 and rvol > 1.3
    # Absorción de Compra: Precio en banda alta + Z-Diff positivo + Volumen alto
    abs_venta = curr['Close'] >= curr['Up'] and z_val > 1.5 and rvol > 1.3

    # PANEL DE MÉTRICAS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precio Actual", f"{curr['Close']:.5f}")
    m2.metric("Z-Diff (Presión)", f"{z_val:.2f}")
    m3.metric("Volumen Relativo", f"{rvol:.2f}x")
    
    # Status de Absorción
    if abs_compra:
        m4.markdown("<div style='background-color:#00ffcc; color:black; padding:10px; border-radius:5px; text-align:center;'><b>🔥 ABSORCIÓN COMPRADORA</b></div>", unsafe_allow_html=True)
    elif abs_venta:
        m4.markdown("<div style='background-color:#ff4b4b; color:white; padding:10px; border-radius:5px; text-align:center;'><b>⚠️ ABSORCIÓN VENDEDORA</b></div>", unsafe_allow_html=True)
    else:
        m4.markdown("<div style='background-color:#333; color:white; padding:10px; border-radius:5px; text-align:center;'>Sin Absorción Clara</div>", unsafe_allow_html=True)

    # --- GRÁFICO PRINCIPAL ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"))
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='orange', width=2), name="VWAP"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Up'], line=dict(color='rgba(255,255,255,0.2)', dash='dot'), name="Liquidez +2"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Low'], line=dict(color='rgba(255,255,255,0.2)', dash='dot'), name="Liquidez -2"))

    # Anotaciones de Señales en el gráfico
    if abs_compra:
        fig.add_annotation(x=df.index[-1], y=df['Low'].iloc[-1], text="ABS COMPRA", showarrow=True, arrowhead=1, bgcolor="#00ffcc")
    if abs_venta:
        fig.add_annotation(x=df.index[-1], y=df['Up'].iloc[-1], text="ABS VENTA", showarrow=True, arrowhead=1, bgcolor="#ff4b4b")

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Mini Tabla de Auditoría
    st.write("**Historial de Presión (Últimas 5 velas M15):**")
    st.dataframe(df[['Close', 'Z_Diff', 'Rel_Vol']].tail(5).style.background_gradient(cmap='RdYlGn', subset=['Z_Diff']))

else:
    st.error("No se han podido cargar los datos. Revisa la conexión con Yahoo Finance.")

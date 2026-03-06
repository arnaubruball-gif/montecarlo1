import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Z-Diff Sniper v5", layout="wide")

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
        # Descargamos un poco más de datos (10 días) para asegurar que el Z-Diff no salga NaN
        df = yf.download(ticker, period='10d', interval='15m', progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # Rellenar huecos de volumen para evitar NaNs en Forex
        df['Volume'] = df['Volume'].replace(0, np.nan).ffill().fillna(1)

        # VWAP y Bandas (Ventana de 30)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * df['Volume']).rolling(30).sum() / df['Volume'].rolling(30).sum()
        std = tp.rolling(30).std()
        df['Up'] = df['VWAP'] + (std * 2)
        df['Low'] = df['VWAP'] - (std * 2)

        # Z-DIFF (Limpieza de NaN)
        df['Ret'] = df['Close'].pct_change().fillna(0)
        df['RMF'] = (df['Close'] * (df['High'] - df['Low']) * 1000).fillna(0)
        
        diff = df['Ret'].rolling(14).sum() - df['RMF'].pct_change().rolling(14).sum()
        z_mean = diff.rolling(14).mean()
        z_std = diff.rolling(14).std()
        
        # Fórmula Z-Score protegida contra división por cero
        df['Z_Diff'] = (diff - z_mean) / (z_std + 1e-10)
        df['Z_Diff'] = df['Z_Diff'].fillna(0) # Elimina los NaNs finales
        
        # VOLUMEN RELATIVO
        df['Rel_Vol'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        return df
    except Exception as e:
        return None

# --- 2. INTERFAZ ---
st.title("🎯 Sniper V5: Absorción de Volumen & Z-Diff")

selected = st.selectbox("Activo:", list(ASSET_MAP.keys()))
df = get_institutional_data(ASSET_MAP[selected])

if df is not None and not df.empty:
    curr = df.iloc[-1]
    z_val = float(curr['Z_Diff'])
    rvol = float(curr['Rel_Vol'])
    
    # --- DETECTOR DE ABSORCIÓN ---
    # Una absorción real necesita: Precio en extremo + Z-Diff saturado + Volumen superior al promedio
    abs_compra = curr['Close'] <= (curr['Low'] * 1.0005) and z_val < -1.2 and rvol > 1.2
    abs_venta = curr['Close'] >= (curr['Up'] * 0.9995) and z_val > 1.2 and rvol > 1.2

    # --- PANEL DE CONTROL (RADAR) ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Presión Z-Diff", f"{z_val:.2f}")
        if z_val > 1.5: st.error("🔥 Sobrecompra Extrema")
        elif z_val < -1.5: st.success("❄️ Sobreventa Extrema")
        else: st.info("⚖️ Flujo Neutral")

    with c2:
        st.metric("Actividad Vol (RVOL)", f"{rvol:.2f}x")
        if rvol > 1.5: st.warning("🐋 Actividad Institucional Alta")
        else: st.write("Volumen Normal")

    with c3:
        st.write("**ESTADO DE ABSORCIÓN**")
        if abs_compra:
            st.markdown("<h2 style='color:#00ffcc; border:2px solid #00ffcc; text-align:center;'>ABSORCIÓN COMPRA</h2>", unsafe_allow_html=True)
            st.caption("Instituciones están aguantando el precio en soporte.")
        elif abs_venta:
            st.markdown("<h2 style='color:#ff4b4b; border:2px solid #ff4b4b; text-align:center;'>ABSORCIÓN VENTA</h2>", unsafe_allow_html=True)
            st.caption("Instituciones están frenando la subida en resistencia.")
        else:
            st.markdown("<h2 style='color:#555; text-align:center;'>SIN SEÑAL</h2>", unsafe_allow_html=True)

    # --- GRÁFICO ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"))
    
    # VWAP y Bandas
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='orange', width=2), name="VWAP"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Up'], line=dict(color='rgba(255,0,0,0.2)', dash='dot'), name="Resistencia Liquidez"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Low'], line=dict(color='rgba(0,255,0,0.2)', dash='dot'), name="Soporte Liquidez"))

    # Señal Visual de Absorción
    if abs_compra:
        fig.add_annotation(x=df.index[-1], y=df['Low'].iloc[-1], text="ENTRY BUY", showarrow=True, arrowhead=2, bgcolor="#00ffcc")
    if abs_venta:
        fig.add_annotation(x=df.index[-1], y=df['Up'].iloc[-1], text="ENTRY SELL", showarrow=True, arrowhead=2, bgcolor="#ff4b4b")

    fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Esperando datos... Si el error persiste, el mercado podría estar cerrado o la API saturada.")

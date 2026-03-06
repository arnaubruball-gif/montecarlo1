import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Z-Diff Live Sniper", layout="wide")

# Tickers 24/5 (Forex, Oro, Índices)
ASSET_MAP = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "ORO (XAU/USD)": "GC=F",
    "S&P 500": "ES=F",
    "NASDAQ 100": "NQ=F"
}

# --- 2. MOTOR DE DATOS (SIN CACHÉ LARGO PARA EVITAR LAG) ---
@st.cache_data(ttl=10) # Solo 10 segundos de memoria para scalping real
def get_live_data(ticker):
    try:
        # Descargamos los últimos 5 días en M15
        # 'auto_adjust=True' ayuda a que los precios sean más precisos
        data = yf.download(ticker, period='5d', interval='15m', progress=False, auto_adjust=True)
        
        if data.empty: return None
        
        # Limpieza de columnas MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            df = data.copy()
            df.columns = df.columns.get_level_values(0)
        else:
            df = data

        # --- INDICADORES ---
        # VWAP Rodante (Fuerza del precio medio)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * df['Volume']).rolling(30).sum() / df['Volume'].rolling(30).sum()
        
        # Bandas de Desviación
        std = tp.rolling(30).std()
        df['Up'] = df['VWAP'] + (std * 2)
        df['Low'] = df['VWAP'] - (std * 2)

        # Z-DIFF (Cálculo Escalar para evitar errores de 18:30)
        df['Ret'] = df['Close'].pct_change()
        df['RMF'] = df['Close'] * (df['High'] - df['Low']) * 1000
        diff = df['Ret'].rolling(14).sum() - df['RMF'].pct_change().rolling(14).sum()
        df['Z_Diff'] = (diff - diff.rolling(14).mean()) / (diff.rolling(14).std() + 1e-10)
        
        return df
    except:
        return None

# --- 3. INTERFAZ ---
st.title("🏹 Sniper Z-Diff M15 (Live Update)")

col_sel, col_status = st.columns([2, 1])
with col_sel:
    selected = st.selectbox("Activo:", list(ASSET_MAP.keys()))

# Botón de refresco manual por si la API se duerme
if st.button("🔄 FORZAR ACTUALIZACIÓN"):
    st.cache_data.clear()

df = get_live_data(ASSET_MAP[selected])

if df is not None:
    # --- CHEQUEO DE TIEMPO REAL ---
    ultima_vela = df.index[-1]
    ahora = datetime.now()
    # Si la última vela es de hace más de 30 min, avisamos
    es_antiguo = (ahora - ultima_vela.replace(tzinfo=None)) > timedelta(minutes=30)
    
    with col_status:
        if es_antiguo:
            st.error(f"⚠️ DATOS RETRASADOS: Última vela a las {ultima_vela.strftime('%H:%M')}")
        else:
            st.success(f"✅ EN VIVO: Datos de las {ultima_vela.strftime('%H:%M')}")

    # --- PANEL DE MÉTRICAS ---
    curr = df.iloc[-1]
    z_val = float(curr['Z_Diff'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Precio", f"{curr['Close']:.5f}")
    m2.metric("Z-Diff", f"{z_val:.2f}")
    
    # Lógica de Señal
    if curr['Close'] < curr['Low'] and z_val < -1.5:
        m3.markdown("<h2 style='color:#00ffcc;'>🟢 COMPRA</h2>", unsafe_allow_html=True)
    elif curr['Close'] > curr['Up'] and z_val > 1.5:
        m3.markdown("<h2 style='color:#ff4b4b;'>🚨 VENTA</h2>", unsafe_allow_html=True)
    else:
        m3.markdown("<h2>⚪ NEUTRAL</h2>", unsafe_allow_html=True)

    # --- GRÁFICO ---
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Precio"))
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='orange', width=1.5), name="VWAP"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Up'], line=dict(color='gray', dash='dot'), name="Liquidez +"))
    fig.add_trace(go.Scatter(x=df.index, y=df['Low'], line=dict(color='gray', dash='dot'), name="Liquidez -"))
    
    fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico Z-Diff
    fig_z = go.Figure(go.Scatter(x=df.index, y=df['Z_Diff'], fill='tozeroy', line=dict(color='cyan')))
    fig_z.add_hline(y=1.5, line_color="red", line_dash="dash")
    fig_z.add_hline(y=-1.5, line_color="green", line_dash="dash")
    fig_z.update_layout(template="plotly_dark", height=200, title="Oscilador de Presión Institucional")
    st.plotly_chart(fig_z, use_container_width=True)

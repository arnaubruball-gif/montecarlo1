import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Z-Diff Sniper 24/5", layout="wide")

# Mapeo de Activos para máxima liquidez 24h
ASSET_MAP = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "ORO (XAU/USD)": "GC=F",
    "S&P 500 (Futuros)": "ES=F",
    "NASDAQ 100 (Futuros)": "NQ=F"
}

# --- MOTOR DE CÁLCULO ---
def get_institutional_data(ticker):
    # Descargamos 7 días para tener suficiente histórico de VWAP
    df = yf.download(ticker, period='7d', interval='15m', progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

    # 1. VWAP RODANTE (Ideal para mercados 24/5)
    window_vwap = 40 # Aproximadamente 10 horas de trading
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * df['Volume']).rolling(window_vwap).sum() / df['Volume'].rolling(window_vwap).sum()
    
    # 2. BANDAS DE DESVIACIÓN (Liquidez)
    std_dev = tp.rolling(window_vwap).std()
    df['Upper_2'] = df['VWAP'] + (std_dev * 2)
    df['Lower_2'] = df['VWAP'] - (std_dev * 2)

    # 3. Z-DIFF (Fuerza del Flujo)
    df['Ret'] = df['Close'].pct_change()
    df['RMF'] = df['Close'] * (df['High'] - df['Low']) * 1000
    z_win = 14
    diff = df['Ret'].rolling(z_win).sum() - df['RMF'].pct_change().rolling(z_win).sum()
    df['Z_Diff'] = (diff - diff.rolling(z_win).mean()) / (diff.rolling(z_win).std() + 1e-10)
    
    # 4. FILTRO DE COMBUSTIBLE (Volumen Relativo)
    df['Rel_Vol'] = df['Volume'] / df['Volume'].rolling(20).mean()
    
    return df

# --- INTERFAZ ---
st.title("🏹 Sniper Z-Diff M15 | Forex, Oro e Índices")
selected_label = st.selectbox("Selecciona Activo:", list(ASSET_MAP.keys()))
ticker = ASSET_MAP[selected_label]

data = get_institutional_data(ticker)

if data is not None:
    current = data.iloc[-1]
    
    # PANEL DE CONTROL
    col1, col2, col3, col4 = st.columns(4)
    
    # Lógica de Señal Pro
    signal = "⚪ ESPERANDO"
    color = "white"
    
    # Condición Compra: Precio < Banda Inferior + Z-Diff < -1.8 + Volumen Alto
    if current['Close'] < current['Lower_2'] and current['Z_Diff'] < -1.5:
        signal = "🟢 COMPRA (REVERSIÓN)"
        color = "#00ffcc"
    # Condición Venta: Precio > Banda Superior + Z-Diff > 1.8 + Volumen Alto
    elif current['Close'] > current['Upper_2'] and current['Z_Diff'] > 1.5:
        signal = "🚨 VENTA (DISTRIBUCIÓN)"
        color = "#ff4b4b"

    col1.metric("Precio", f"{current['Close']:.2f}")
    col2.metric("Z-Diff", f"{current['Z_Diff']:.2f}")
    col3.metric("Vol. Relativo", f"{current['Rel_Vol']:.2f}x")
    col4.markdown(f"<h2 style='color:{color};'>{signal}</h2>", unsafe_allow_html=True)

    # GRÁFICO PRINCIPAL
    fig = go.Figure()
    # Velas
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                 low=data['Low'], close=data['Close'], name="Precio"))
    # VWAP y Liquidez
    fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='orange', width=2), name="VWAP"))
    fig.add_trace(go.Scatter(x=data.index, y=data['Upper_2'], line=dict(color='rgba(255,255,255,0.2)', dash='dot'), name="Banda Liquidez +2"))
    fig.add_trace(go.Scatter(x=data.index, y=data['Lower_2'], line=dict(color='rgba(255,255,255,0.2)', dash='dot'), name="Banda Liquidez -2"))

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False,
                      margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # OSCILADOR Z-DIFF
    fig_z = go.Figure()
    fig_z.add_trace(go.Scatter(x=data.index, y=data['Z_Diff'], line=dict(color='cyan'), fill='tozeroy'))
    fig_z.add_hline(y=1.5, line_dash="dash", line_color="red")
    fig_z.add_hline(y=-1.5, line_dash="dash", line_color="green")
    fig_z.update_layout(template="plotly_dark", height=250, title="Oscilador de Flujo Institucional (Z-Diff)")
    st.plotly_chart(fig_z, use_container_width=True)

    st.info("""
    **Guía de Scalping:**
    1. Busca que el precio toque las bandas punteadas (zonas de liquidez).
    2. El Z-Diff debe estar en extremos (Rojo para vender, Verde para comprar).
    3. Si el Volumen Relativo es > 1.5x, la señal tiene mucha más fuerza.
    """)

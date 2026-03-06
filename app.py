import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Z-Diff M15 Scalper", layout="wide")

# --- MOTOR DE CÁLCULO ---
def get_scalping_data(ticker):
    # Descargamos 5 días de datos en M15 para tener contexto
    df = yf.download(ticker, period='5d', interval='15m', progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

    # 1. VWAP Cálculo (Acumulado diario)
    df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VP'] = df['Typical_Price'] * df['Volume']
    
    # Agrupamos por día para resetear la VWAP
    df['Date'] = df.index.date
    df['VWAP'] = df.groupby('Date')['VP'].cumsum() / df.groupby('Date')['Volume'].cumsum()
    
    # 2. Bandas de Desviación (Liquidez Institucional)
    df['VWAP_Std'] = df.groupby('Date')['Typical_Price'].transform(lambda x: x.expanding().std())
    df['Upper_Band'] = df['VWAP'] + (2 * df['VWAP_Std'])
    df['Lower_Band'] = df['VWAP'] - (2 * df['VWAP_Std'])

    # 3. Z-DIFF (Retorno vs Flujo de Dinero)
    df['Ret'] = df['Close'].pct_change()
    df['RMF'] = df['Close'] * (df['High'] - df['Low']) * 1000 # Proxy de flujo
    
    window = 14
    diff = df['Ret'].rolling(window).sum() - df['RMF'].pct_change().rolling(window).sum()
    df['Z_Diff'] = (diff - diff.rolling(window).mean()) / (diff.rolling(window).std() + 1e-10)
    
    return df

# --- INTERFAZ ---
st.title("⚡ M15 Institutional Scalper")
ticker = st.text_input("Símbolo (ej: SPY, QQQ, BTC-USD)", "SPY")

data = get_scalping_data(ticker)

if data is not None:
    last_row = data.iloc[-1]
    
    # Dashboard de Métricas
    c1, c2, c3 = st.columns(3)
    z_val = float(last_row['Z_Diff'])
    
    # Lógica de Señal
    # COMPRA: Precio bajo VWAP + Z-Diff < -1.5 (Agotamiento de ventas)
    # VENTA: Precio sobre VWAP + Z-Diff > 1.5 (Agotamiento de compras)
    status = "⚪ NEUTRAL"
    if last_row['Close'] < last_row['VWAP'] and z_val < -1.5:
        status = "🟢 SEÑAL DE COMPRA (Reversión a VWAP)"
    elif last_row['Close'] > last_row['VWAP'] and z_val > 1.5:
        status = "🚨 SEÑAL DE VENTA (Reversión a VWAP)"

    c1.metric("Precio Actual", f"{last_row['Close']:.2f}")
    c2.metric("Z-Diff (14p)", f"{z_val:.2f}")
    c3.subheader(status)

    # Gráfico Profesional
    fig = go.Figure()

    # Velas
    fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                 low=data['Low'], close=data['Close'], name="Precio"))

    # VWAP y Bandas
    fig.add_trace(go.Scatter(x=data.index, y=data['VWAP'], line=dict(color='orange', width=2), name="VWAP"))
    fig.add_trace(go.Scatter(x=data.index, y=data['Upper_Band'], line=dict(color='gray', dash='dot'), name="+2 Std"))
    fig.add_trace(go.Scatter(x=data.index, y=data['Lower_Band'], line=dict(color='gray', dash='dot'), name="-2 Std"))

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico de Z-Diff inferior
    fig_z = go.Figure()
    fig_z.add_trace(go.Scatter(x=data.index, y=data['Z_Diff'], line=dict(color='cyan')))
    fig_z.add_hline(y=1.5, line_dash="dash", line_color="red")
    fig_z.add_hline(y=-1.5, line_dash="dash", line_color="green")
    fig_z.update_layout(template="plotly_dark", height=200, title="Z-Diff Oscillator")
    st.plotly_chart(fig_z, use_container_width=True)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from datetime import datetime, timedelta
import json

# ─── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="OrderFlow PRO | Quant Dashboard", layout="wide")

# Estilo CSS para apariencia "Terminal Bloomberg / Dark Quant"
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; }
    .stMetric { background: #0e1117; border: 1px solid #1e293b; padding: 15px; border-radius: 5px; }
    .reportview-container { background: #04070d; }
</style>
""", unsafe_allow_html=True)

# ─── MOTOR DE DATOS (CONECTOR PROFESIONAL) ────────────────────────────────────

def get_data_pro(api_key, provider, symbol, timeframe="4h", limit=100):
    """Descarga datos usando APIs oficiales para evitar bloqueos legales."""
    try:
        if provider == "Polygon.io":
            from polygon import RESTClient
            client = RESTClient(api_key)
            # Mapeo: 4h en Polygon es multiplier=4, timespan="hour"
            aggs = client.get_aggs(ticker=symbol, multiplier=4, timespan="hour", 
                                   from_="2025-01-01", to="2026-12-31", limit=limit)
            df = pd.DataFrame(aggs)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.rename(columns={'o':'Open','h':'High','l':'Low','c':'Close','v':'Volume'})
            return df
            
        elif provider == "Alpha Vantage":
            from alpha_vantage.timeseries import TimeSeries
            ts = TimeSeries(key=api_key, output_format='pandas')
            # AV no tiene 4h nativo, bajamos 60min y resampleamos
            data, _ = ts.get_intraday(symbol=symbol, interval='60min', outputsize='full')
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            df = data.resample('4H').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
            return df.tail(limit)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# ─── LÓGICA CUANTITATIVA AVANZADA ──────────────────────────────────────────────

def calc_quant_metrics(df):
    # 1. Z-Diff (Flujo Institucional Relativo)
    df['returns'] = df['Close'].pct_change()
    df['vol_pct'] = df['Volume'] * df['returns']
    mu = df['vol_pct'].rolling(14).mean()
    std = df['vol_pct'].rolling(14).std()
    df['z_flow'] = (df['vol_pct'] - mu) / std

    # 2. Monte Carlo (Proyección Estadística)
    last_price = df['Close'].iloc[-1]
    returns = df['returns'].dropna()
    sims = 1000
    days = 5  # Proyectar a 5 velas (20h en H4)
    
    # Simulación GBM (Geometric Brownian Motion)
    drift = returns.mean()
    vol = returns.std()
    rand_walk = np.exp((drift - 0.5 * vol**2) + vol * np.random.standard_normal((sims, days)))
    paths = np.zeros_like(rand_walk)
    paths[:, 0] = last_price
    for t in range(1, days):
        paths[:, t] = paths[:, t-1] * rand_walk[:, t]
    
    # 3. Markov (Probabilidad de Estado)
    # Definimos estados: -1 (Bajista), 0 (Neutral), 1 (Alcista)
    bins = [-np.inf, -0.002, 0.002, np.inf]
    df['state'] = pd.cut(df['returns'], bins=bins, labels=[-1, 0, 1])
    # Matriz de transición simplificada (P de que el siguiente sea Alcista dado el actual)
    current_state = df['state'].iloc[-1]
    next_state_probs = df.groupby('state')['state'].shift(-1).value_counts(normalize=True).loc[current_state]
    
    return df, paths, next_state_probs

# ─── INTERFAZ DE USUARIO (SIDEBAR) ─────────────────────────────────────────────

with st.sidebar:
    st.title("📊 OrderFlow PRO")
    st.subheader("Configuración de Datos")
    
    provider = st.selectbox("API Provider", ["Polygon.io", "Alpha Vantage"])
    api_key = st.text_input(f"Introduce tu API Key de {provider}", type="password")
    
    st.divider()
    
    symbol = st.text_input("Símbolo (Ej: AAPL, C:EURUSD, X:BTCUSD)", value="C:EURUSD")
    n_candles = st.slider("Velas de análisis", 50, 500, 100)
    
    btn_run = st.button("EJECUTAR MODELOS", type="primary")
    
    st.info("💡 Este software requiere tu propia API Key (disponible gratis en polygon.io o alphavantage.co)")

# ─── DASHBOARD PRINCIPAL ──────────────────────────────────────────────────────

if btn_run and api_key:
    df = get_data_pro(api_key, provider, symbol, limit=n_candles)
    
    if df is not None:
        df, paths, markov_probs = calc_quant_metrics(df)
        
        # COLUMNAS DE MÉTRICAS (KPIs)
        k1, k2, k3, k4 = st.columns(4)
        last_p = df['Close'].iloc[-1]
        z_val = df['z_flow'].iloc[-1]
        
        k1.metric("Precio Actual", f"{last_p:,.4f}")
        k2.metric("Z-Flow (OrderFlow)", f"{z_val:.2f}", delta="Institucional" if z_val > 1.5 else "Retail")
        
        # Probabilidad de subida basada en Monte Carlo
        prob_up = (paths[:, -1] > last_p).mean() * 100
        k3.metric("Prob. Alcista (MC)", f"{prob_up:.1f}%")
        
        # Estado Markov
        k4.metric("Prob. Continuidad", f"{markov_probs.max()*100:.1f}%")

        # GRÁFICO MAESTRO
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05, row_heights=[0.7, 0.3])

        # Velas Japonesas
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                     low=df['Low'], close=df['Close'], name="Precio"), row=1, col=1)

        # Proyección Monte Carlo (Capa visual)
        for i in range(10): # Dibujar 10 rutas aleatorias
            fig.add_trace(go.Scatter(x=[df.index[-1] + timedelta(hours=4*t) for t in range(5)], 
                                     y=paths[i, :], mode='lines', 
                                     line=dict(width=1, color='rgba(0, 255, 255, 0.2)'),
                                     showlegend=False), row=1, col=1)

        # Z-Flow Histograma
        colors = ['red' if x < 0 else 'green' for x in df['z_flow']]
        fig.add_trace(go.Bar(x=df.index, y=df['z_flow'], marker_color=colors, name="Z-Flow"), row=2, col=1)

        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # SECCIÓN DE ANÁLISIS TÉCNICO-CUANTITATIVO
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🎯 Proyección de Precios (5 velas)")
            st.write(f"Percentil 95% (Techo): {np.percentile(paths[:, -1], 95):,.4f}")
            st.write(f"Mediana Esperada: {np.median(paths[:, -1]):,.4f}")
            st.write(f"Percentil 5% (Suelo): {np.percentile(paths[:, -1], 5):,.4f}")
        
        with c2:
            st.subheader("⛓️ Probabilidades de Markov")
            st.write(f"Prob. de Reversión: {1 - markov_probs.max():.2%}")
            st.write("Estado actual del mercado:", "SOBRECOMPRA" if z_val > 2 else "ESTABLE" if z_val > -2 else "CAPITULACIÓN")

    else:
        st.error("No se pudieron obtener datos. Verifica tu API Key y el Símbolo.")
else:
    st.warning("👈 Por favor, introduce tu API Key y haz clic en Ejecutar.")

# ─── FOOTER LEGAL ─────────────────────────────────────────────────────────────
st.divider()
st.caption("Aviso Legal: Este software es una herramienta de análisis estadístico. No constituye asesoría financiera. El uso de APIs de terceros está sujeto a los términos de servicio de Polygon.io o Alpha Vantage.")

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Halcón 4.0 Pro: Fractal & Volume", layout="wide", page_icon="🦅")

# --- 2. FUNCIONES MATEMÁTICAS ---

def calcular_hurst(ts):
    if len(ts) < 30: return 0.5
    lags = range(2, 20)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

@st.cache_data(ttl=600)
def fetch_and_calculate(tickers):
    results = []
    for ticker in tickers:
        df_hist = pd.DataFrame()
        # Sistema de reintentos (3 oportunidades por ticker)
        for intento in range(3):
            try:
                df_hist = yf.download(ticker, period="70d", interval="1d", progress=False, timeout=10)
                if not df_hist.empty:
                    break
                time.sleep(1) # Espera un segundo antes de reintentar
            except Exception:
                time.sleep(1)
        
        if not df_hist.empty:
            try:
                # Limpieza de Multi-index
                if isinstance(df_hist.columns, pd.MultiIndex):
                    df_hist.columns = df_hist.columns.get_level_values(0)
                df_hist = df_hist.dropna()

                if len(df_hist) > 40:
                    prices = df_hist['Close'].values.flatten().astype(float)
                    volumes = df_hist['Volume'].values.flatten().astype(float)
                    
                    # --- MÉTRICAS ---
                    window = prices[-40:]
                    ma40 = np.mean(window)
                    std40 = np.std(window)
                    z_diff = (prices[-1] - ma40) / std40 if std40 != 0 else 0
                    
                    # R-Squared
                    x = np.arange(len(window))
                    coeffs = np.polyfit(x, window, 1)
                    y_hat = np.poly1d(coeffs)(x)
                    r2 = 1 - (np.sum((window - y_hat)**2) / np.sum((window - np.mean(window))**2))
                    
                    hurst = calcular_hurst(prices[-50:])
                    
                    vol_avg = np.mean(volumes[-20:])
                    vol_rel = volumes[-1] / vol_avg if vol_avg > 0 else 1
                    volatilidad = np.std(np.diff(prices[-20:]) / prices[-21:-1])

                    results.append({
                        'Ticker': ticker, 'Precio': round(prices[-1], 4),
                        'Z-Diff': round(z_diff, 2), 'R2': round(r2, 3),
                        'Hurst': round(hurst, 2), 'Vol_Rel': round(vol_rel, 2),
                        'Volatilidad': volatilidad, 'MA40': ma40
                    })
            except: continue
    return pd.DataFrame(results)

# --- 3. INTERFAZ ---
st.title("🦅 Halcón 4.0: Terminal Fractal Pro")

assets = [
    'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'NZDUSD=X', 
    'USDCAD=X', 'USDCHF=X', 'BTC-USD', 'GC=F', 'ES=F'
]

if st.button('🔄 Forzar Actualización de Radar'):
    st.cache_data.clear()

with st.spinner('Cazando datos... (esto puede tardar por los reintentos)'):
    df = fetch_and_calculate(assets)

if df.empty:
    st.warning("⚠️ Los servidores de datos están saturados. Haz clic en el botón de arriba para reintentar.")
    st.stop()

# Score Halcón
df['Score_Halcon'] = (abs(df['Z-Diff']) * (1 - df['Hurst']) / (df['Vol_Rel'] + 0.1)).round(2)
df = df.sort_values(by='Score_Halcon', ascending=False)

# --- 4. VISUALIZACIÓN ---
c1, c2 = st.columns(2)
with c1:
    st.subheader("📊 Matriz de Oportunidad")
    st.dataframe(df.style.background_gradient(subset=['Score_Halcon'], cmap='YlOrRd'), use_container_width=True)

with c2:
    st.subheader("🎯 Radar Fractal")
    fig = px.scatter(df, x="Z-Diff", y="Hurst", size="Vol_Rel", text="Ticker", 
                     color="Score_Halcon", color_continuous_scale="Viridis")
    fig.add_hline(y=0.5, line_dash="dash", line_color="white")
    st.plotly_chart(fig, use_container_width=True)

# --- 5. MONTECARLO ---
st.divider()
target = st.selectbox("Activo para Deep Dive:", df['Ticker'])
d = df[df['Ticker'] == target].iloc[0]

ca, cb = st.columns([1, 2])
with ca:
    st.metric("Hurst (Fractalidad)", d['Hurst'], delta="REVERSIÓN" if d['Hurst'] < 0.5 else "TENDENCIA", delta_color="inverse")
    st.metric("Volumen Relativo", d['Vol_Rel'])
    if d['Hurst'] < 0.45 and abs(d['Z-Diff']) > 1.6:
        st.success("🔥 SEÑAL HALCÓN: Reversión inminente.")

with cb:
    sims, days = 250, 5
    rets = np.random.normal(0, d['Volatilidad'], (days, sims))
    paths = np.zeros((days+1, sims)); paths[0] = d['Precio']
    for t in range(1, days+1): paths[t] = paths[t-1] * (1 + rets[t-1])
    
    p10, p50, p90 = np.percentile(paths, 10, axis=1), np.percentile(paths, 50, axis=1), np.percentile(paths, 90, axis=1)
    
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Scatter(x=list(range(6))+list(range(6))[::-1], y=list(p90)+list(p10[::-1]), fill='toself', fillcolor='rgba(0,150,255,0.1)', line=dict(color='rgba(255,255,255,0)'), name='80% Prob.'))
    fig_mc.add_trace(go.Scatter(x=list(range(6)), y=p50, line=dict(color='cyan', width=3), name='Eje Central'))
    st.plotly_chart(fig_mc, use_container_width=True)

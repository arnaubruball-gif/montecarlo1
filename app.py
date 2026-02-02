import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Halcón 4.0: Terminal Fractal", layout="wide", page_icon="🦅")

def calcular_hurst(ts):
    if len(ts) < 30: return 0.5
    lags = range(2, 20)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

@st.cache_data(ttl=600)
def fetch_data_robust(tickers):
    results = []
    # Descargamos uno a uno con manejo de error individual
    for ticker in tickers:
        try:
            # Añadimos un pequeño retraso para no saturar
            df = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
            
            if not df.empty:
                # Aplanar columnas si vienen con multi-index
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                prices = df['Close'].values.flatten().astype(float)
                volumes = df['Volume'].values.flatten().astype(float)
                
                # Cálculos
                window = prices[-40:]
                ma40 = np.mean(window)
                z_diff = (prices[-1] - ma40) / (np.std(window) + 1e-9)
                hurst = calcular_hurst(prices[-50:])
                vol_rel = volumes[-1] / (np.mean(volumes[-20:]) + 1e-9)
                volatilidad = np.std(np.diff(prices[-20:]) / (prices[-21:-1] + 1e-9))

                results.append({
                    'Ticker': ticker, 'Precio': round(prices[-1], 4),
                    'Z-Diff': round(z_diff, 2), 'Hurst': round(hurst, 2),
                    'Vol_Rel': round(vol_rel, 2), 'Volatilidad': volatilidad, 'MA40': ma40
                })
        except Exception:
            continue
    return pd.DataFrame(results)

# --- 2. INTERFAZ ---
st.title("🦅 Halcón 4.0: Radar Anti-Bloqueo")

# Lista optimizada (menos activos = menos riesgo de bloqueo)
assets = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'BTC-USD', 'GC=F', 'ES=F']

if st.button('🔄 Intentar Reconexión'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('Accediendo a la red de liquidez...'):
    df = fetch_data_robust(assets)

if df.empty:
    st.error("🚨 Yahoo Finance sigue bloqueando la petición desde este servidor.")
    st.info("💡 **SOLUCIÓN:** Como estás en el Free Tier de Streamlit, la IP es compartida. Prueba a cambiar el nombre del repositorio en GitHub o espera 5 minutos para que se asigne una nueva IP.")
    st.stop()

# Score Halcón
df['Score_Halcon'] = (abs(df['Z-Diff']) * (1 - df['Hurst']) / (df['Vol_Rel'] + 0.1)).round(2)
df = df.sort_values(by='Score_Halcon', ascending=False)

# --- 3. DASHBOARD ---
c1, c2 = st.columns(2)
with c1:
    st.subheader("📊 Oportunidades")
    st.dataframe(df.style.background_gradient(subset=['Score_Halcon'], cmap='YlOrRd'), use_container_width=True)

with c2:
    st.subheader("🎯 Mapa Fractal")
    fig = px.scatter(df, x="Z-Diff", y="Hurst", size="Vol_Rel", text="Ticker", color="Score_Halcon", color_continuous_scale="Viridis")
    fig.add_hline(y=0.5, line_dash="dash", line_color="white")
    st.plotly_chart(fig, use_container_width=True)

# --- 4. MONTECARLO ---
st.divider()
sel = st.selectbox("Activo:", df['Ticker'])
d = df[df['Ticker'] == sel].iloc[0]

ca, cb = st.columns([1, 2])
with ca:
    st.metric("Distancia a Media (Z)", d['Z-Diff'])
    st.metric("Hurst", d['Hurst'])
    if d['Hurst'] < 0.45:
        st.success("✅ Mercado en Reversión")
    else:
        st.warning("⚠️ Mercado en Tendencia")

with cb:
    sims, days = 100, 5
    rets = np.random.normal(0, d['Volatilidad'], (days, sims))
    paths = np.zeros((days+1, sims)); paths[0] = d['Precio']
    for t in range(1, days+1): paths[t] = paths[t-1] * (1 + rets[t-1])
    p10, p50, p90 = np.percentile(paths, 10, axis=1), np.percentile(paths, 50, axis=1), np.percentile(paths, 90, axis=1)
    
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Scatter(x=list(range(6))+list(range(6))[::-1], y=list(p90)+list(p10[::-1]), fill='toself', fillcolor='rgba(0,150,255,0.1)', line=dict(color='rgba(255,255,255,0)'), name='80% Prob.'))
    fig_mc.add_trace(go.Scatter(x=list(range(6)), y=p50, line=dict(color='cyan', width=2), name='Media'))
    st.plotly_chart(fig_mc, use_container_width=True)

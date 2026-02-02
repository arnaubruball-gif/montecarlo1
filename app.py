import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import time

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Halcón 4.0: Fractal Terminal", layout="wide", page_icon="🦅")

# --- 2. FUNCIONES MATEMÁTICAS ---

def calcular_hurst(ts):
    if len(ts) < 30: return 0.5
    lags = range(2, 20)
    tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

@st.cache_data(ttl=900) # Aumentamos cache a 15 min para evitar bloqueos
def fetch_global_data(tickers):
    # Descarga masiva para evitar múltiples peticiones
    try:
        data = yf.download(tickers, period="70d", interval="1d", progress=False, group_by='ticker')
        return data
    except:
        return None

def process_data(data, tickers):
    results = []
    for ticker in tickers:
        try:
            df_hist = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
            
            if len(df_hist) > 40:
                prices = df_hist['Close'].values.flatten().astype(float)
                volumes = df_hist['Volume'].values.flatten().astype(float)
                
                # --- MÉTRICAS HALCÓN ---
                window = prices[-40:]
                ma40 = np.mean(window)
                z_diff = (prices[-1] - ma40) / np.std(window)
                
                hurst = calcular_hurst(prices[-50:])
                
                vol_avg = np.mean(volumes[-20:])
                vol_rel = volumes[-1] / vol_avg if vol_avg > 0 else 1
                volatilidad = np.std(np.diff(prices[-20:]) / prices[-21:-1])

                results.append({
                    'Ticker': ticker, 'Precio': round(prices[-1], 4),
                    'Z-Diff': round(z_diff, 2), 'Hurst': round(hurst, 2), 
                    'Vol_Rel': round(vol_rel, 2), 'Volatilidad': volatilidad, 
                    'MA40': ma40
                })
        except: continue
    return pd.DataFrame(results)

# --- 3. INTERFAZ ---
st.title("🦅 Halcón 4.0: Terminal Fractal Pro")

assets = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'NZDUSD=X', 'USDCAD=X', 'BTC-USD', 'GC=F', 'ES=F']

if st.button('🔄 Refrescar Conexión'):
    st.cache_data.clear()
    st.rerun()

with st.spinner('Sincronizando con mercados globales...'):
    raw_data = fetch_global_data(assets)
    if raw_data is not None and not raw_data.empty:
        df = process_data(raw_data, assets)
    else:
        df = pd.DataFrame()

if df.empty:
    st.error("🚨 Yahoo Finance ha limitado la conexión. Por favor, espera 30 segundos y pulsa 'Refrescar Conexión'.")
    st.info("💡 Consejo: No refresques la página excesivamente para evitar bloqueos de IP.")
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
                     color="Score_Halcon", color_continuous_scale="Viridis",
                     range_x=[-4, 4], range_y=[0.2, 0.8])
    fig.add_hline(y=0.5, line_dash="dash", line_color="white")
    st.plotly_chart(fig, use_container_width=True)

# --- 5. MONTECARLO ---
st.divider()
target = st.selectbox("Activo para Proyección:", df['Ticker'])
d = df[df['Ticker'] == target].iloc[0]

ca, cb = st.columns([1, 2])
with ca:
    st.write(f"### Estrategia para {target}")
    st.metric("Fractalidad", d['Hurst'], delta="REVERSIÓN" if d['Hurst'] < 0.5 else "TENDENCIA")
    if d['Hurst'] < 0.45 and abs(d['Z-Diff']) > 1.8:
        st.success("🎯 SEÑAL: Reversión de alta convicción.")
    else:
        st.info("⏳ Esperando ineficiencia fractal...")

with cb:
    sims, days = 250, 5
    rets = np.random.normal(0, d['Volatilidad'], (days, sims))
    paths = np.zeros((days+1, sims)); paths[0] = d['Precio']
    for t in range(1, days+1): paths[t] = paths[t-1] * (1 + rets[t-1])
    
    p10, p50, p90 = np.percentile(paths, 10, axis=1), np.percentile(paths, 50, axis=1), np.percentile(paths, 90, axis=1)
    
    fig_mc = go.Figure()
    fig_mc.add_trace(go.Scatter(x=list(range(6))+list(range(6))[::-1], y=list(p90)+list(p10[::-1]), fill='toself', fillcolor='rgba(0,150,255,0.15)', line=dict(color='rgba(255,255,255,0)'), name='80% Confianza'))
    fig_mc.add_trace(go.Scatter(x=list(range(6)), y=p50, line=dict(color='cyan', width=3), name='Media'))
    st.plotly_chart(fig_mc, use_container_width=True)

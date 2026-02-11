import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Terminal Pro: Safe Mode", layout="wide", page_icon="🏦")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-box { padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 8px solid; }
    .safe { background-color: #052111; border-color: #3fb950; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE VALORACIÓN ---
def calcular_graham(eps, g):
    return (eps * (8.5 + 2 * (g * 100)) * 4.4) / 4.5 if eps > 0 else 0

def calcular_ddm(div, g_div, k):
    return (div * (1 + g_div)) / (k - g_div) if k > g_div and div > 0 else 0

# --- 3. GESTIÓN DE DATOS ---
@st.cache_data(ttl=600)
def get_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        if 'currentPrice' not in info: return None
        return info
    except:
        return None

# --- 4. SIDEBAR ---
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/3310/3310111.png"
st.sidebar.image(LOGO_URL, width=60)
st.sidebar.title("Equity Suite v5.5")
ticker = st.sidebar.text_input("Ticker", "NVDA").upper()

info = get_data(ticker)

# --- 5. LÓGICA DE VISUALIZACIÓN ---
if info:
    st.success(f"Datos de {ticker} cargados correctamente.")
    # Extraer datos reales
    current_price = info.get('currentPrice', 0)
    eps_real = info.get('trailingEps', 0)
    div_real = info.get('trailingAnnualDividendRate', 0)
    fcf_real = info.get('freeCashflow') or (info.get('operatingCashflow', 0) * 0.8)
else:
    st.warning("⚠️ Yahoo Finance está bloqueando la conexión (Rate Limit).")
    st.info("Introduce los datos manualmente para usar los modelos analíticos:")
    col_man1, col_man2, col_man3 = st.columns(3)
    current_price = col_man1.number_input("Precio Acción", value=100.0)
    eps_real = col_man2.number_input("EPS (Beneficio por Acción)", value=5.0)
    div_real = col_man3.number_input("Dividendo Anual", value=2.0)
    fcf_real = eps_real * 0.9 # Estimación simple

# --- 6. PARÁMETROS DE LOS MODELOS ---
st.sidebar.divider()
k = st.sidebar.slider("Retorno Exigido (k) %", 5.0, 15.0, 9.0) / 100
g_growth = st.sidebar.slider("Crecimiento 5y (%)", 0.0, 50.0, 15.0) / 100
g_div = st.sidebar.slider("Crecimiento Div (%)", 0.0, 10.0, 4.0) / 100

# --- 7. PESTAÑAS ---
t1, t2, t3, t4 = st.tabs(["🚀 Growth (DCF)", "📜 Graham", "💰 Dividendos (DDM)", "⚠️ Riesgo"])

with t1:
    # Modelo simplificado de 2 etapas
    tv = (fcf_real * (1+g_growth)**5 * 25) / (1+k)**5
    fcf_d = sum([(fcf_real * (1+g_growth)**i)/(1+k)**i for i in range(1,6)])
    val_growth = (fcf_d + tv) / (info.get('sharesOutstanding', 1) if info else 1)
    # Si estamos en modo manual, ajustamos el valor para que sea legible
    if not info: val_growth = fcf_d + (fcf_real * (1+g_growth)**5 * 15 / (1+k)**5)
    
    st.metric("Target Growth", f"{val_growth:.2f}")
    

with t2:
    val_graham = calcular_graham(eps_real, g_growth)
    st.metric("Target Graham", f"{val_graham:.2f}")
    

with t3:
    val_ddm = calcular_ddm(div_real, g_div, k)
    st.metric("Target DDM", f"{val_ddm:.2f}")
    

with t4:
    st.subheader("Análisis de Riesgo")
    if info:
        z = (1.2 * (info.get('totalCurrentAssets', 0) / info.get('totalAssets', 1))) # Simplificado
        st.write(f"Z-Score estimado: {z:.2f}")
    else:
        st.write("Modo manual: Datos de balance no disponibles.")

# --- 8. VEREDICTO ---
st.divider()
targets = [v for v in [val_growth, val_graham, val_ddm] if v > 0]
final_target = sum(targets) / len(targets) if targets else 0
upside = ((final_target / current_price) - 1) * 100

c_v1, c_v2 = st.columns([1, 2])
c_v1.metric("Target Final Ponderado", f"{final_target:.2f}", delta=f"{upside:.1f}%")

if upside > 20:
    c_v2.markdown("<div class='status-box safe'><h2>🚀 COMPRA</h2>Buen margen de seguridad.</div>", unsafe_allow_html=True)
else:
    c_v2.markdown("<div class='status-box' style='background-color:#1c1c1c;'><h2>⚖️ MANTENER</h2>Precio en equilibrio.</div>", unsafe_allow_html=True)

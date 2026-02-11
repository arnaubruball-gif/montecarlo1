import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Terminal Pro: Total Analysis", layout="wide", page_icon="🏦")

# Estilo CSS
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
    # Fórmula Graham: (EPS * (8.5 + 2g) * 4.4) / 4.5
    return (eps * (8.5 + 2 * (g * 100)) * 4.4) / 4.5 if eps > 0 else 0

def calcular_ddm(div, g_div, k):
    # Gordon Growth
    return (div * (1 + g_div)) / (k - g_div) if k > g_div and div > 0 else 0

# --- 3. CARGA DE DATOS (MÉTODO ROBUSTO) ---
@st.cache_data(ttl=3600)
def get_full_data(ticker_symbol):
    try:
        dat = yf.Ticker(ticker_symbol)
        # Intentamos obtener todo en un solo bloque para evitar múltiples hits
        info = dat.info
        if 'currentPrice' not in info:
            return None
        return info
    except Exception:
        return None

# --- 4. SIDEBAR ---
st.sidebar.title("🏛️ Equity Engine Pro")
ticker = st.sidebar.text_input("Ticker", "NVDA").upper()
info = get_full_data(ticker)

# Parámetros Globales
st.sidebar.divider()
k = st.sidebar.slider("Retorno Exigido (k) %", 5.0, 15.0, 9.0) / 100
g_growth = st.sidebar.slider("Crecimiento 5y (%)", 0.0, 60.0, 20.0) / 100
g_div = st.sidebar.slider("Crecimiento Div (%)", 0.0, 12.0, 5.0) / 100

# --- 5. INTERFAZ PRINCIPAL ---
if info:
    st.title(f"{info.get('longName', ticker)}")
    
    # Datos Clave
    price = info.get('currentPrice', 1)
    eps = info.get('trailingEps', 0)
    div = info.get('trailingAnnualDividendRate', 0)
    fcf = info.get('freeCashflow') or (info.get('operatingCashflow', 0) * 0.8)
    shares = info.get('sharesOutstanding', 1)

    # Pestañas
    t_growth, t_div, t_graham, t_risk = st.tabs(["🚀 GROWTH (Exit)", "💰 DDF (Dividendos)", "📜 GRAHAM", "⚠️ RIESGO/CALIDAD"])

    with t_growth:
        st.subheader("Modelo de Múltiplos de Salida")
        
        # Proyectamos FCF a 5 años y aplicamos múltiplo
        fcf_5 = fcf * (1 + g_growth)**5
        exit_m = 25 
        tv_d = (fcf_5 * exit_m) / (1 + k)**5
        fcf_d = sum([(fcf * (1 + g_growth)**i)/(1+k)**i for i in range(1,6)])
        val_exit = (fcf_d + tv_d - info.get('totalDebt', 0) + info.get('totalCash', 0)) / shares
        st.metric("Target Growth", f"{val_exit:.2f} {info.get('currency')}")

    with t_div:
        st.subheader("Modelo de Descuento de Dividendos")
        
        val_ddm = calcular_ddm(div, g_div, k)
        st.metric("Target DDM", f"{val_ddm:.2f} {info.get('currency')}")
        st.write(f"Payout Ratio: {info.get('payoutRatio', 0)*100:.1f}%")

    with t_graham:
        st.subheader("Fórmula de Benjamin Graham")
        
        val_graham = calcular_graham(eps, g_growth)
        st.metric("Target Graham", f"{val_graham:.2f} {info.get('currency')}")

    with t_risk:
        st.subheader("Calidad y Solvencia")
        
        roe = info.get('returnOnEquity', 0)
        cr = info.get('currentRatio', 0)
        # Z-Score simplificado
        z = (1.2 * (info.get('totalCurrentAssets', 0)/info.get('totalAssets', 1))) + (3.3 * (info.get('ebitda', 0)/info.get('totalAssets', 1)))
        
        c1, c2, c3 = st.columns(3)
        c1.metric("ROE", f"{roe*100:.1f}%")
        c2.metric("Liquidez", f"{cr:.2f}x")
        c3.metric("Z-Score Est.", f"{z:.2f}")

    # --- VEREDICTO ---
    st.divider()
    modelos = [v for v in [val_exit, val_ddm, val_graham] if v > 0]
    final_target = sum(modelos) / len(modelos) if modelos else 0
    upside = ((final_target / price) - 1) * 100

    col_res1, col_res2 = st.columns([1, 2])
    col_res1.metric("Target Promedio", f"{final_target:.2f}", delta=f"{upside:.1f}%")
    
    if upside > 20:
        col_res2.markdown("<div class='status-box safe'><h2>🚀 COMPRA FUERTE</h2>Buen margen de seguridad detectado.</div>", unsafe_allow_html=True)
    else:
        col_res2.markdown("<div class='status-box' style='background-color:#1c1c1c;'><h2>⚖️ MANTENER</h2>Valoración en línea con mercado.</div>", unsafe_allow_html=True)

else:
    st.error("❌ Yahoo Finance ha bloqueado la petición (Rate Limit).")
    st.info("Yahoo bloquea las IPs de los servidores de Streamlit a menudo. Prueba a ejecutarlo en local o espera unos minutos.")

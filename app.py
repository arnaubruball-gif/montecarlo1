import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Terminal Pro: Multi-Model Suite", layout="wide", page_icon="🏦")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-box { padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 8px solid; font-size: 14px; }
    .safe { background-color: #052111; border-color: #3fb950; }
    .warning { background-color: #211d05; border-color: #d29922; }
    .danger { background-color: #210505; border-color: #f85149; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE MODELADO ---
def calcular_graham(eps, g_f1):
    if eps <= 0: return 0
    # Fórmula: (EPS * (8.5 + 2g) * 4.4) / 4.5
    return (eps * (8.5 + 2 * (g_f1 * 100)) * 4.4) / 4.5

def calcular_ddm(div, g_div, k):
    if k <= g_div or div <= 0: return 0
    return (div * (1 + g_div)) / (k - g_div)

def calcular_z_score(info):
    try:
        # Simplificación para evitar errores si faltan datos de balance profundo
        total_assets = info.get('totalAssets', 1)
        z = (1.2 * (info.get('totalCurrentAssets', 0) / total_assets) +
             1.4 * (info.get('retainedEarnings', 0) / total_assets) +
             3.3 * (info.get('ebitda', 0) / total_assets) +
             0.6 * (info.get('marketCap', 0) / info.get('totalLiabilitiesNetMinorityInterest', 1)) +
             1.0 * (info.get('totalRevenue', 0) / total_assets))
        return z
    except: return 0

# --- 3. GESTIÓN DE DATOS (ANTI-RATE LIMIT) ---
@st.cache_data(ttl=3600) # Caché de 1 hora para no saturar a Yahoo
def fetch_all_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        if not info or 'currentPrice' not in info:
            return None, None
        hist = stock.history(period="5y")
        return info, hist
    except Exception:
        return None, None

# --- 4. SIDEBAR ---
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/3310/3310111.png"
st.sidebar.image(LOGO_URL, width=60)
st.sidebar.title("Equity Suite v5.0")
ticker_input = st.sidebar.text_input("Ticker", "NVDA").upper()

info, hist = fetch_all_data(ticker_input)

if info:
    # Controles
    st.sidebar.divider()
    k = st.sidebar.slider("Exigencia de Retorno (k) %", 5.0, 15.0, 9.0) / 100
    g_f1 = st.sidebar.slider("Crecimiento 5y (%)", 0.0, 60.0, 20.0) / 100
    g_div = st.sidebar.slider("Crecimiento Dividendos (%)", 0.0, 10.0, 4.0) / 100
    
    # --- 5. HEADER ---
    st.title(f"{info.get('longName', ticker_input)}")
    price = info.get('currentPrice', 1)
    currency = info.get('currency', 'USD')
    
    # --- 6. TABS ---
    t_growth, t_dividend, t_graham, t_value, t_risk = st.tabs([
        "🚀 GROWTH", "💰 DDF (Dividendos)", "📜 GRAHAM", "💎 ASSETS", "⚠️ RIESGO"
    ])

    with t_growth:
        st.subheader("Valoración por Múltiplos de Salida")
        
        fcf = info.get('freeCashflow') or (info.get('operatingCashflow', 0) * 0.8)
        exit_m = 25 
        fcf_5 = fcf * (1 + g_f1)**5
        tv_d = (fcf_5 * exit_m) / (1 + k)**5
        fcf_d = sum([(fcf * (1 + g_f1)**i) / (1 + k)**i for i in range(1, 6)])
        val_growth = (fcf_d + tv_d - info.get('totalDebt', 0) + info.get('totalCash', 0)) / info.get('sharesOutstanding', 1)
        st.metric("Target Growth", f"{val_growth:.2f} {currency}")

    with t_dividend:
        st.subheader("Modelo de Descuento de Dividendos (DDF)")
        
        div = info.get('trailingAnnualDividendRate', 0)
        val_ddm = calcular_ddm(div, g_div, k)
        st.metric("Target DDF", f"{val_ddm:.2f} {currency}")
        st.write(f"Payout Ratio: {info.get('payoutRatio', 0)*100:.1f}%")

    with t_graham:
        st.subheader("Fórmula de Graham")
        
        eps = info.get('trailingEps', 0)
        val_graham = calcular_graham(eps, g_f1)
        st.metric("Target Graham", f"{val_graham:.2f} {currency}")

    with t_value:
        st.subheader("Análisis de Activos")
        ncav = (info.get('totalCurrentAssets', 0) - info.get('totalLiabilitiesNetMinorityInterest', 0)) / info.get('sharesOutstanding', 1)
        st.metric("Valor Liquidación (NCAV)", f"{ncav:.2f} {currency}")

    with t_risk:
        st.subheader("Salud Financiera")
        
        z = calcular_z_score(info)
        if z > 2.99: st.success(f"Zona Segura (Z={z:.2f})")
        elif z > 1.81: st.warning(f"Zona Gris (Z={z:.2f})")
        else: st.error(f"Zona de Peligro (Z={z:.2f})")

    # --- 7. VEREDICTO ---
    st.divider()
    modelos = [v for v in [val_growth, val_ddm, val_graham] if v > 0]
    final_target = sum(modelos) / len(modelos) if modelos else 0
    upside = ((final_target / price) - 1) * 100
    
    col_v1, col_v2 = st.columns([1, 2])
    col_v1.metric("Target Consenso", f"{final_target:.2f} {currency}", delta=f"{upside:.1f}%")
    
    if upside > 20 and z > 1.81:
        col_v2.markdown(f"<div class='status-box safe'><h2>🚀 COMPRA</h2>Se apoya en {len(modelos)} modelos analíticos.</div>", unsafe_allow_html=True)
    elif upside > -10:
        col_v2.markdown(f"<div class='status-box warning'><h2>⚖️ MANTENER</h2>Precio en rango de mercado.</div>", unsafe_allow_html=True)
    else:
        col_v2.markdown(f"<div class='status-box danger'><h2>⚠️ EVITAR</h2>Acción sobrevalorada o riesgo financiero.</div>", unsafe_allow_html=True)

else:
    st.error("🚨 Yahoo Finance ha bloqueado temporalmente las peticiones (Rate Limit).")
    st.info("Para solucionar esto: \n1. Espera 5-10 minutos.\n2. Si estás en local, cambia de red (puntos de acceso móvil).\n3. Revisa que el Ticker sea correcto.")

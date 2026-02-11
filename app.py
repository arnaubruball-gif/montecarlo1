import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Terminal Pro: Equity Engine", layout="wide", page_icon="🏦")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .status-box { padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 8px solid; }
    .info-card { background-color: #1c2128; border: 1px solid #30363d; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    .safe { background-color: #052111; border-color: #3fb950; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIONES DE VALORACIÓN ---
def calcular_graham(eps, g):
    return (eps * (8.5 + 2 * (g * 100)) * 4.4) / 4.5 if eps > 0 else 0

def calcular_ddm(div, g_div, k):
    return (div * (1 + g_div)) / (k - g_div) if k > g_div and div > 0 else 0

@st.cache_data(ttl=3600)
def get_full_data(ticker_symbol):
    try:
        dat = yf.Ticker(ticker_symbol)
        info = dat.info
        if 'currentPrice' not in info: return None
        return info
    except: return None

# --- 3. SIDEBAR ---
st.sidebar.title("🏛️ Equity Engine Pro")
ticker = st.sidebar.text_input("Ticker", "NVDA").upper()
info = get_full_data(ticker)

st.sidebar.divider()
k = st.sidebar.slider("Retorno Exigido (k) %", 5.0, 15.0, 9.0) / 100
g_growth = st.sidebar.slider("Crecimiento 5y (%)", 0.0, 60.0, 20.0) / 100
g_div = st.sidebar.slider("Crecimiento Div (%)", 0.0, 12.0, 5.0) / 100

# --- 4. DASHBOARD PRINCIPAL ---
if info:
    # --- SECCIÓN A: INFO GENERAL Y PRECIO ---
    st.title(f"{info.get('longName', ticker)}")
    st.caption(f"Sector: {info.get('sector')} | Industria: {info.get('industry')} | País: {info.get('country')}")
    
    with st.expander("📖 Descripción de la Empresa"):
        st.write(info.get('longBusinessSummary'))

    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    price = info.get('currentPrice', 1)
    currency = info.get('currency', 'USD')
    
    col_p1.metric("Precio Actual", f"{price} {currency}")
    col_p2.metric("Market Cap", f"{info.get('marketCap', 0)/1e9:.2f}B")
    col_p3.metric("Máx 52 Semanas", f"{info.get('fiftyTwoWeekHigh')} {currency}")
    col_p4.metric("Mín 52 Semanas", f"{info.get('fiftyTwoWeekLow')} {currency}")

    st.divider()

    # --- SECCIÓN B: RATIOS PRINCIPALES ---
    st.subheader("📊 Ratios Clave de Análisis")
    r1, r2, r3, r4 = st.columns(4)
    
    # Valoración
    with r1:
        st.write("**Valoración**")
        st.write(f"PER (Trailing): `{info.get('trailingPE', 'N/A')}`")
        st.write(f"Forward PER: `{info.get('forwardPE', 'N/A')}`")
        st.write(f"Price/Book: `{info.get('priceToBook', 'N/A')}`")
        st.write(f"EV/EBITDA: `{info.get('enterpriseToEbitda', 'N/A')}`")

    # Rentabilidad
    with r2:
        st.write("**Rentabilidad**")
        st.write(f"ROE: `{info.get('returnOnEquity', 0)*100:.2f}%`")
        st.write(f"ROA: `{info.get('returnOnAssets', 0)*100:.2f}%`")
        st.write(f"M. Bruto: `{info.get('grossMargins', 0)*100:.2f}%`")
        st.write(f"M. Neto: `{info.get('profitMargins', 0)*100:.2f}%`")

    # Salud Financiera
    with r3:
        st.write("**Solvencia**")
        st.write(f"Current Ratio: `{info.get('currentRatio', 'N/A')}x`")
        st.write(f"Quick Ratio: `{info.get('quickRatio', 'N/A')}x`")
        st.write(f"Debt/Equity: `{info.get('debtToEquity', 'N/A')}`")
        st.write(f"Caja Total: `{info.get('totalCash', 0)/1e9:.2f}B`")

    # Dividendos
    with r4:
        st.write("**Dividendo**")
        st.write(f"Rentabilidad: `{info.get('dividendYield', 0)*100:.2f}%`")
        st.write(f"Div. Anual: `{info.get('trailingAnnualDividendRate', 'N/A')} {currency}`")
        st.write(f"Payout Ratio: `{info.get('payoutRatio', 0)*100:.2f}%`")
        st.write(f"5y Avg Yield: `{info.get('fiveYearAvgDividendYield', 'N/A')}%`")

    st.divider()

    # --- SECCIÓN C: MODELOS DE VALORACIÓN (TABS) ---
    eps = info.get('trailingEps', 0)
    div = info.get('trailingAnnualDividendRate', 0)
    fcf = info.get('freeCashflow') or (info.get('operatingCashflow', 0) * 0.8)
    shares = info.get('sharesOutstanding', 1)

    t_growth, t_div, t_graham, t_risk = st.tabs(["🚀 GROWTH (Exit)", "💰 DDF (Dividendos)", "📜 GRAHAM", "⚠️ RIESGO Z-SCORE"])

    with t_growth:
        st.subheader("Modelo de Múltiplos de Salida")
        
        fcf_5 = fcf * (1 + g_growth)**5
        tv_d = (fcf_5 * 25) / (1 + k)**5
        fcf_d = sum([(fcf * (1 + g_growth)**i)/(1+k)**i for i in range(1,6)])
        val_exit = (fcf_d + tv_d - info.get('totalDebt', 0) + info.get('totalCash', 0)) / shares
        st.metric("Target Growth", f"{val_exit:.2f} {currency}")

    with t_div:
        st.subheader("Modelo Gordon Growth")
        
        val_ddm = calcular_ddm(div, g_div, k)
        st.metric("Target DDM", f"{val_ddm:.2f} {currency}")

    with t_graham:
        st.subheader("Fórmula de Graham")
        
        val_graham = calcular_graham(eps, g_growth)
        st.metric("Target Graham", f"{val_graham:.2f} {currency}")

    with t_risk:
        st.subheader("Salud Financiera")
        
        z = (1.2 * (info.get('totalCurrentAssets', 0)/info.get('totalAssets', 1))) + (3.3 * (info.get('ebitda', 0)/info.get('totalAssets', 1)))
        st.metric("Z-Score Estimado", f"{z:.2f}")

    # --- VEREDICTO ---
    st.divider()
    modelos = [v for v in [val_exit, val_ddm, val_graham] if v > 0]
    final_target = sum(modelos) / len(modelos) if modelos else 0
    upside = ((final_target / price) - 1) * 100

    col_res1, col_res2 = st.columns([1, 2])
    col_res1.metric("Precio Objetivo Medio", f"{final_target:.2f} {currency}", delta=f"{upside:.1f}%")
    
    if upside > 20:
        col_res2.markdown("<div class='status-box safe'><h2>🚀 RECOMENDACIÓN: COMPRA</h2>Margen de seguridad atractivo.</div>", unsafe_allow_html=True)
    else:
        col_res2.markdown("<div class='status-box' style='background-color:#1c1c1c;'><h2>⚖️ RECOMENDACIÓN: MANTENER</h2>Valoración justa.</div>", unsafe_allow_html=True)

else:
    st.error("No se han podido cargar los datos. Revisa el Ticker o intenta más tarde (Rate Limit).")

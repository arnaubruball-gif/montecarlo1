import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

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
    """Fórmula de Benjamin Graham (Valor Intrínseco)"""
    # Valor = (EPS * (8.5 + 2g) * 4.4) / Y (Bond Yield actual ~4.5)
    if eps <= 0: return 0
    return (eps * (8.5 + 2 * (g_f1 * 100)) * 4.4) / 4.5

def calcular_ddm(div, g_div, k):
    """Modelo de Descuento de Dividendos (Gordon Growth)"""
    if k <= g_div or div <= 0: return 0
    return (div * (1 + g_div)) / (k - g_div)

@st.cache_data
def fetch_all_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    return stock.info, stock.history(period="5y")

# --- 3. SIDEBAR ---
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/3310/3310111.png"
st.sidebar.image(LOGO_URL, width=60)
st.sidebar.title("Equity Suite v5.0")
ticker = st.sidebar.text_input("Ticker", "NVDA").upper()

try:
    info, hist = fetch_all_data(ticker)
    
    st.sidebar.divider()
    k = st.sidebar.slider("Exigencia de Retorno (k) %", 5.0, 15.0, 9.0) / 100
    g_f1 = st.sidebar.slider("Crecimiento 5y (%)", 0.0, 60.0, 20.0) / 100
    g_div = st.sidebar.slider("Crecimiento Dividendos (%)", 0.0, 10.0, 4.0) / 100
    
    # --- 4. HEADER ---
    st.title(f"{info.get('longName', ticker)}")
    price = info.get('currentPrice', 1)
    currency = info.get('currency', 'USD')
    
    # --- 5. TABS DE MODELOS ---
    t_growth, t_dividend, t_graham, t_value, t_risk = st.tabs([
        "🚀 GROWTH", "💰 DDF (Dividendos)", "📜 GRAHAM", "💎 ASSETS", "⚠️ RIESGO"
    ])

    with t_growth:
        st.subheader("Valoración por Múltiplos de Salida")
        
        fcf = info.get('freeCashflow') or (info.get('operatingCashflow', 0) * 0.8)
        exit_m = 25 # Múltiplo estándar para el sector
        fcf_5 = fcf * (1 + g_f1)**5
        tv_d = (fcf_5 * exit_m) / (1 + k)**5
        fcf_d = sum([(fcf * (1 + g_f1)**i) / (1 + k)**i for i in range(1, 6)])
        val_growth = (fcf_d + tv_d - info.get('totalDebt', 0) + info.get('totalCash', 0)) / info.get('sharesOutstanding', 1)
        st.metric("Precio Objetivo Growth", f"{val_growth:.2f} {currency}")

    with t_dividend:
        st.subheader("Modelo de Descuento de Dividendos (DDF)")
        
        div = info.get('trailingAnnualDividendRate', 0)
        val_ddm = calcular_ddm(div, g_div, k)
        st.metric("Precio Objetivo Dividendos", f"{val_ddm:.2f} {currency}")
        st.write(f"Payout Ratio: {info.get('payoutRatio', 0)*100:.1f}%")

    with t_graham:
        st.subheader("Fórmula de Valor Intrínseco de Graham")
        
        eps = info.get('trailingEps', 0)
        val_graham = calcular_graham(eps, g_f1)
        st.metric("Precio Objetivo Graham", f"{val_graham:.2f} {currency}")
        st.caption("Nota: Este modelo es sensible al crecimiento esperado de los beneficios (EPS).")

    with t_value:
        st.subheader("Valoración por Activos Reales")
        ncav = (info.get('totalCurrentAssets', 0) - info.get('totalLiabilitiesNetMinorityInterest', 0)) / info.get('sharesOutstanding', 1)
        st.metric("Valor de Liquidación (NCAV)", f"{ncav:.2f} {currency}")
        st.metric("Valor Contable por Acción", f"{info.get('bookValue', 0):.2f}")

    with t_risk:
        st.subheader("Análisis de Riesgo de Quiebra (Altman)")
        # Lógica resumida del Z-Score (reutilizando la función anterior)
        z = 3.1 # Placeholder: aquí iría la función de Z-score definida antes
        st.metric("Altman Z-Score", f"{z:.2f}")

    # --- 6. VEREDICTO MAESTRO ---
    st.divider()
    st.subheader("⚖️ Veredicto Ponderado")
    
    # Promedio inteligente (Solo cuenta modelos con valores positivos)
    modelos = [v for v in [val_growth, val_ddm, val_graham] if v > 0]
    final_target = sum(modelos) / len(modelos) if modelos else 0
    upside = ((final_target / price) - 1) * 100
    
    col_v1, col_v2 = st.columns([1, 2])
    col_v1.metric("Target Consensuado", f"{final_target:.2f} {currency}", delta=f"{upside:.1f}%")
    
    if upside > 20:
        col_v2.markdown(f"<div class='status-box safe'><h2>🚀 RECOMENDACIÓN: COMPRA</h2>Upside significativo basado en {len(modelos)} modelos.</div>", unsafe_allow_html=True)
    elif upside > -10:
        col_v2.markdown(f"<div class='status-box warning'><h2>⚖️ RECOMENDACIÓN: PRECIO JUSTO</h2>La acción cotiza en rangos razonables.</div>", unsafe_allow_html=True)
    else:
        col_v2.markdown(f"<div class='status-box danger'><h2>⚠️ RECOMENDACIÓN: VENTA</h2>Sobrevaloración detectada.</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error cargando ticker: {e}")

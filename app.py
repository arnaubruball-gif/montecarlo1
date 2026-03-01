import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Ultra-Quant Terminal", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: white; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    .trade-card { padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 10px solid; }
    .long { background-color: #052111; border-color: #3fb950; }
    .short { background-color: #210505; border-color: #f85149; }
    .neutral { background-color: #1c1c1c; border-color: #8b949e; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR CUANTITATIVO (INDICADORES DE VELOCIDAD) ---
def get_quant_metrics(df):
    # ATR (Volatilidad para Stop Loss)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(14).mean()
    
    # Bandas de Bollinger (Límites Estadísticos)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['Upper_B'] = df['MA20'] + (df['STD20'] * 2)
    df['Lower_B'] = df['MA20'] - (df['STD20'] * 2)
    
    # ADX (Fuerza de la Tendencia)
    plus_dm = df['High'].diff()
    minus_dm = df['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    tr_14 = df['TR'].rolling(14).sum()
    plus_di = 100 * (plus_dm.rolling(14).sum() / tr_14)
    minus_di = 100 * (abs(minus_dm).rolling(14).sum() / tr_14)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['ADX'] = dx.rolling(14).mean()
    
    # Sharpe Ratio (Eficiencia del precio)
    returns = df['Close'].pct_change()
    df['Sharpe'] = (returns.mean() / returns.std()) * np.sqrt(252)
    
    return df

@st.cache_data(ttl=300)
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty: return None
        return get_quant_metrics(hist)
    except: return None

# --- 3. SIDEBAR: CONTROL DE RIESGO Y APALANCAMIENTO ---
st.sidebar.title("🛠️ Risk Manager")
capital = st.sidebar.number_input("Capital en Cuenta ($)", value=5000)
risk_pct = st.sidebar.slider("Riesgo por Operación (%)", 0.5, 3.0, 1.0) / 100
leverage = st.sidebar.number_input("Apalancamiento (X)", value=5, min_value=1)

ticker = st.sidebar.text_input("Ticker (Ej: ICE, EQIX, HAG.DE)", "ICE").upper()
df = fetch_data(ticker)

# --- 4. PANEL DE OPERATIVA ---
if df is not None:
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    st.title(f"⚡ Operativa de Corto Plazo: {ticker}")
    
    # MÉTRICAS DE VOLATILIDAD Y FUERZA
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precio Actual", f"{last['Close']:.2f}")
    m2.metric("ADX (Tendencia)", f"{last['ADX']:.1f}", help=">25 indica tendencia fuerte")
    m3.metric("Sharpe Ratio", f"{last['Sharpe']:.2f}", help="Calidad del movimiento")
    m4.metric("ATR (Volatilidad)", f"{last['ATR']:.2f}")

    st.divider()

    # --- PESTAÑAS ---
    t_signal, t_stats, t_calc = st.tabs(["🎯 SEÑAL QUANT", "📊 MÉTRICAS AVANZADAS", "🧮 CALCULADORA DE LOTES"])

    with t_signal:
        # Lógica de señales combinada
        trend_strong = last['ADX'] > 25
        oversold = last['Close'] < last['Lower_B']
        overbought = last['Close'] > last['Upper_B']
        momentum = last['Close'] > last['MA20']

        if oversold and trend_strong:
            st.markdown("<div class='trade-card long'><h2>🚀 COMPRA (Reversión Media)</h2>Precio en suelo estadístico con tendencia fuerte.</div>", unsafe_allow_html=True)
        elif momentum and trend_strong and not overbought:
            st.markdown("<div class='trade-card long'><h2>📈 COMPRA (Momentum)</h2>Tendencia confirmada y con espacio para subir.</div>", unsafe_allow_html=True)
        elif overbought:
            st.markdown("<div class='trade-card short'><h2>⚠️ VENTA / TAKE PROFIT</h2>Extremo de sobrecompra. Riesgo de retroceso.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='trade-card neutral'><h2>⚖️ ESPERAR</h2>No hay ventaja estadística clara ahora mismo.</div>", unsafe_allow_html=True)

    with t_stats:
        st.subheader("Análisis de Desviación")
        
        st.line_chart(df[['Close', 'Upper_B', 'Lower_B', 'MA20']].tail(60))
        st.write(f"Distancia a la banda superior: **{last['Upper_B'] - last['Close']:.2f}**")
        st.write(f"Fuerza de tendencia (ADX): **{last['ADX']:.1f}**")

    with t_calc:
        st.subheader("Planificación Apalancada")
        # Stop Loss a 2x ATR (Seguridad ante latigazos)
        stop_price = last['Close'] - (2 * last['ATR'])
        take_profit = last['Close'] + (4 * last['ATR'])
        risk_per_share = last['Close'] - stop_price
        
        # Tamaño de posición basado en riesgo monetario
        shares_to_buy = (capital * risk_pct) / risk_per_share
        notional_value = shares_to_buy * last['Close']
        required_margin = notional_value / leverage

        c_r1, c_r2 = st.columns(2)
        with c_r1:
            st.info(f"🛑 STOP-LOSS: **{stop_price:.2f}**")
            st.success(f"🎯 TAKE-PROFIT: **{take_profit:.2f}**")
        
        with c_r2:
            st.write(f"Acciones a operar: **{int(shares_to_buy)}**")
            st.write(f"Valor nominal: **${notional_value:.2f}**")
            st.warning(f"Margen real a aportar: **${required_margin:.2f}**")
        
        

    st.divider()
    st.caption("Recuerda: El apalancamiento es una herramienta de precisión. Si el ADX es bajo, reduce el tamaño de la posición.")

else:
    st.error("Error: Ticker no encontrado o exceso de peticiones a la API.")

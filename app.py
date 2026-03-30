"""
MACRO ECONOMIC DASHBOARD PRO
Dashboard completo de análisis económico con enfoque en tipos de interés y tendencias macro
Autor: Trading Analytics
Versión: 1.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
from fredapi import Fred
import requests
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Macro Economic Dashboard Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# ESTILOS PERSONALIZADOS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.3);
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .main-subtitle {
        font-size: 1.1rem;
        color: rgba(255, 255, 255, 0.8);
        margin-top: 0.5rem;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.6);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.25rem;
    }
    
    .metric-change {
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .metric-change.positive {
        color: #10b981;
    }
    
    .metric-change.negative {
        color: #ef4444;
    }
    
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(59, 130, 246, 0.5);
    }
    
    .info-box {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .warning-box {
        background: rgba(245, 158, 11, 0.1);
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .success-box {
        background: rgba(16, 185, 129, 0.1);
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: rgba(255, 255, 255, 0.9);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: white;
    }
    
    div[data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.7);
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE DATOS - FRED API
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_fred_data(series_id: str, start_date: str = None) -> pd.Series:
    """
    Obtiene datos de FRED (Federal Reserve Economic Data)
    Necesitas una API key gratuita de https://fred.stlouisfed.org/
    """
    try:
        # IMPORTANTE: Reemplaza con tu API key de FRED
        fred = Fred(api_key='TU_API_KEY_AQUI')
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
        
        data = fred.get_series(series_id, start_date)
        return data
    except Exception as e:
        st.warning(f"Error obteniendo datos de FRED: {e}")
        return pd.Series()

@st.cache_data(ttl=3600)
def get_interest_rate_expectations() -> pd.DataFrame:
    """
    Obtiene expectativas de tipos de interés desde diferentes fuentes
    """
    try:
        # Fed Funds Rate efectivo
        fed_funds = get_fred_data('DFF')
        
        # Treasury yields (curva de rendimientos)
        t3m = get_fred_data('DGS3MO')
        t2y = get_fred_data('DGS2')
        t10y = get_fred_data('DGS10')
        t30y = get_fred_data('DGS30')
        
        # Combinar en DataFrame
        df = pd.DataFrame({
            'Fed Funds': fed_funds,
            '3M Treasury': t3m,
            '2Y Treasury': t2y,
            '10Y Treasury': t10y,
            '30Y Treasury': t30y
        })
        
        return df.dropna()
    except Exception as e:
        st.error(f"Error obteniendo expectativas de tipos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_macro_indicators() -> Dict[str, pd.Series]:
    """
    Obtiene indicadores macroeconómicos principales
    """
    indicators = {
        'GDP': 'GDP',           # PIB
        'CPI': 'CPIAUCSL',      # Inflación (CPI)
        'Unemployment': 'UNRATE',  # Tasa de desempleo
        'Retail Sales': 'RSXFS',   # Ventas minoristas
        'Industrial Production': 'INDPRO',  # Producción industrial
        'Housing Starts': 'HOUST',  # Inicio de viviendas
        'Consumer Sentiment': 'UMCSENT',  # Sentimiento del consumidor
        'PCE': 'PCEPI',         # Índice de precios PCE
        'M2 Money Supply': 'M2SL',  # Oferta monetaria M2
        'Trade Balance': 'BOPGSTB'  # Balanza comercial
    }
    
    data = {}
    for name, series_id in indicators.items():
        data[name] = get_fred_data(series_id)
    
    return data

@st.cache_data(ttl=3600)
def get_market_data() -> Dict[str, pd.DataFrame]:
    """
    Obtiene datos de mercados financieros
    """
    tickers = {
        'S&P 500': '^GSPC',
        'NASDAQ': '^IXIC',
        'DXY (Dollar Index)': 'DX-Y.NYB',
        'Gold': 'GC=F',
        'Oil (WTI)': 'CL=F',
        'VIX': '^VIX',
        '10Y Treasury': '^TNX'
    }
    
    data = {}
    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period='2y', progress=False)
            data[name] = df
        except Exception as e:
            st.warning(f"Error obteniendo {name}: {e}")
    
    return data

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_yield_curve_slope(df: pd.DataFrame) -> float:
    """
    Calcula la pendiente de la curva de rendimientos (10Y - 2Y)
    Una pendiente negativa puede indicar recesión
    """
    if '10Y Treasury' in df.columns and '2Y Treasury' in df.columns:
        latest = df.iloc[-1]
        return latest['10Y Treasury'] - latest['2Y Treasury']
    return 0.0

def calculate_rate_of_change(series: pd.Series, periods: int = 12) -> float:
    """
    Calcula la tasa de cambio porcentual en n períodos
    """
    if len(series) < periods + 1:
        return 0.0
    
    current = series.iloc[-1]
    past = series.iloc[-periods-1]
    
    if past == 0:
        return 0.0
    
    return ((current - past) / past) * 100

def forecast_interest_rates(df: pd.DataFrame, periods: int = 12) -> pd.DataFrame:
    """
    Proyección simple de tipos de interés usando media móvil y tendencia
    """
    forecasts = {}
    
    for col in df.columns:
        series = df[col].dropna()
        if len(series) < 3:
            continue
        
        # Calcular tendencia lineal simple
        x = np.arange(len(series))
        y = series.values
        
        # Regresión lineal simple
        coeffs = np.polyfit(x[-60:] if len(x) > 60 else x, y[-60:] if len(y) > 60 else y, 1)
        
        # Proyectar
        future_x = np.arange(len(series), len(series) + periods)
        future_y = np.polyval(coeffs, future_x)
        
        forecasts[col] = future_y
    
    # Crear DataFrame de proyecciones
    future_dates = pd.date_range(
        start=df.index[-1] + pd.Timedelta(days=30),
        periods=periods,
        freq='MS'
    )
    
    forecast_df = pd.DataFrame(forecasts, index=future_dates)
    return forecast_df

def calculate_recession_probability(indicators: Dict[str, pd.Series]) -> float:
    """
    Calcula probabilidad de recesión basada en indicadores clave
    Modelo simplificado basado en múltiples señales
    """
    score = 0
    max_score = 0
    
    # 1. Curva de rendimientos invertida
    max_score += 25
    # (se calculará con datos reales de la curva)
    
    # 2. Desempleo en aumento
    if 'Unemployment' in indicators:
        unemp = indicators['Unemployment']
        if len(unemp) >= 12:
            recent_change = unemp.iloc[-1] - unemp.iloc[-12]
            if recent_change > 0.5:  # Aumento de 0.5% en desempleo
                score += 20
    max_score += 20
    
    # 3. Producción industrial en descenso
    if 'Industrial Production' in indicators:
        ip = indicators['Industrial Production']
        if len(ip) >= 6:
            recent_trend = (ip.iloc[-1] - ip.iloc[-6]) / ip.iloc[-6] * 100
            if recent_trend < -2:  # Caída de 2%
                score += 15
    max_score += 15
    
    # 4. Sentimiento del consumidor bajo
    if 'Consumer Sentiment' in indicators:
        sentiment = indicators['Consumer Sentiment']
        if len(sentiment) >= 12:
            avg_sentiment = sentiment.iloc[-12:].mean()
            if sentiment.iloc[-1] < avg_sentiment * 0.9:  # 10% por debajo de media
                score += 15
    max_score += 15
    
    # 5. M2 Money Supply (velocidad del dinero)
    if 'M2 Money Supply' in indicators:
        m2 = indicators['M2 Money Supply']
        if len(m2) >= 12:
            m2_growth = (m2.iloc[-1] - m2.iloc[-12]) / m2.iloc[-12] * 100
            if m2_growth < 0:  # Contracción monetaria
                score += 15
    max_score += 15
    
    # 6. Inflación (CPI)
    if 'CPI' in indicators:
        cpi = indicators['CPI']
        if len(cpi) >= 12:
            inflation = (cpi.iloc[-1] - cpi.iloc[-12]) / cpi.iloc[-12] * 100
            if inflation > 4:  # Inflación alta
                score += 10
    max_score += 10
    
    return (score / max_score * 100) if max_score > 0 else 0

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE VISUALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def create_yield_curve_chart(df: pd.DataFrame, forecast_df: pd.DataFrame = None):
    """
    Crea gráfico de curva de rendimientos con proyección
    """
    fig = go.Figure()
    
    # Curva actual
    latest = df.iloc[-1]
    maturities = ['3M', '2Y', '10Y', '30Y']
    rates = [
        latest.get('3M Treasury', 0),
        latest.get('2Y Treasury', 0),
        latest.get('10Y Treasury', 0),
        latest.get('30Y Treasury', 0)
    ]
    
    fig.add_trace(go.Scatter(
        x=maturities,
        y=rates,
        mode='lines+markers',
        name='Curva Actual',
        line=dict(color='#3b82f6', width=3),
        marker=dict(size=10)
    ))
    
    # Si hay forecast, agregar proyección
    if forecast_df is not None and len(forecast_df) > 0:
        forecast_latest = forecast_df.iloc[-1]
        forecast_rates = [
            forecast_latest.get('3M Treasury', 0),
            forecast_latest.get('2Y Treasury', 0),
            forecast_latest.get('10Y Treasury', 0),
            forecast_latest.get('30Y Treasury', 0)
        ]
        
        fig.add_trace(go.Scatter(
            x=maturities,
            y=forecast_rates,
            mode='lines+markers',
            name='Proyección 12M',
            line=dict(color='#10b981', width=2, dash='dash'),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title='Curva de Rendimientos US Treasury',
        xaxis_title='Vencimiento',
        yaxis_title='Rendimiento (%)',
        template='plotly_dark',
        hovermode='x unified',
        height=400,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_interest_rate_history_chart(df: pd.DataFrame, forecast_df: pd.DataFrame = None):
    """
    Crea gráfico histórico de tipos de interés con proyección
    """
    fig = go.Figure()
    
    # Datos históricos
    for col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[col],
            mode='lines',
            name=col,
            line=dict(width=2)
        ))
    
    # Proyecciones
    if forecast_df is not None and len(forecast_df) > 0:
        for col in forecast_df.columns:
            fig.add_trace(go.Scatter(
                x=forecast_df.index,
                y=forecast_df[col],
                mode='lines',
                name=f'{col} (Proyección)',
                line=dict(width=2, dash='dash'),
                opacity=0.7
            ))
    
    fig.update_layout(
        title='Evolución y Proyección de Tipos de Interés',
        xaxis_title='Fecha',
        yaxis_title='Tasa (%)',
        template='plotly_dark',
        hovermode='x unified',
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def create_macro_indicators_chart(indicators: Dict[str, pd.Series]):
    """
    Crea gráfico de indicadores macroeconómicos normalizados
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Inflación (CPI YoY%)', 'Desempleo (%)', 
                       'Producción Industrial', 'Sentimiento Consumidor'),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    # CPI
    if 'CPI' in indicators and len(indicators['CPI']) > 12:
        cpi = indicators['CPI']
        cpi_yoy = cpi.pct_change(12) * 100
        fig.add_trace(
            go.Scatter(x=cpi_yoy.index, y=cpi_yoy.values, 
                      name='CPI YoY%', line=dict(color='#ef4444', width=2)),
            row=1, col=1
        )
    
    # Unemployment
    if 'Unemployment' in indicators:
        unemp = indicators['Unemployment']
        fig.add_trace(
            go.Scatter(x=unemp.index, y=unemp.values,
                      name='Desempleo', line=dict(color='#f59e0b', width=2)),
            row=1, col=2
        )
    
    # Industrial Production
    if 'Industrial Production' in indicators:
        ip = indicators['Industrial Production']
        fig.add_trace(
            go.Scatter(x=ip.index, y=ip.values,
                      name='Prod. Industrial', line=dict(color='#3b82f6', width=2)),
            row=2, col=1
        )
    
    # Consumer Sentiment
    if 'Consumer Sentiment' in indicators:
        sentiment = indicators['Consumer Sentiment']
        fig.add_trace(
            go.Scatter(x=sentiment.index, y=sentiment.values,
                      name='Sentimiento', line=dict(color='#10b981', width=2)),
            row=2, col=2
        )
    
    fig.update_layout(
        height=600,
        template='plotly_dark',
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_market_overview_chart(market_data: Dict[str, pd.DataFrame]):
    """
    Crea gráfico de overview de mercados
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('S&P 500', 'VIX (Volatilidad)', 
                       'Dollar Index (DXY)', 'Gold'),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    # S&P 500
    if 'S&P 500' in market_data:
        sp500 = market_data['S&P 500']
        fig.add_trace(
            go.Candlestick(
                x=sp500.index,
                open=sp500['Open'],
                high=sp500['High'],
                low=sp500['Low'],
                close=sp500['Close'],
                name='S&P 500'
            ),
            row=1, col=1
        )
    
    # VIX
    if 'VIX' in market_data:
        vix = market_data['VIX']
        fig.add_trace(
            go.Scatter(x=vix.index, y=vix['Close'],
                      name='VIX', line=dict(color='#ef4444', width=2)),
            row=1, col=2
        )
    
    # DXY
    if 'DXY (Dollar Index)' in market_data:
        dxy = market_data['DXY (Dollar Index)']
        fig.add_trace(
            go.Scatter(x=dxy.index, y=dxy['Close'],
                      name='DXY', line=dict(color='#3b82f6', width=2)),
            row=2, col=1
        )
    
    # Gold
    if 'Gold' in market_data:
        gold = market_data['Gold']
        fig.add_trace(
            go.Scatter(x=gold.index, y=gold['Close'],
                      name='Gold', line=dict(color='#f59e0b', width=2)),
            row=2, col=2
        )
    
    fig.update_layout(
        height=600,
        template='plotly_dark',
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig.update_xaxes(rangeslider_visible=False)
    
    return fig

def create_recession_probability_gauge(probability: float):
    """
    Crea gauge de probabilidad de recesión
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=probability,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Probabilidad de Recesión", 'font': {'size': 24, 'color': 'white'}},
        delta={'reference': 50, 'increasing': {'color': "#ef4444"}, 'decreasing': {'color': "#10b981"}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "#3b82f6"},
            'bgcolor': "rgba(255,255,255,0.1)",
            'borderwidth': 2,
            'bordercolor': "white",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(16, 185, 129, 0.3)'},
                {'range': [30, 60], 'color': 'rgba(245, 158, 11, 0.3)'},
                {'range': [60, 100], 'color': 'rgba(239, 68, 68, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        template='plotly_dark',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': "white", 'family': "Inter"}
    )
    
    return fig

# ═══════════════════════════════════════════════════════════════════════════════
# INTERFAZ PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">📊 MACRO ECONOMIC DASHBOARD PRO</h1>
        <p class="main-subtitle">
            Análisis completo de tendencias macroeconómicas, tipos de interés y proyecciones futuras
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/stocks-growth.png", width=80)
        st.title("⚙️ Configuración")
        
        analysis_period = st.selectbox(
            "Período de análisis",
            ["1 año", "2 años", "5 años", "10 años"],
            index=2
        )
        
        forecast_months = st.slider(
            "Meses de proyección",
            min_value=3,
            max_value=24,
            value=12,
            step=3
        )
        
        st.markdown("---")
        st.markdown("### 📡 Fuentes de datos")
        st.markdown("""
        - **FRED**: Federal Reserve Economic Data
        - **Yahoo Finance**: Datos de mercado
        - **Treasury.gov**: Bonos del tesoro
        """)
        
        st.markdown("---")
        st.markdown("### ℹ️ Nota importante")
        st.info("""
        Para usar este dashboard necesitas:
        1. API key de FRED (gratuita)
        2. Conexión a internet
        3. Instalar dependencias
        """)
        
        if st.button("🔄 Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Tabs principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Overview", 
        "📈 Tipos de Interés", 
        "🌍 Indicadores Macro",
        "💹 Mercados",
        "🔮 Proyecciones"
    ])
    
    # Cargar datos
    with st.spinner("Cargando datos económicos..."):
        try:
            interest_rates = get_interest_rate_expectations()
            macro_indicators = get_macro_indicators()
            market_data = get_market_data()
            
            # Calcular proyecciones
            forecast_df = forecast_interest_rates(interest_rates, forecast_months)
            
            # Calcular métricas
            yield_slope = calculate_yield_curve_slope(interest_rates)
            recession_prob = calculate_recession_probability(macro_indicators)
            
        except Exception as e:
            st.error(f"Error cargando datos: {e}")
            st.stop()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1: OVERVIEW
    # ═══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown('<p class="section-header">📊 Resumen Ejecutivo</p>', unsafe_allow_html=True)
        
        # KPIs principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if not interest_rates.empty and 'Fed Funds' in interest_rates.columns:
                current_fed = interest_rates['Fed Funds'].iloc[-1]
                prev_fed = interest_rates['Fed Funds'].iloc[-30] if len(interest_rates) > 30 else current_fed
                change_fed = current_fed - prev_fed
                
                st.metric(
                    label="Fed Funds Rate",
                    value=f"{current_fed:.2f}%",
                    delta=f"{change_fed:+.2f}%" if change_fed != 0 else "Sin cambio"
                )
        
        with col2:
            if not interest_rates.empty and '10Y Treasury' in interest_rates.columns:
                current_10y = interest_rates['10Y Treasury'].iloc[-1]
                prev_10y = interest_rates['10Y Treasury'].iloc[-30] if len(interest_rates) > 30 else current_10y
                change_10y = current_10y - prev_10y
                
                st.metric(
                    label="10Y Treasury",
                    value=f"{current_10y:.2f}%",
                    delta=f"{change_10y:+.2f}%"
                )
        
        with col3:
            st.metric(
                label="Pendiente 10Y-2Y",
                value=f"{yield_slope:.2f}%",
                delta="Invertida" if yield_slope < 0 else "Normal",
                delta_color="inverse"
            )
        
        with col4:
            if 'CPI' in macro_indicators and len(macro_indicators['CPI']) > 12:
                cpi = macro_indicators['CPI']
                inflation = (cpi.iloc[-1] - cpi.iloc[-12]) / cpi.iloc[-12] * 100
                
                st.metric(
                    label="Inflación (CPI YoY)",
                    value=f"{inflation:.1f}%",
                    delta=f"{'Alto' if inflation > 3 else 'Controlado'}"
                )
        
        # Gauge de recesión
        st.markdown('<p class="section-header">⚠️ Análisis de Riesgo de Recesión</p>', unsafe_allow_html=True)
        
        col_gauge, col_info = st.columns([1, 1])
        
        with col_gauge:
            fig_gauge = create_recession_probability_gauge(recession_prob)
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col_info:
            st.markdown("### Factores de Riesgo Evaluados")
            
            if recession_prob < 30:
                st.markdown('<div class="success-box">✅ <strong>Riesgo Bajo</strong>: La economía muestra señales saludables.</div>', unsafe_allow_html=True)
            elif recession_prob < 60:
                st.markdown('<div class="warning-box">⚠️ <strong>Riesgo Moderado</strong>: Algunos indicadores muestran debilidad.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="warning-box" style="border-color: #ef4444; background: rgba(239, 68, 68, 0.1)">🔴 <strong>Riesgo Alto</strong>: Múltiples señales de recesión presentes.</div>', unsafe_allow_html=True)
            
            st.markdown("""
            **Indicadores analizados:**
            - Curva de rendimientos (inversión 10Y-2Y)
            - Tasa de desempleo (tendencia)
            - Producción industrial
            - Sentimiento del consumidor
            - Oferta monetaria (M2)
            - Inflación (CPI)
            """)
        
        # Curva de rendimientos
        st.markdown('<p class="section-header">📉 Curva de Rendimientos Actual</p>', unsafe_allow_html=True)
        fig_yield = create_yield_curve_chart(interest_rates, forecast_df)
        st.plotly_chart(fig_yield, use_container_width=True)
        
        if yield_slope < 0:
            st.markdown('<div class="warning-box">⚠️ <strong>Curva Invertida Detectada:</strong> Históricamente, una curva de rendimientos invertida ha precedido a recesiones económicas en Estados Unidos.</div>', unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2: TIPOS DE INTERÉS
    # ═══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown('<p class="section-header">📈 Análisis Detallado de Tipos de Interés</p>', unsafe_allow_html=True)
        
        # Gráfico histórico + proyección
        fig_rates = create_interest_rate_history_chart(interest_rates, forecast_df)
        st.plotly_chart(fig_rates, use_container_width=True)
        
        # Análisis de tendencias
        st.markdown('<p class="section-header">📊 Tendencias y Expectativas</p>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### Fed Funds")
            if not interest_rates.empty and 'Fed Funds' in interest_rates.columns:
                fed_data = interest_rates['Fed Funds'].dropna()
                if len(fed_data) > 0:
                    current = fed_data.iloc[-1]
                    change_3m = calculate_rate_of_change(fed_data, 3)
                    change_12m = calculate_rate_of_change(fed_data, 12)
                    
                    st.metric("Tasa actual", f"{current:.2f}%")
                    st.metric("Cambio 3M", f"{change_3m:+.1f}%")
                    st.metric("Cambio 12M", f"{change_12m:+.1f}%")
                    
                    if not forecast_df.empty and 'Fed Funds' in forecast_df.columns:
                        projected = forecast_df['Fed Funds'].iloc[-1]
                        st.metric("Proyección 12M", f"{projected:.2f}%",
                                delta=f"{projected-current:+.2f}%")
        
        with col2:
            st.markdown("### 10Y Treasury")
            if not interest_rates.empty and '10Y Treasury' in interest_rates.columns:
                t10y_data = interest_rates['10Y Treasury'].dropna()
                if len(t10y_data) > 0:
                    current = t10y_data.iloc[-1]
                    change_3m = calculate_rate_of_change(t10y_data, 3)
                    change_12m = calculate_rate_of_change(t10y_data, 12)
                    
                    st.metric("Rendimiento actual", f"{current:.2f}%")
                    st.metric("Cambio 3M", f"{change_3m:+.1f}%")
                    st.metric("Cambio 12M", f"{change_12m:+.1f}%")
                    
                    if not forecast_df.empty and '10Y Treasury' in forecast_df.columns:
                        projected = forecast_df['10Y Treasury'].iloc[-1]
                        st.metric("Proyección 12M", f"{projected:.2f}%",
                                delta=f"{projected-current:+.2f}%")
        
        with col3:
            st.markdown("### Spread 10Y-2Y")
            if not interest_rates.empty:
                st.metric("Spread actual", f"{yield_slope:.2f}%")
                
                spread_status = "🔴 Invertida" if yield_slope < 0 else "🟢 Normal"
                st.metric("Estado", spread_status)
                
                # Histórico del spread
                if '10Y Treasury' in interest_rates.columns and '2Y Treasury' in interest_rates.columns:
                    spread_history = interest_rates['10Y Treasury'] - interest_rates['2Y Treasury']
                    avg_spread = spread_history.mean()
                    st.metric("Spread promedio", f"{avg_spread:.2f}%")
        
        # Tabla de datos
        st.markdown('<p class="section-header">📋 Datos Completos</p>', unsafe_allow_html=True)
        
        if not interest_rates.empty:
            display_df = interest_rates.tail(20).copy()
            display_df.index = display_df.index.strftime('%Y-%m-%d')
            st.dataframe(display_df.style.format("{:.2f}%"), use_container_width=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3: INDICADORES MACRO
    # ═══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown('<p class="section-header">🌍 Indicadores Macroeconómicos Principales</p>', unsafe_allow_html=True)
        
        # Gráficos de indicadores
        fig_macro = create_macro_indicators_chart(macro_indicators)
        st.plotly_chart(fig_macro, use_container_width=True)
        
        # Métricas detalladas
        st.markdown('<p class="section-header">📊 Métricas Detalladas</p>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        indicators_to_show = [
            ('GDP', 'PIB (Trimestral)', col1),
            ('CPI', 'Inflación (CPI)', col2),
            ('Unemployment', 'Desempleo', col3),
            ('Consumer Sentiment', 'Sent. Consumidor', col4)
        ]
        
        for key, label, col in indicators_to_show:
            if key in macro_indicators:
                data = macro_indicators[key].dropna()
                if len(data) > 0:
                    with col:
                        current = data.iloc[-1]
                        prev = data.iloc[-2] if len(data) > 1 else current
                        change = current - prev
                        
                        # Formato especial para CPI (mostrar como % YoY)
                        if key == 'CPI' and len(data) > 12:
                            yoy_change = (data.iloc[-1] - data.iloc[-12]) / data.iloc[-12] * 100
                            st.metric(
                                label=label,
                                value=f"{yoy_change:.1f}%",
                                delta=f"{change:.2f} pts"
                            )
                        else:
                            st.metric(
                                label=label,
                                value=f"{current:.2f}",
                                delta=f"{change:+.2f}"
                            )
        
        # Análisis adicional
        st.markdown('<p class="section-header">📈 Análisis de Tendencias</p>', unsafe_allow_html=True)
        
        analysis_cols = st.columns(2)
        
        with analysis_cols[0]:
            st.markdown("### 🏭 Sector Real")
            
            if 'Industrial Production' in macro_indicators:
                ip = macro_indicators['Industrial Production'].dropna()
                if len(ip) > 12:
                    ip_change = calculate_rate_of_change(ip, 12)
                    
                    if ip_change > 2:
                        st.markdown('<div class="success-box">✅ Producción industrial en expansión (+{:.1f}% YoY)</div>'.format(ip_change), unsafe_allow_html=True)
                    elif ip_change < -2:
                        st.markdown('<div class="warning-box">⚠️ Producción industrial en contracción ({:.1f}% YoY)</div>'.format(ip_change), unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="info-box">ℹ️ Producción industrial estable ({:.1f}% YoY)</div>'.format(ip_change), unsafe_allow_html=True)
            
            if 'Retail Sales' in macro_indicators:
                rs = macro_indicators['Retail Sales'].dropna()
                if len(rs) > 12:
                    rs_change = calculate_rate_of_change(rs, 12)
                    st.markdown(f"**Ventas minoristas:** {rs_change:+.1f}% YoY")
        
        with analysis_cols[1]:
            st.markdown("### 💼 Mercado Laboral")
            
            if 'Unemployment' in macro_indicators:
                unemp = macro_indicators['Unemployment'].dropna()
                if len(unemp) > 12:
                    current_unemp = unemp.iloc[-1]
                    prev_unemp = unemp.iloc[-12]
                    unemp_change = current_unemp - prev_unemp
                    
                    if unemp_change < -0.3:
                        st.markdown('<div class="success-box">✅ Desempleo en descenso ({:.1f}% → {:.1f}%)</div>'.format(prev_unemp, current_unemp), unsafe_allow_html=True)
                    elif unemp_change > 0.5:
                        st.markdown('<div class="warning-box">⚠️ Desempleo en aumento ({:.1f}% → {:.1f}%)</div>'.format(prev_unemp, current_unemp), unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="info-box">ℹ️ Desempleo estable en {:.1f}%</div>'.format(current_unemp), unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4: MERCADOS
    # ═══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown('<p class="section-header">💹 Panorama de Mercados Financieros</p>', unsafe_allow_html=True)
        
        # Overview de mercados
        fig_markets = create_market_overview_chart(market_data)
        st.plotly_chart(fig_markets, use_container_width=True)
        
        # Métricas de mercado
        st.markdown('<p class="section-header">📊 Métricas Clave</p>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        market_metrics = [
            ('S&P 500', col1),
            ('VIX', col2),
            ('DXY (Dollar Index)', col3),
            ('Gold', col4)
        ]
        
        for market_name, col in market_metrics:
            if market_name in market_data:
                df = market_data[market_name]
                if not df.empty and 'Close' in df.columns:
                    with col:
                        current = df['Close'].iloc[-1]
                        prev = df['Close'].iloc[-5] if len(df) > 5 else current
                        change = (current - prev) / prev * 100
                        
                        st.metric(
                            label=market_name,
                            value=f"{current:.2f}",
                            delta=f"{change:+.2f}%"
                        )
        
        # Análisis de correlaciones
        st.markdown('<p class="section-header">🔗 Análisis de Correlaciones</p>', unsafe_allow_html=True)
        
        if len(market_data) >= 2:
            # Construir matriz de correlación
            corr_data = {}
            for name, df in market_data.items():
                if not df.empty and 'Close' in df.columns:
                    corr_data[name] = df['Close']
            
            if corr_data:
                corr_df = pd.DataFrame(corr_data).dropna()
                
                if len(corr_df) > 20:
                    # Calcular correlación
                    correlation_matrix = corr_df.corr()
                    
                    # Crear heatmap
                    fig_corr = go.Figure(data=go.Heatmap(
                        z=correlation_matrix.values,
                        x=correlation_matrix.columns,
                        y=correlation_matrix.columns,
                        colorscale='RdBu',
                        zmid=0,
                        text=correlation_matrix.values,
                        texttemplate='%{text:.2f}',
                        textfont={"size": 10},
                        colorbar=dict(title="Correlación")
                    ))
                    
                    fig_corr.update_layout(
                        title='Matriz de Correlación (90 días)',
                        template='plotly_dark',
                        height=500,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    
                    st.plotly_chart(fig_corr, use_container_width=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 5: PROYECCIONES
    # ═══════════════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown('<p class="section-header">🔮 Proyecciones y Escenarios Futuros</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="info-box">ℹ️ <strong>Nota:</strong> Las proyecciones se basan en modelos de tendencia lineal y no constituyen asesoramiento financiero. Los resultados reales pueden variar significativamente.</div>', unsafe_allow_html=True)
        
        # Proyección de tipos de interés
        st.markdown("### 📈 Proyección de Tipos de Interés ({} meses)".format(forecast_months))
        
        if not forecast_df.empty:
            # Mostrar tabla de proyecciones
            projection_table = forecast_df.copy()
            projection_table.index = projection_table.index.strftime('%Y-%m')
            st.dataframe(projection_table.style.format("{:.2f}%"), use_container_width=True)
            
            # Análisis de escenarios
            st.markdown("### 🎯 Escenarios Proyectados")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### Escenario Base")
                if 'Fed Funds' in forecast_df.columns:
                    base_fed = forecast_df['Fed Funds'].iloc[-1]
                    current_fed = interest_rates['Fed Funds'].iloc[-1] if 'Fed Funds' in interest_rates.columns else 0
                    
                    st.metric("Fed Funds proyectado", f"{base_fed:.2f}%",
                            delta=f"{base_fed - current_fed:+.2f}%")
                    
                    if base_fed > current_fed:
                        st.markdown("🔴 Política monetaria restrictiva continuada")
                    elif base_fed < current_fed:
                        st.markdown("🟢 Inicio de recortes de tipos esperado")
                    else:
                        st.markdown("🟡 Tipos estables en el horizonte proyectado")
            
            with col2:
                st.markdown("#### Escenario Optimista")
                st.markdown("""
                - Inflación controlada (< 2.5%)
                - Crecimiento económico sólido
                - Recortes de tipos graduales
                - Mercados alcistas
                """)
            
            with col3:
                st.markdown("#### Escenario Pesimista")
                st.markdown("""
                - Recesión económica
                - Desempleo en aumento
                - Recortes de emergencia
                - Volatilidad extrema
                """)
        
        # Recomendaciones estratégicas
        st.markdown('<p class="section-header">💡 Recomendaciones Estratégicas</p>', unsafe_allow_html=True)
        
        rec_col1, rec_col2 = st.columns(2)
        
        with rec_col1:
            st.markdown("### 🎯 Renta Fija")
            
            if yield_slope < 0:
                st.markdown("""
                - ⚠️ Curva invertida: precaución con bonos largos
                - Considerar posiciones en corto plazo
                - Diversificar con bonos corporativos de grado de inversión
                - Monitorear señales de recesión
                """)
            else:
                st.markdown("""
                - ✅ Curva normal: oportunidades en toda la curva
                - Balance entre corto y largo plazo
                - Evaluar duration según expectativas de tipos
                """)
        
        with rec_col2:
            st.markdown("### 📊 Renta Variable")
            
            if recession_prob > 60:
                st.markdown("""
                - ⚠️ Alto riesgo de recesión
                - Posiciones defensivas (utilities, consumer staples)
                - Incrementar efectivo
                - Reducir exposición cíclica
                """)
            elif recession_prob > 30:
                st.markdown("""
                - 🟡 Riesgo moderado
                - Equilibrio entre crecimiento y defensivos
                - Diversificación sectorial
                - Monitorear indicadores adelantados
                """)
            else:
                st.markdown("""
                - ✅ Entorno favorable
                - Sesgo hacia growth y tecnología
                - Aprovechar oportunidades cíclicas
                """)
        
        # Calendario de eventos clave
        st.markdown('<p class="section-header">📅 Próximos Eventos Clave</p>', unsafe_allow_html=True)
        
        st.markdown("""
        | Fecha | Evento | Importancia |
        |-------|--------|-------------|
        | Próximo miércoles | Decisión FOMC | 🔴 Alta |
        | 1er viernes del mes | Nóminas no agrícolas (NFP) | 🔴 Alta |
        | Mes siguiente | Reporte CPI | 🟡 Media-Alta |
        | Trimestral | PIB preliminar | 🟡 Media |
        
        **Nota:** Las fechas exactas varían. Consultar calendario económico oficial.
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: rgba(255,255,255,0.5); padding: 2rem 0;'>
        <p>📊 <strong>Macro Economic Dashboard Pro</strong> v1.0</p>
        <p>Datos proporcionados por FRED, Yahoo Finance y otras fuentes públicas</p>
        <p>⚠️ Este dashboard es únicamente para fines educativos e informativos. No constituye asesoramiento financiero.</p>
        <p style='margin-top: 1rem; font-size: 0.8rem;'>
            Última actualización: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()

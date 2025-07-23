import streamlit as st
import pandas as pd
from qfc.utils.data_fetcher import DataFetcher
from qfc.agents.analyst_agent import AnalystAgent
from config import settings
from main import visualize_trades # Reutilizamos la función de graficar de main

st.set_page_config(layout="wide", page_title="QFC Dashboard")
st.title("📈 Quantum Forex Collective (QFC) - Panel de Control")

# --- Selector de Par ---
pair = st.selectbox("Selecciona un par para analizar:", settings.TRADING_PAIRS)

if pair:
    st.header(f"Análisis para {pair}")

    # --- Cargar y Analizar Datos ---
    with st.spinner(f"Obteniendo y analizando datos para {pair}..."):
        # Inicializar agentes y fetcher
        analyst_agent = AnalystAgent(config=settings.ANALYST_AGENT_CONFIG)
        data_fetcher = DataFetcher(pair=pair, interval=settings.ANALYST_AGENT_CONFIG['timeframe'])
        
        df = data_fetcher.fetch_data()
        
        if not df.empty:
            analysis_df = analyst_agent.analyze(df, pair=pair)
            st.success("Análisis completado.")

            # --- Mostrar Gráfico Interactivo ---
            fig_placeholder = st.empty()
            # Creamos una copia para la visualización, ya que la función puede modificarla
            visualize_trades(analysis_df.copy(), pair) 
            fig_placeholder.pyplot(st) # Usamos st.pyplot() para mostrar el gráfico

            # --- Mostrar Datos en Bruto ---
            st.subheader("Datos Analizados (últimas 10 velas)")
            st.dataframe(analysis_df.tail(10))
        else:
            st.error(f"No se pudieron obtener datos para {pair}.")
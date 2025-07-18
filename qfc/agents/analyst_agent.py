# qfc/agents/analyst_agent.py (versión final corregida)

import pandas as pd
import numpy as np
from config.logger_config import log

# Se movió la función de cálculo de ATR aquí para que sea autónoma
def _calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

class AnalystAgent:
    def __init__(self, config: dict):
        """
        Inicializa el Agente Analista.
        """
        self.strategy_name = config.get("strategy_name", "Unnamed Strategy")
        
        # --- CORRECCIÓN AQUÍ ---
        # Nos aseguramos de que los nombres de los atributos sean los que usa el método 'analyze'.
        self.sma_short_window = config.get("sma_short_window", 50)
        self.sma_long_window = config.get("sma_long_window", 200)
        # ---------------------
        
        log.info(f"Agente Analista inicializado con la estrategia '{self.strategy_name}'.")

    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica la estrategia de análisis técnico al DataFrame de datos.
        """
        if data.empty:
            return pd.DataFrame()

        # 1. Calcular todos los indicadores necesarios
        data['atr'] = _calculate_atr(data, period=14)
        
        short_sma_col = f'sma_{self.sma_short_window}'
        long_sma_col = f'sma_{self.sma_long_window}'
        
        log.info(f"Calculando {short_sma_col} y {long_sma_col}...")
        data[short_sma_col] = data['close'].rolling(window=self.sma_short_window).mean()
        data[long_sma_col] = data['close'].rolling(window=self.sma_long_window).mean()
        
        # 2. Eliminar filas con NaNs después de calcular TODOS los indicadores
        data.dropna(inplace=True)
        if data.empty:
            log.warning("El DataFrame quedó vacío después de eliminar NaNs. No se puede continuar el análisis.")
            return pd.DataFrame()

        # 3. Generar las señales de trading
        log.info("Generando señales de trading...")
        # 'signal' representa la tendencia actual: 1 si la SMA corta está por encima de la larga, -1 si está por debajo.
        data['signal'] = np.where(data[short_sma_col] > data[long_sma_col], 1, -1)
        
        # 'position' detecta el evento del cruce. Es 1.0 el día del cruce al alza, -1.0 el día del cruce a la baja.
        # Se convierte a 2.0 (-2.0) si la señal cambia de -1 a 1 (o viceversa), lo cual es lo que buscamos.
        # Usamos .diff() para detectar este cambio.
        data['position'] = data['signal'].diff()
        
        log.info("Señales generadas.")
        return data
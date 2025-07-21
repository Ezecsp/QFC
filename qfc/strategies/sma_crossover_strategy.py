import pandas as pd
import numpy as np
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

# La función para calcular el ATR es necesaria para el Coordinador.
def _calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

class SmaCrossoverStrategy(BaseStrategy):
    """
    Estrategia de trading basada en el cruce de dos medias móviles simples (SMA).
    """
    def __init__(self, config: dict):
        super().__init__(config)
        self.sma_short_window = self.config.get("sma_short_window", 20)
        self.sma_long_window = self.config.get("sma_long_window", 50)
        log.info(f"Estrategia 'SMACrossover' inicializada con ventanas {self.sma_short_window}/{self.sma_long_window}.")

    def analyze(self, data, pair: str) -> pd.DataFrame:
        log.info("Ejecutando análisis de estrategia: SMACrossover...")
        
        df = data.copy()

        # Aseguramos que el ATR esté presente para que el Coordinador lo use
        if 'atr' not in df.columns:
            df['atr'] = _calculate_atr(df, period=14)

        # Usamos prefijos en las columnas para evitar conflictos con otras estrategias
        short_sma_col = f'sma_short'
        long_sma_col = f'sma_long'
        
        df[short_sma_col] = df['close'].rolling(window=self.sma_short_window).mean()
        df[long_sma_col] = df['close'].rolling(window=self.sma_long_window).mean()
        
        # Generamos las señales de la estrategia
        df['signal'] = np.where(df[short_sma_col] > df[long_sma_col], 1, -1)
        df['position'] = df['signal'].diff().fillna(0) # Rellenamos NaNs con 0
        
        log.info("Análisis de SMACrossover completado.")
        return df
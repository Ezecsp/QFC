import pandas as pd
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class MarketStructureShiftStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        self.lookback = self.config.get("lookback", 20)
        self.mss_lookback = self.config.get("mss_lookback", 10)
        log.info("Estrategia 'MarketStructureShift' (LG+MSS) inicializada.")

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis de Market Structure Shift para {pair}...")
        df = data.copy()
        df['mss_signal'] = 0

        # Iteramos solo en las últimas N velas para eficiencia
        recent_data = df.tail(200).copy()
        for i in range(self.lookback + 1, len(recent_data)):
            liquidity_window = recent_data.iloc[i - self.lookback : i]
            
            # Señal Alcista: Captura de liquidez bajista + MSS alcista
            low_to_beat = liquidity_window['low'].min()
            if recent_data['low'].iloc[i] < low_to_beat:
                mss_high_level = liquidity_window['high'].max()
                for j in range(i + 1, len(recent_data)):
                    if recent_data['high'].iloc[j] > mss_high_level:
                        df.at[recent_data.index[j], 'mss_signal'] = 1
                        break

            # Señal Bajista: Captura de liquidez alcista + MSS bajista
            high_to_beat = liquidity_window['high'].max()
            if recent_data['high'].iloc[i] > high_to_beat:
                mss_low_level = liquidity_window['low'].min()
                for k in range(i + 1, len(recent_data)):
                    if recent_data['low'].iloc[k] < mss_low_level:
                        df.at[recent_data.index[k], 'mss_signal'] = -1
                        break
        return df
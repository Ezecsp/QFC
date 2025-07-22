import pandas as pd
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class OrderBlockStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        self.lookback = self.config.get("lookback", 75)
        self.breakout_candles = self.config.get("breakout_candles", 3)
        log.info("Estrategia 'OrderBlockStrategy' (con Confirmación) inicializada.")

    def _find_order_blocks(self, df: pd.DataFrame) -> list:
        obs = []
        subset = df.tail(self.lookback)
        for i in range(len(subset) - self.breakout_candles):
            candle = subset.iloc[i]
            if candle['close'] < candle['open']:
                breakout_move = subset.iloc[i+1 : i+1+self.breakout_candles]
                if all(breakout_move['close'] > breakout_move['open']) and breakout_move['high'].max() > candle['high']:
                    obs.append((candle['low'], candle['high'], 'bullish'))
            if candle['close'] > candle['open']:
                breakout_move = subset.iloc[i+1 : i+1+self.breakout_candles]
                if all(breakout_move['close'] < breakout_move['open']) and breakout_move['low'].min() < candle['low']:
                    obs.append((candle['low'], candle['high'], 'bearish'))
        return obs

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis de Order Blocks con Confirmación para {pair}...")
        df = data.copy()
        
        order_blocks = self._find_order_blocks(df)
        df['ob_zones'] = [order_blocks] * len(df)
        df['ob_signal'] = 0

        for i in range(1, len(df)):
            previous_candle = df.iloc[i-1]
            current_candle_index = df.index[i]

            for low, high, ob_type in order_blocks:
                # 1. ¿Vela ANTERIOR tocó el OB?
                if previous_candle['low'] <= high and previous_candle['high'] >= low:
                    if ob_type == 'bullish' and previous_candle['close'] > previous_candle['open']:
                        df.at[current_candle_index, 'ob_signal'] = 1
                    elif ob_type == 'bearish' and previous_candle['close'] < previous_candle['open']:
                        df.at[current_candle_index, 'ob_signal'] = -1
        return df
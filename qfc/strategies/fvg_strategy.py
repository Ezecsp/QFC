import pandas as pd
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class FvgStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        self.min_size_pct = self.config.get("min_size_pct", 0.001)
        log.info("Estrategia 'FvgStrategy' (con filtro y Confirmación) inicializada.")

    def _find_fvgs(self, df: pd.DataFrame) -> list:
        fvgs = []
        df['fvg_bullish'] = (df['low'].shift(-1) > df['high'].shift(1))
        df['fvg_bearish'] = (df['high'].shift(-1) < df['low'].shift(1))
        for i in range(1, len(df) - 1):
            is_bullish, is_bearish = df['fvg_bullish'].iloc[i], df['fvg_bearish'].iloc[i]
            if is_bullish or is_bearish:
                top = df['low'].iloc[i+1] if is_bullish else df['high'].iloc[i+1]
                bottom = df['high'].iloc[i-1] if is_bullish else df['low'].iloc[i-1]
                if abs(top - bottom) > df['close'].iloc[i] * self.min_size_pct:
                    fvgs.append((bottom, top, 'bullish' if is_bullish else 'bearish'))
        return fvgs

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis de FVG con Confirmación para {pair}...")
        df = data.copy()
        
        all_fvgs = self._find_fvgs(df)
        unmitigated_fvgs = [fvg for fvg in all_fvgs if (fvg[2] == 'bullish' and fvg[0] > df.tail(100)['low'].min()) or (fvg[2] == 'bearish' and fvg[1] < df.tail(100)['high'].max())]

        df['fvg_zones'] = [unmitigated_fvgs] * len(df)
        df['fvg_signal'] = 0

        for i in range(1, len(df)):
            previous_candle = df.iloc[i-1]
            current_candle_index = df.index[i]
            for start, end, fvg_type in unmitigated_fvgs:
                if fvg_type == 'bullish' and previous_candle['low'] <= end:
                    if previous_candle['close'] > previous_candle['open']:
                        df.at[current_candle_index, 'fvg_signal'] = 1
                elif fvg_type == 'bearish' and previous_candle['high'] >= start:
                    if previous_candle['close'] < previous_candle['open']:
                        df.at[current_candle_index, 'fvg_signal'] = -1
        return df
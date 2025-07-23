import pandas as pd
from scipy.signal import find_peaks
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

def _cluster_levels_into_zones(levels: list, threshold_pct: float=0.002) -> list:
    if not levels: return []
    levels.sort()
    zones, current_zone_start = [], levels[0]
    for i in range(1, len(levels)):
        if levels[i] > current_zone_start * (1 + threshold_pct):
            zones.append((current_zone_start, levels[i-1]))
            current_zone_start = levels[i]
    zones.append((current_zone_start, levels[-1]))
    return zones

class SupportResistanceStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        self.lookback_period = self.config.get("lookback_period", 90)
        self.peak_distance = self.config.get("peak_distance", 5)
        log.info("Estrategia 'SupportResistance' (con Vela de Momentum) inicializada.")

    def analyze(self, data, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis S/R con Momentum para {pair}...")
        df = data.copy()
        
        lookback_data = df.tail(self.lookback_period)
        resistance_indices, _ = find_peaks(lookback_data['high'], distance=self.peak_distance)
        support_indices, _ = find_peaks(-lookback_data['low'], distance=self.peak_distance)
        resistance_zones = _cluster_levels_into_zones(lookback_data['high'].iloc[resistance_indices].unique().tolist())
        support_zones = _cluster_levels_into_zones(lookback_data['low'].iloc[support_indices].unique().tolist())

        df['sr_position'] = 0
        df['avg_body_size'] = abs(df['close'] - df['open']).rolling(window=30).mean()
        
        prev_low = df['low'].shift(1)
        prev_high = df['high'].shift(1)
        prev_body_size = abs(df['close'].shift(1) - df['open'].shift(1))
        avg_body_size_prev = df['avg_body_size'].shift(1)

        is_bullish_momentum = (df['close'].shift(1) > df['open'].shift(1)) & (prev_body_size > avg_body_size_prev)
        is_bearish_momentum = (df['close'].shift(1) < df['open'].shift(1)) & (prev_body_size > avg_body_size_prev)

        buy_mask = pd.Series(False, index=df.index)
        sell_mask = pd.Series(False, index=df.index)
        for zone_start, zone_end in support_zones: buy_mask |= (prev_low <= zone_end) & is_bullish_momentum
        for zone_start, zone_end in resistance_zones: sell_mask |= (prev_high >= zone_start) & is_bearish_momentum
        
        df.loc[buy_mask, 'sr_position'] = 1
        df.loc[sell_mask, 'sr_position'] = -1

        return df.drop(columns=['avg_body_size'])
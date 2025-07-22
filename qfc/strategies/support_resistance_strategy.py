import pandas as pd
from scipy.signal import find_peaks
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

def _cluster_levels_into_zones(levels: list, threshold_pct: float) -> list:
    if not levels: return []
    levels.sort()
    zones = []
    current_zone_start = levels[0]
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
        self.zone_threshold_pct = self.config.get("zone_creation_threshold_pct", 0.002)
        log.info("Estrategia 'SupportResistance' (con Zonas y Confirmación) inicializada.")

    def analyze(self, data, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis de S/R con Confirmación para {pair}...")
        df = data.copy()
        
        lookback_data = df.iloc[-self.lookback_period:]
        resistance_indices, _ = find_peaks(lookback_data['high'], distance=self.peak_distance)
        support_indices, _ = find_peaks(-lookback_data['low'], distance=self.peak_distance)
        raw_resistance_levels = lookback_data['high'].iloc[resistance_indices].unique().tolist()
        raw_support_levels = lookback_data['low'].iloc[support_indices].unique().tolist()
        resistance_zones = _cluster_levels_into_zones(raw_resistance_levels, self.zone_threshold_pct)
        support_zones = _cluster_levels_into_zones(raw_support_levels, self.zone_threshold_pct)

        df['resistance_zones'] = [resistance_zones] * len(df)
        df['support_zones'] = [support_zones] * len(df)
        df['sr_position'] = 0

        # Lógica de vela de confirmación: miramos la vela anterior para generar señal en la actual
        for i in range(1, len(df)):
            previous_candle = df.iloc[i-1]
            current_candle_index = df.index[i]
            
            # Chequear rebote en zonas de soporte
            for zone_start, zone_end in support_zones:
                # 1. ¿Vela ANTERIOR tocó o atravesó la zona?
                if previous_candle['low'] <= zone_end:
                    # 2. ¿Vela ANTERIOR cerró como una vela de confirmación alcista?
                    if previous_candle['close'] > previous_candle['open']:
                        # 3. Señal en la vela ACTUAL
                        df.at[current_candle_index, 'sr_position'] = 1
            
            # Chequear rechazo en zonas de resistencia
            for zone_start, zone_end in resistance_zones:
                # 1. ¿Vela ANTERIOR tocó o atravesó la zona?
                if previous_candle['high'] >= zone_start:
                    # 2. ¿Vela ANTERIOR cerró como una vela de confirmación bajista?
                    if previous_candle['close'] < previous_candle['open']:
                        # 3. Señal en la vela ACTUAL
                        df.at[current_candle_index, 'sr_position'] = -1
                        
        return df
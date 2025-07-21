import pandas as pd
from scipy.signal import find_peaks
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

def _cluster_levels_into_zones(levels: list, threshold_pct: float) -> list:
    """
    Agrupa niveles de precios cercanos en zonas.
    
    Args:
        levels (list): Lista de precios de soporte o resistencia.
        threshold_pct (float): El porcentaje de diferencia para agrupar niveles.
    
    Returns:
        list: Una lista de tuplas, donde cada tupla es una zona (inicio, fin).
    """
    if not levels:
        return []
    
    levels.sort()
    
    zones = []
    current_zone_start = levels[0]
    
    for i in range(1, len(levels)):
        # Si el nivel actual está muy lejos del inicio de la zona, cerramos la zona actual
        if levels[i] > current_zone_start * (1 + threshold_pct):
            zones.append((current_zone_start, levels[i-1]))
            current_zone_start = levels[i]

    # Añadir la última zona
    zones.append((current_zone_start, levels[-1]))
    
    return zones

class SupportResistanceStrategy(BaseStrategy):
    """
    Estrategia que identifica ZONAS de soporte/resistencia y genera señales.
    """
    def __init__(self, config: dict):
        super().__init__(config)
        self.lookback_period = self.config.get("lookback_period", 90)
        self.peak_distance = self.config.get("peak_distance", 5)
        self.touch_proximity_pct = self.config.get("touch_proximity_pct", 0.001)
        # Nuevo: umbral para crear las zonas
        self.zone_threshold_pct = self.config.get("zone_creation_threshold_pct", 0.002) # 0.2%
        log.info("Estrategia 'SupportResistance' (con Zonas) inicializada.")

    def analyze(self, data, pair: str) -> pd.DataFrame:
        log.info("Ejecutando análisis de estrategia: SupportResistance (con Zonas)...")
        df = data.copy()
        
        lookback_data = df.iloc[-self.lookback_period:]
        resistance_indices, _ = find_peaks(lookback_data['high'], distance=self.peak_distance)
        support_indices, _ = find_peaks(-lookback_data['low'], distance=self.peak_distance)
        
        raw_resistance_levels = lookback_data['high'].iloc[resistance_indices].unique().tolist()
        raw_support_levels = lookback_data['low'].iloc[support_indices].unique().tolist()

        resistance_zones = _cluster_levels_into_zones(raw_resistance_levels, self.zone_threshold_pct)
        support_zones = _cluster_levels_into_zones(raw_support_levels, self.zone_threshold_pct)

        log.info(f"Zonas de Resistencia identificadas: {[(f'{z[0]:.4f}', f'{z[1]:.4f}') for z in resistance_zones]}")
        log.info(f"Zonas de Soporte identificadas: {[(f'{z[0]:.4f}', f'{z[1]:.4f}') for z in support_zones]}")

        # Guardamos las zonas
        df['resistance_zones'] = [resistance_zones] * len(df)
        df['support_zones'] = [support_zones] * len(df)
        df['sr_position'] = 0

        # Lógica de señales adaptada para zonas
        for i in range(len(df)):
            current_low = df['low'].iloc[i]
            current_high = df['high'].iloc[i]
            current_close = df['close'].iloc[i]
            
            # Chequear rebote en zonas de soporte
            for zone_start, zone_end in support_zones:
                # Si el 'low' de la vela entró en la zona de soporte...
                if current_low <= zone_end * (1 + self.touch_proximity_pct):
                    # ...y cerró por encima de la zona.
                    if current_close > zone_end:
                        df.at[df.index[i], 'sr_position'] = 1
            
            # Chequear rechazo en zonas de resistencia
            for zone_start, zone_end in resistance_zones:
                # Si el 'high' de la vela entró en la zona de resistencia...
                if current_high >= zone_start * (1 - self.touch_proximity_pct):
                     # ...y cerró por debajo de la zona.
                    if current_close < zone_start:
                        df.at[df.index[i], 'sr_position'] = -1
                        
        return df
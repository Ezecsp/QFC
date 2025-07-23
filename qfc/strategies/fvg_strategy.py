import pandas as pd
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class FvgStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        self.min_size_pct = self.config.get("min_size_pct", 0.001)
        log.info("Estrategia 'FvgStrategy' (Hiper-Optimizada) inicializada.")

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis de FVG Hiper-Optimizado para {pair}...")
        df = data.copy()

        # --- Vectorización Completa para la detección de FVG ---
        high_prev = df['high'].shift(1)
        low_prev = df['low'].shift(1)
        low_next = df['low'].shift(-1)
        high_next = df['high'].shift(-1)

        # Condiciones para la FORMACIÓN de un FVG
        bullish_fvg_created = (low_next > high_prev)
        bearish_fvg_created = (high_next < low_prev)
        
        # Guardamos dónde se crearon los FVGs y sus límites
        df['bullish_fvg_top'] = low_next
        df['bullish_fvg_bottom'] = high_prev
        df['bearish_fvg_top'] = high_next
        df['bearish_fvg_bottom'] = low_prev
        
        # Llenamos hacia adelante los FVG no mitigados para saber qué zonas están activas
        df['active_bull_fvg_bottom'] = df.where(bullish_fvg_created)['bullish_fvg_bottom'].ffill()
        df['active_bear_fvg_top'] = df.where(bearish_fvg_created)['bearish_fvg_top'].ffill()

        # --- Vectorización de la lógica de TESTEO y CONFIRMACIÓN ---
        prev_low = df['low'].shift(1)
        prev_high = df['high'].shift(1)
        is_bullish_confirmation = (df['close'].shift(1) > df['open'].shift(1))
        is_bearish_confirmation = (df['close'].shift(1) < df['open'].shift(1))

        # Señal de compra: la vela anterior tocó un FVG alcista activo Y fue una vela de confirmación
        buy_signal = (prev_low <= df['active_bull_fvg_bottom']) & is_bullish_confirmation
        
        # Señal de venta: la vela anterior tocó un FVG bajista activo Y fue una vela de confirmación
        sell_signal = (prev_high >= df['active_bear_fvg_top']) & is_bearish_confirmation

        df['fvg_signal'] = 0
        df.loc[buy_signal, 'fvg_signal'] = 1
        df.loc[sell_signal, 'fvg_signal'] = -1
        
        # Limpieza de columnas auxiliares
        df.drop(columns=[
            'bullish_fvg_top', 'bullish_fvg_bottom', 'bearish_fvg_top', 'bearish_fvg_bottom',
            'active_bull_fvg_bottom', 'active_bear_fvg_top'
        ], inplace=True)
        
        df['fvg_zones'] = [[] for _ in range(len(df))]

        return df
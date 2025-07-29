import pandas as pd
import numpy as np
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class CombinedFiboStrategy(BaseStrategy):
    """
    Estrategia combinada que incorpora elementos de:
    - CambioEstructuraFibo (Patrón específico de 3 velas + Fibo 61.8%)
    - TendenciaBasicaFibo (Nivel de retroceso de Fibo 61.8% estándar)
    - ParidadVelaFibo (Vela de alto volumen + retorno al precio)
    """

    def __init__(self, config: dict):
        super().__init__(config)

        # Configuración para CambioEstructuraFibo
        # (Usamos un patrón fijo de 3 velas como en el MQL5 original)
        self.cambio_estructura_bars = 3

        # Configuración para TendenciaBasicaFibo
        self.tendencia_basica_period = self.config.get("tendencia_basica_period", 10)

        # Configuración para ParidadVelaFibo
        self.paridad_volume_threshold = self.config.get("paridad_volume_threshold", None) # Si es None, se calcula dinámicamente
        self.paridad_lookback_window = self.config.get("paridad_lookback_window", 20)
        self.paridad_touch_threshold_pct = self.config.get("paridad_touch_threshold_pct", 0.002) # 0.2% por defecto

        # Umbral de proximidad para señales de Fibo (porcentaje del precio)
        self.fibo_touch_threshold_pct = self.config.get("fibo_touch_threshold_pct", 0.002) # 0.2% por defecto

        log.info("Estrategia 'CombinedFiboStrategy' inicializada.")

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        """
        Aplica el análisis combinado de Fibonacci.
        Añade una columna 'combined_fibo_signal' con valores:
        - 1: Señal de Compra
        - -1: Señal de Venta (puede añadirse lógica específica si se desea)
        - 0: Sin señal
        """
        log.info(f"Ejecutando análisis de CombinedFiboStrategy para {pair}...")
        df = data.copy()

        # Inicializar columna de señales
        df['combined_fibo_signal'] = 0

        # --- 1. Lógica de CambioEstructuraFibo ---
        # Buscar el patrón: vela 1 (high), vela 2 (low), vela 3 (cerca del 61.8%)
        # Ajustamos para usar las últimas N velas para eficiencia
        lookback_window_cambio = max(self.cambio_estructura_bars, 100) # Revisar últimas 100 velas
        recent_data_cambio = df.tail(lookback_window_cambio).copy()

        for i in range(2, len(recent_data_cambio)): # Necesitamos al menos 3 velas (índices 0,1,2)
            # Índices en el DataFrame recortado
            idx_0 = recent_data_cambio.index[i - 2] # Vela 1 (potencial high)
            idx_1 = recent_data_cambio.index[i - 1] # Vela 2 (potencial low)
            idx_2 = recent_data_cambio.index[i]     # Vela 3 (verificación)

            # Verificar patrón: high[idx_0] > low[idx_1] y close[idx_2] cerca del 61.8%
            if (recent_data_cambio.loc[idx_0, 'high'] > recent_data_cambio.loc[idx_1, 'low']):
                highest = recent_data_cambio.loc[idx_0, 'high']
                lowest = recent_data_cambio.loc[idx_1, 'low']
                fibo_618_level = lowest + (highest - lowest) * 0.618
                price_at_idx_2 = recent_data_cambio.loc[idx_2, 'close']
                threshold = self.fibo_touch_threshold_pct * price_at_idx_2

                if abs(price_at_idx_2 - fibo_618_level) <= threshold:
                    # Señal de compra si la vela 3 cierra por encima de su apertura (momentum)
                    if recent_data_cambio.loc[idx_2, 'close'] > recent_data_cambio.loc[idx_2, 'open']:
                         df.at[idx_2, 'combined_fibo_signal'] = 1
                         log.debug(f"CambioEstructuraFibo BUY Signal en {idx_2} (Precio: {price_at_idx_2:.5f}, Fibo: {fibo_618_level:.5f})")
                    # Se podría añadir lógica para señal de venta si cierra por debajo


        # --- 2. Lógica de TendenciaBasicaFibo ---
        # Calcular Fibonacci 61.8% estándar sobre un periodo
        if len(df) >= self.tendencia_basica_period:
            # Usar rolling para encontrar HH y LL en el periodo
            rolling_high = df['high'].rolling(window=self.tendencia_basica_period, min_periods=self.tendencia_basica_period).max()
            rolling_low = df['low'].rolling(window=self.tendencia_basica_period, min_periods=self.tendencia_basica_period).min()

            # Calcular el nivel de Fibonacci 61.8%
            df['fibo_tendencia_level'] = rolling_low + (rolling_high - rolling_low) * 0.618

            # Señal cuando el precio toca este nivel (última vela)
            if len(df) > 1:
                 current_close = df['close'].iloc[-1]
                 current_fibo_level = df['fibo_tendencia_level'].iloc[-1]

                 # Solo generar señal si el nivel es válido (no NaN)
                 if pd.notna(current_fibo_level) and current_fibo_level > 0:
                     threshold = self.fibo_touch_threshold_pct * current_close
                     # Comprobar si la vela anterior o la actual cruzó/tocó el nivel
                     prev_close = df['close'].iloc[-2]
                     if (prev_close <= current_fibo_level <= current_close) or \
                        (current_close <= current_fibo_level <= prev_close):
                         # Añadir confirmación de momentum (vela alcista)
                         if current_close > df['open'].iloc[-1]:
                             df.at[df.index[-1], 'combined_fibo_signal'] = 1 # Priorizamos compra
                             log.debug(f"TendenciaBasicaFibo BUY Signal en {df.index[-1]} (Precio: {current_close:.5f}, Fibo: {current_fibo_level:.5f})")
                         # Se podría añadir lógica para señal de venta

        # --- 3. Lógica de ParidadVelaFibo ---
        # Determinar umbral de volumen si no se proporciona
        volume_threshold = self.paridad_volume_threshold
        if volume_threshold is None and 'volume' in df.columns and not df['volume'].empty:
            volume_threshold = df['volume'].quantile(0.90) # Percentil 90
            log.debug(f"Umbral de volumen calculado dinámicamente para {pair}: {volume_threshold}")

        if volume_threshold is not None and 'volume' in df.columns:
            # Revisar últimas N velas para eficiencia
            lookback_window_paridad = max(self.paridad_lookback_window, 100)
            recent_data_paridad = df.tail(lookback_window_paridad).copy()

            for i in range(len(recent_data_paridad)):
                idx_actual = recent_data_paridad.index[i]
                current_volume = recent_data_paridad.loc[idx_actual, 'volume']

                # Verificar si es una vela de alto volumen
                if current_volume > volume_threshold:
                    reference_price = recent_data_paridad.loc[idx_actual, 'close']
                    touch_threshold = self.paridad_touch_threshold_pct * reference_price

                    # Buscar retorno al precio de referencia en las siguientes velas
                    end_idx = min(i + self.paridad_lookback_window, len(recent_data_paridad))
                    future_data = recent_data_paridad.iloc[i+1:end_idx]

                    for j in range(len(future_data)):
                        future_idx = future_data.index[j]
                        future_close = future_data.loc[future_idx, 'close']

                        if abs(future_close - reference_price) <= touch_threshold:
                            # Señal de compra si el precio sube después del retorno
                            # (ejemplo simple: si la vela de retorno es alcista)
                            future_open = future_data.loc[future_idx, 'open']
                            if future_close > future_open:
                                df.at[future_idx, 'combined_fibo_signal'] = 1
                                log.debug(f"ParidadVelaFibo BUY Signal en {future_idx} (Ref: {reference_price:.5f}, Retorno: {future_close:.5f})")
                            # Se podría añadir lógica para señal de venta
                            break # Solo una señal por vela de alto volumen

        log.info(f"Análisis de CombinedFiboStrategy completado para {pair}.")
        return df

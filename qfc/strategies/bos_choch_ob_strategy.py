import pandas as pd
import numpy as np
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class BosChochObStrategy(BaseStrategy):
    """
    Estrategia que identifica Break of Structure (BOS), Change of Character (CHOCH),
    y Order Blocks (OB) potenciales.
    Genera señales cuando el precio interactúa con estos niveles de una manera específica.
    """

    def __init__(self, config: dict):
        super().__init__(config)

        # --- Configuración para Detección de Swings ---
        self.swing_detection_period = self.config.get("swing_detection_period", 5)
        # Método de detección de swing: 'simple' o 'pandas_ta' (si se instala)
        self.swing_method = self.config.get("swing_method", "simple")

        # --- Configuración para BOS/CHOCH ---
        # Usar solo el cierre para confirmar la ruptura (como en el MQL5)
        self.use_close_only_for_break = self.config.get("use_close_only_for_break", True)
        # Umbral de proximidad para considerar que el precio "toca" un nivel (porcentaje del precio)
        self.level_touch_threshold_pct = self.config.get("level_touch_threshold_pct", 0.001) # 0.1% por defecto

        # --- Configuración para Order Blocks ---
        # Definición del OB: 'range' (high-low de la vela del swing) o 'level' (solo el nivel del swing)
        self.ob_definition = self.config.get("ob_definition", "level")
        # Ventana para buscar retorno al OB después de un BOS
        self.ob_return_lookback = self.config.get("ob_return_lookback", 20)
        # Confirmación de momentum tras el retorno al OB
        self.ob_return_momentum_confirmation = self.config.get("ob_return_momentum_confirmation", True)

        # --- Configuración de Señal ---
        # Requiere confirmación de momentum para señales de BOS/CHOCH
        self.bos_choch_momentum_confirmation = self.config.get("bos_choch_momentum_confirmation", True)
        # Tipo de señal a generar: 'bos', 'choch', 'ob_return', 'combined'
        self.signal_type = self.config.get("signal_type", "combined") # 'combined' por defecto

        log.info(f"Estrategia 'BosChochObStrategy' inicializada con configuración: "
                 f"Swing Period={self.swing_detection_period}, "
                 f"Signal Type={self.signal_type}")

    def _detect_swings_simple(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detección de swings usando el método simple del MQL5."""
        df = df.copy()
        df['is_swing_high'] = False
        df['is_swing_low'] = False
        df['swing_high_price'] = np.nan
        df['swing_low_price'] = np.nan

        period = self.swing_detection_period
        if len(df) < 2 * period + 1:
            return df

        for i in range(period, len(df) - period):
            is_high = True
            is_low = True
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            # Verificar si es un máximo local
            for j in range(1, period + 1):
                if (current_high <= df['high'].iloc[i - j] or
                    current_high <= df['high'].iloc[i + j]):
                    is_high = False
                    break

            # Verificar si es un mínimo local
            for j in range(1, period + 1):
                if (current_low >= df['low'].iloc[i - j] or
                    current_low >= df['low'].iloc[i + j]):
                    is_low = False
                    break

            if is_high:
                df.at[df.index[i], 'is_swing_high'] = True
                df.at[df.index[i], 'swing_high_price'] = current_high
            if is_low:
                df.at[df.index[i], 'is_swing_low'] = True
                df.at[df.index[i], 'swing_low_price'] = current_low

        # Forward-fill swing prices to know the "last" swing at any point
        df['last_swing_high_price'] = df['swing_high_price'].ffill()
        df['last_swing_low_price'] = df['swing_low_price'].ffill()

        return df

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        """
        Aplica el análisis de BOS, CHOCH y OB.
        Añade columnas para señales y niveles:
        - 'bos_choch_ob_signal': Valor final de la señal (1: Compra, -1: Venta, 0: Sin señal)
        - Columnas auxiliares para niveles y estados si se desea visualizar.
        """
        log.info(f"Ejecutando análisis de BosChochObStrategy para {pair}...")
        df = data.copy()

        # Inicializar columnas de salida
        df['bos_choch_ob_signal'] = 0
        # Columnas auxiliares para visualización o depuración
        df['is_uptrend_bos'] = True # Estado de tendencia inicial
        df['last_bos_type'] = "" # 'bullish' o 'bearish'
        df['last_choch_type'] = "" # 'bullish' o 'bearish'
        df['potential_bullish_ob'] = np.nan # Nivel del BOB potencial
        df['potential_bearish_ob'] = np.nan # Nivel del SOB potencial

        if df.empty:
            log.warning(f"No hay datos para analizar en BosChochObStrategy para {pair}.")
            return df

        # --- 1. Detección de Swings ---
        df = self._detect_swings_simple(df)
        if df['last_swing_high_price'].isna().all() or df['last_swing_low_price'].isna().all():
             log.warning(f"No se encontraron suficientes swings en {pair}.")
             return df

        # --- 2. Identificación de BOS y CHOCH ---
        df['bos_bullish_detected'] = False
        df['bos_bearish_detected'] = False
        df['choch_bullish_detected'] = False
        df['choch_bearish_detected'] = False

        for i in range(1, len(df)): # Comenzar desde la segunda vela
            idx_current = df.index[i]
            idx_prev = df.index[i-1]

            current_close = df.loc[idx_current, 'close']
            current_open = df.loc[idx_current, 'open']
            current_high = df.loc[idx_current, 'high']
            current_low = df.loc[idx_current, 'low']

            prev_close = df.loc[idx_prev, 'close']
            prev_open = df.loc[idx_prev, 'open']

            last_swing_high = df.loc[idx_current, 'last_swing_high_price']
            last_swing_low = df.loc[idx_current, 'last_swing_low_price']
            is_uptrend = df.loc[idx_current, 'is_uptrend_bos']

            momentum_ok_bullish = True
            momentum_ok_bearish = True
            if self.bos_choch_momentum_confirmation:
                momentum_ok_bullish = current_close > current_open
                momentum_ok_bearish = current_close < current_open

            # --- Lógica de BOS/CHOCH ---
            if is_uptrend:
                # Tendencia Alcista
                # BOS Alcista: Romper el último máximo
                bos_bullish_break = False
                if self.use_close_only_for_break:
                    bos_bullish_break = (prev_close <= last_swing_high < current_close) and momentum_ok_bullish
                else:
                    bos_bullish_break = (current_high > last_swing_high) and momentum_ok_bullish

                if bos_bullish_break:
                    df.at[idx_current, 'bos_bullish_detected'] = True
                    df.at[idx_current, 'last_bos_type'] = 'bullish'
                    log.debug(f"BOS Bullish detectado en {idx_current} para {pair} en {current_close:.5f} (Nivel: {last_swing_high:.5f})")
                    # Identificar BOB potencial: basado en el último swing low
                    if pd.notna(last_swing_low):
                         df.at[idx_current, 'potential_bullish_ob'] = last_swing_low # Puede ser el nivel o el rango
                         log.debug(f"  -> BOB potencial identificado en nivel {last_swing_low:.5f}")

                # CHOCH Bajista: Romper el último mínimo
                choch_bearish_break = False
                if self.use_close_only_for_break:
                    choch_bearish_break = (prev_close >= last_swing_low > current_close) and momentum_ok_bearish
                else:
                    choch_bearish_break = (current_low < last_swing_low) and momentum_ok_bearish

                if choch_bearish_break:
                    df.at[idx_current, 'choch_bearish_detected'] = True
                    df.at[idx_current, 'last_choch_type'] = 'bearish'
                    df.at[idx_current, 'is_uptrend_bos'] = False # Cambiar tendencia
                    log.debug(f"CHOCH Bearish detectado en {idx_current} para {pair} en {current_close:.5f} (Nivel: {last_swing_low:.5f}) -> Tendencia bajista iniciada")

            else:
                # Tendencia Bajista
                # BOS Bajista: Romper el último mínimo
                bos_bearish_break = False
                if self.use_close_only_for_break:
                    bos_bearish_break = (prev_close >= last_swing_low > current_close) and momentum_ok_bearish
                else:
                    bos_bearish_break = (current_low < last_swing_low) and momentum_ok_bearish

                if bos_bearish_break:
                    df.at[idx_current, 'bos_bearish_detected'] = True
                    df.at[idx_current, 'last_bos_type'] = 'bearish'
                    log.debug(f"BOS Bearish detectado en {idx_current} para {pair} en {current_close:.5f} (Nivel: {last_swing_low:.5f})")
                    # Identificar SOB potencial: basado en el último swing high
                    if pd.notna(last_swing_high):
                         df.at[idx_current, 'potential_bearish_ob'] = last_swing_high # Puede ser el nivel o el rango
                         log.debug(f"  -> SOB potencial identificado en nivel {last_swing_high:.5f}")

                # CHOCH Alcista: Romper el último máximo
                choch_bullish_break = False
                if self.use_close_only_for_break:
                    choch_bullish_break = (prev_close <= last_swing_high < current_close) and momentum_ok_bullish
                else:
                    choch_bullish_break = (current_high > last_swing_high) and momentum_ok_bullish

                if choch_bullish_break:
                    df.at[idx_current, 'choch_bullish_detected'] = True
                    df.at[idx_current, 'last_choch_type'] = 'bullish'
                    df.at[idx_current, 'is_uptrend_bos'] = True # Cambiar tendencia
                    log.debug(f"CHOCH Bullish detectado en {idx_current} para {pair} en {current_close:.5f} (Nivel: {last_swing_high:.5f}) -> Tendencia alcista iniciada")

        # --- 3. Identificación de Retornos a OB y Generación de Señales ---
        # Buscar retorno a los OB potenciales identificados
        for i in range(len(df)):
            idx_current = df.index[i]
            potential_bullish_ob_level = df.loc[idx_current, 'potential_bullish_ob']
            potential_bearish_ob_level = df.loc[idx_current, 'potential_bearish_ob']

            # --- Señal de Compra: Retorno a BOB ---
            if pd.notna(potential_bullish_ob_level):
                threshold = self.level_touch_threshold_pct * potential_bullish_ob_level
                # Buscar en las próximas velas
                end_search_idx = min(i + self.ob_return_lookback, len(df))
                for j in range(i + 1, end_search_idx):
                    future_idx = df.index[j]
                    future_low = df.loc[future_idx, 'low']
                    future_close = df.loc[future_idx, 'close']
                    future_open = df.loc[future_idx, 'open']

                    if abs(future_low - potential_bullish_ob_level) <= threshold:
                        momentum_ok = True
                        if self.ob_return_momentum_confirmation:
                            momentum_ok = future_close > future_open # Vela alcista
                        if momentum_ok:
                            df.at[future_idx, 'bos_choch_ob_signal'] = 1
                            log.info(f"✅ BosChochOb BUY Signal (Retorno BOB) para {pair} en {future_idx} (OB: {potential_bullish_ob_level:.5f})")
                            break # Solo una señal por OB

            # --- Señal de Venta: Retorno a SOB ---
            if pd.notna(potential_bearish_ob_level):
                threshold = self.level_touch_threshold_pct * potential_bearish_ob_level
                # Buscar en las próximas velas
                end_search_idx = min(i + self.ob_return_lookback, len(df))
                for j in range(i + 1, end_search_idx):
                    future_idx = df.index[j]
                    future_high = df.loc[future_idx, 'high']
                    future_close = df.loc[future_idx, 'close']
                    future_open = df.loc[future_idx, 'open']

                    if abs(future_high - potential_bearish_ob_level) <= threshold:
                        momentum_ok = True
                        if self.ob_return_momentum_confirmation:
                            momentum_ok = future_close < future_open # Vela bajista
                        if momentum_ok:
                            df.at[future_idx, 'bos_choch_ob_signal'] = -1
                            log.info(f"🔻 BosChochOb SELL Signal (Retorno SOB) para {pair} en {future_idx} (OB: {potential_bearish_ob_level:.5f})")
                            break # Solo una señal por OB

        # --- 4. Lógica para otros tipos de señales (BOS/CHOCH directos) ---
        # Esta parte se puede ampliar si se quiere generar señales directas de BOS/CHOCH
        # Por ejemplo, si signal_type == 'bos' o 'choch', podrías activar señales en
        # df['bos_bullish_detected'] o df['choch_bullish_detected'] directamente.
        # Actualmente, la señal principal se genera en el retorno al OB.

        # Limpiar columnas auxiliares si no se necesitan fuera de esta estrategia
        # cols_to_drop = ['is_swing_high', 'is_swing_low', 'swing_high_price', 'swing_low_price',
        #                 'last_swing_high_price', 'last_swing_low_price', 'is_uptrend_bos',
        #                 'last_bos_type', 'last_choch_type', 'potential_bullish_ob',
        #                 'potential_bearish_ob', 'bos_bullish_detected', 'bos_bearish_detected',
        #                 'choch_bullish_detected', 'choch_bearish_detected']
        # df.drop(columns=cols_to_drop, inplace=True, errors='ignore')

        log.info(f"Análisis de BosChochObStrategy completado para {pair}.")
        return df

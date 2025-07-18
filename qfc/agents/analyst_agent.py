import pandas as pd
import pandas_ta as ta
from config.logger_config import log

class AnalystAgent:
    def __init__(self, config: dict):
        self.strategy_name = config.get("strategy_name", "UnknownStrategy")
        self.short_window = config.get("sma_short_window", 20)
        self.long_window = config.get("sma_long_window", 50)
        # Nombres de columna que usaremos internamente. Ahora tenemos control total.
        self.short_sma_col = f'sma_{self.short_window}'
        self.long_sma_col = f'sma_{self.long_window}'
        log.info(f"Agente Analista inicializado con la estrategia '{self.strategy_name}'.")

    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Añade los indicadores técnicos necesarios al dataframe."""
        log.info(f"Calculando {self.short_sma_col} y {self.long_sma_col}...")
        
        # --- LA CORRECCIÓN CLAVE ---
        # Le decimos explícitamente a sma() que use la columna 'close' del dataframe.
        # Esto asegura que devuelva una única Serie de Pandas, no un DataFrame.
        sma_short = ta.sma(close=data['close'], length=self.short_window)
        sma_long = ta.sma(close=data['close'], length=self.long_window)
        
        # Ahora que tenemos las Series, las asignamos a nuestras columnas.
        # Esto también nos da la flexibilidad de nombrar las columnas como queramos.
        data[self.short_sma_col] = sma_short
        data[self.long_sma_col] = sma_long
        # ---------------------------
        
        log.info(f"Indicadores calculados y añadidos al DataFrame. Nuevas columnas: {self.short_sma_col}, {self.long_sma_col}")
        return data

    def _generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Genera señales de compra/venta basadas en la estrategia."""
        log.info("Generando señales de trading...")
        
        # 'position' detecta el cambio de señal (el momento exacto del cruce)
        # 1 = Entrar en largo, -1 = Entrar en corto
        # Usamos .shift(1) para comparar la posición actual con la de la vela anterior.
        buy_condition = (data[self.short_sma_col] > data[self.long_sma_col]) & \
                        (data[self.short_sma_col].shift(1) <= data[self.long_sma_col].shift(1))
                        
        sell_condition = (data[self.short_sma_col] < data[self.long_sma_col]) & \
                         (data[self.short_sma_col].shift(1) >= data[self.long_sma_col].shift(1))

        data['position'] = 0
        data.loc[buy_condition, 'position'] = 1
        data.loc[sell_condition, 'position'] = -1

        # 'signal' indica el estado actual de la tendencia (si la corta está por encima o por debajo)
        data['signal'] = 0
        data.loc[data[self.short_sma_col] > data[self.long_sma_col], 'signal'] = 1
        data.loc[data[self.short_sma_col] < data[self.long_sma_col], 'signal'] = -1
        
        log.info("Señales generadas.")
        return data

    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        """Ejecuta el pipeline completo de análisis para un conjunto de datos."""
        if data.empty:
            log.warning("El dataframe de entrada está vacío. No se puede analizar.")
            return pd.DataFrame()
        
        df = data.copy()
        df_with_indicators = self._calculate_indicators(df)
        
        # --- LÍNEAS DE DEPURACIÓN ---
        log.info("--- DEPURACIÓN: Antes de dropna() ---")
        log.info(f"Columnas del DataFrame: {df_with_indicators.columns.tolist()}")
        log.info(f"Recuento de NaNs por columna:\n{df_with_indicators.isna().sum()}")
        # -----------------------------

        # Las SMAs tendrán valores NaN al principio. Los eliminamos para evitar problemas.
        df_with_indicators.dropna(inplace=True)
        
        log.info(f"--- DEPURACIÓN: Después de dropna(), filas restantes: {len(df_with_indicators)} ---")

        df_with_signals = self._generate_signals(df_with_indicators)
        
        return df_with_signals
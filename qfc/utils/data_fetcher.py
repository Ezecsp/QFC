import yfinance as yf
import pandas as pd
from config.logger_config import log

class DataFetcher:
    # ... (el __init__ y _get_appropriate_period no cambian) ...
    def __init__(self, pair: str, interval: str):
        self.pair = pair
        self.interval = interval

    def _get_appropriate_period(self) -> str:
        """
        Selecciona un 'period' válido y generoso basado en el 'interval'.
        Los periodos intradía están limitados por la API de yfinance.
        """
        # Mapeo de intervalo a periodo máximo permitido por yfinance
        interval_to_period = {
            # Intervalos intradía (limitados a 60 días)
            "1m": "7d",   # Límite máximo de yfinance
            "2m": "60d",  # Límite máximo de yfinance
            "5m": "60d",  # Límite máximo de yfinance
            "15m": "60d", # Límite máximo de yfinance
            "30m": "60d", # Límite máximo de yfinance
            
            # Intervalos horarios (limitados a 730 días o 2 años)
            "60m": "730d", # Límite máximo de yfinance
            "1h": "730d",  # Límite máximo de yfinance
            "90m": "60d",  # Límite máximo de yfinance (peculiaridad)

            # Intervalos diarios o superiores (prácticamente ilimitados)
            "1d": "5y",    # Pedimos 5 años en lugar de 'max' para tener un límite razonable
            "1wk": "10y",
            "1mo": "max"
        }
        
        # Usamos el valor del diccionario. Si el timeframe no está, usamos '1y' como default seguro.
        period = interval_to_period.get(self.interval, "1y")
        
        log.info(f"Para el intervalo '{self.interval}', se ha seleccionado un periodo de '{period}'.")
        return period

    def fetch_data(self) -> pd.DataFrame:
        """
        Descarga datos históricos, limpia las columnas y selecciona solo las esenciales.
        """
        period = self._get_appropriate_period()
        log.info(f"Obteniendo datos para {self.pair} con intervalo {self.interval} y periodo {period}...")
        try:
            data = yf.download(
                self.pair, period=period, interval=self.interval,
                progress=False, auto_adjust=False
            )
            if data.empty:
                log.warning(f"No se obtuvieron datos para {self.pair}.")
                return pd.DataFrame()

            # PASO 1: Aplanar el MultiIndex. El nivel del Ticker es el 1.
            if isinstance(data.columns, pd.MultiIndex):
                # ESTA ES LA CORRECCIÓN CRUCIAL. DEBE SER droplevel(1).
                data.columns = data.columns.droplevel(1)

            # PASO 2: Estandarizar nombres a minúsculas
            data.columns = data.columns.str.lower()

            # PASO 3: Priorizar 'adj close' si existe
            if 'adj close' in data.columns:
                data['close'] = data['adj close']

            # PASO 4: Seleccionar solo las columnas esenciales para evitar problemas futuros.
            essential_cols = ['open', 'high', 'low', 'close', 'volume']
            
            # Verificar que las columnas requeridas existen antes de intentar seleccionarlas
            cols_to_keep = [col for col in essential_cols if col in data.columns]
            if len(cols_to_keep) != len(essential_cols):
                 log.error(f"Faltan columnas esenciales. Requeridas: {essential_cols}, Encontradas en DataFrame: {data.columns.tolist()}")
                 return pd.DataFrame()
                 
            # Seleccionar únicamente las columnas esenciales
            data = data[essential_cols]

            log.info(f"Limpieza de datos completa. Columnas finales: {data.columns.tolist()}")
            log.info(f"Datos obtenidos exitosamente. {len(data)} velas cargadas.")
            return data
            
        except Exception as e:
            log.error(f"Error durante la obtención de datos para {self.pair}: {e}")
            return pd.DataFrame()
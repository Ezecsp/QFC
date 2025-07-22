import yfinance as yf
import pandas as pd
from config.logger_config import log

class DataFetcher:
    def __init__(self, pair: str, interval: str):
        self.pair = pair
        self.interval = interval

    def _get_period_for_interval(self, interval: str) -> str:
        # Mapeo de intervalos a periodos de tiempo razonables
        period_map = {
            '1m': '7d',   '5m': '60d',  '15m': '60d', '30m': '60d',
            '1h': '730d', '4h': '730d', '1d': '5y',   '1wk': '10y', '1mo': 'max'
        }
        default_period = period_map.get(interval)
        if default_period:
            log.info(f"Para el intervalo '{interval}', se ha seleccionado un periodo de '{default_period}'.")
            return default_period
        return '5y' # Un valor por defecto si el intervalo no está en el mapa

    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia los datos descargados de yfinance.
        Ahora es capaz de manejar columnas MultiIndex.
        """
        # --- ¡CAMBIO CLAVE! ---
        # Si yfinance devuelve un MultiIndex (columnas como tuplas), lo aplanamos.
        if isinstance(data.columns, pd.MultiIndex):
            log.info("Detectado un MultiIndex en las columnas, aplanando...")
            data.columns = data.columns.get_level_values(0)
        # ---------------------

        data.columns = [col.lower() for col in data.columns]
        if 'dividends' in data.columns:
            data = data.drop(columns=['dividends'])
        if 'stock splits' in data.columns:
            data = data.drop(columns=['stock splits'])
        data.dropna(inplace=True)
        log.info(f"Limpieza de datos completa. Columnas finales: {list(data.columns)}")
        return data

    def fetch_data(self, period: str = None, interval_override: str = None) -> pd.DataFrame:
        """
        Obtiene y limpia los datos históricos para el par.
        
        Args:
            period (str, optional): El periodo a descargar (ej. '5y', '730d').
                                    Si se provee, anula el cálculo automático.
            interval_override (str, optional): Anula el intervalo por defecto de la clase.
        
        Returns:
            pd.DataFrame: DataFrame con los datos limpios.
        """
        # --- ¡CAMBIO CLAVE! ---
        # Si no se provee un período, lo calculamos. Si sí, lo usamos.
        final_interval = interval_override if interval_override else self.interval
        final_period = period if period else self._get_period_for_interval(final_interval)
        # ---------------------

        log.info(f"Obteniendo datos para {self.pair} con intervalo {final_interval} y periodo {final_period}...")
        
        try:
            data = yf.download(
                tickers=self.pair,
                period=final_period,
                interval=final_interval,
                progress=False,
                auto_adjust=True
            )
            
            if data.empty:
                log.warning(f"No se obtuvieron datos para {self.pair}. El ticker puede ser incorrecto o no hay datos para el periodo.")
                return pd.DataFrame()
                
            clean_data = self._clean_data(data)
            log.info(f"Datos obtenidos exitosamente. {len(clean_data)} velas cargadas.")
            return clean_data

        except Exception as e:
            log.error(f"Error al descargar datos de yfinance para {self.pair}: {e}")
            return pd.DataFrame()
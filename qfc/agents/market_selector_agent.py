import pandas as pd
import pandas_ta as ta
from config.logger_config import log
from qfc.utils.data_fetcher import DataFetcher

class MarketSelectorAgent:
    """
    Agente 2: Analiza la volatilidad del mercado para seleccionar y rankear
    los pares de divisas más prometedores para el día.
    """
    def __init__(self, config: dict):
        self.atr_period = config.get("atr_period", 14)
        log.info(f"Agente Vigilante del Mercado inicializado con ATR({self.atr_period}).")

    def rank_pairs_by_volatility(self, pairs: list) -> list:
        """
        Calcula la volatilidad (ATR) para una lista de pares y los devuelve rankeados.
        """
        log.info(f"Rankeando {len(pairs)} pares por volatilidad...")
        pair_volatility = []

        for pair in pairs:
            # Para el ATR diario, pedimos datos en timeframe '1d'.
            log.info(f"Analizando volatilidad para {pair}...")
            fetcher = DataFetcher(pair=pair, interval="1d")
            data = fetcher.fetch_data()

            if data.empty or len(data) < self.atr_period:
                log.warning(f"No hay suficientes datos para calcular el ATR para {pair}. Se omitirá.")
                continue

            # Calcular ATR usando pandas-ta
            data.ta.atr(length=self.atr_period, append=True)
            
            # El nombre de la columna es usualmente 'ATRr_14'
            atr_col_name = f'ATRr_{self.atr_period}'
            
            if atr_col_name in data.columns:
                # Tomamos el último valor del ATR como la medida de volatilidad actual
                last_atr = data[atr_col_name].iloc[-1]
                pair_volatility.append({"pair": pair, "volatility_atr": last_atr})
                log.info(f"Volatilidad (ATR) para {pair}: {last_atr:.5f}")
            else:
                log.warning(f"No se pudo encontrar la columna ATR '{atr_col_name}' para {pair}.")

        if not pair_volatility:
            log.error("No se pudo calcular la volatilidad para ningún par.")
            return []

        # Ordenar la lista de diccionarios de mayor a menor volatilidad
        ranked_pairs = sorted(pair_volatility, key=lambda x: x['volatility_atr'], reverse=True)
        
        log.info("Ranking de pares por volatilidad completado.")
        return ranked_pairs
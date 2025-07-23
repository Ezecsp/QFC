import pandas as pd
from config.logger_config import log
from qfc.strategies.support_resistance_strategy import SupportResistanceStrategy
from qfc.strategies.order_block_strategy import OrderBlockStrategy
from qfc.strategies.fvg_strategy import FvgStrategy
from qfc.strategies.market_structure_shift_strategy import MarketStructureShiftStrategy 
from qfc.strategies.ml_prediction_strategy import MLPredictionStrategy

class AnalystAgent:
    def __init__(self, config: dict):
        self.strategies = []
        strategies_to_run = config.get("strategies_to_run", [])
        strategy_configs = config.get("strategy_configs", {})

        log.info(f"Cargando {len(strategies_to_run)} estrategias...")

        for strategy_name in strategies_to_run:
            conf = strategy_configs.get(strategy_name, {})
            if strategy_name == "support_resistance":
                self.strategies.append(SupportResistanceStrategy(conf))
            elif strategy_name == "order_block":
                self.strategies.append(OrderBlockStrategy(conf))
            elif strategy_name == "fvg":
                self.strategies.append(FvgStrategy(conf))
            elif strategy_name == "market_structure_shift": # <-- AÑADIR BLOQUE
                self.strategies.append(MarketStructureShiftStrategy(conf))
            elif strategy_name == "ml_prediction":
                self.strategies.append(MLPredictionStrategy(conf))
            else:
                log.warning(f"Estrategia '{strategy_name}' no reconocida. Será ignorada.")
        
        log.info("Agente Analista y estrategias inicializados.")

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        if not self.strategies:
            log.warning("No hay estrategias cargadas para analizar.")
            return data

        analysis_df = data.copy()
        # Aseguramos que el ATR esté presente para el Coordinador
        if 'atr' not in analysis_df.columns:
            analysis_df.ta.atr(length=14, append=True)

        log.info(f"Ejecutando {len(self.strategies)} estrategias sobre los datos...")
        for strategy in self.strategies:
            try:
                analysis_df = strategy.analyze(analysis_df, pair=pair)
            except Exception as e:
                log.error(f"Error al ejecutar la estrategia {strategy.__class__.__name__}: {e}")

        return analysis_df
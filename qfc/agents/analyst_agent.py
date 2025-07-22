import pandas as pd
from config.logger_config import log
from qfc.strategies.sma_crossover_strategy import SmaCrossoverStrategy
from qfc.strategies.support_resistance_strategy import SupportResistanceStrategy
#from qfc.strategies.fibonacci_retracement_strategy import FibonacciRetracementStrategy
from qfc.strategies.ml_prediction_strategy import MLPredictionStrategy
from qfc.strategies.fvg_strategy import FvgStrategy 
from qfc.strategies.order_block_strategy import OrderBlockStrategy 


class AnalystAgent:
    def __init__(self, config: dict):
        """
        Inicializa el Agente Analista.
        Ya no contiene lógica de estrategia, sino que carga las estrategias
        especificadas en la configuración.
        """
        self.strategies = []
        strategies_to_run = config.get("strategies_to_run", [])
        strategy_configs = config.get("strategy_configs", {})

        log.info(f"Cargando {len(strategies_to_run)} estrategias...")

        for strategy_name in strategies_to_run:
            if strategy_name == "sma_crossover":
                # Pasa solo la configuración específica de esta estrategia
                conf = strategy_configs.get(strategy_name, {})
                self.strategies.append(SmaCrossoverStrategy(conf))
            
            elif strategy_name == "support_resistance":
                conf = strategy_configs.get(strategy_name, {})
                self.strategies.append(SupportResistanceStrategy(conf))
                
            elif strategy_name == "ml_prediction":
                conf = strategy_configs.get(strategy_name, {})
                self.strategies.append(MLPredictionStrategy(conf))
                
            #elif strategy_name == "fibonacci_retracement":
            #    conf = strategy_configs.get(strategy_name, {})
            #   self.strategies.append(FibonacciRetracementStrategy(conf))
            
            elif strategy_name == "fvg":
                conf = strategy_configs.get(strategy_name, {})
                self.strategies.append(FvgStrategy(conf))
                
            elif strategy_name == "order_block":
                conf = strategy_configs.get(strategy_name, {})
                self.strategies.append(OrderBlockStrategy(conf))
                
            else:
                log.warning(f"Estrategia '{strategy_name}' no reconocida. Será ignorada.")
        
        log.info("Agente Analista y estrategias inicializados.")


    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        """
        Ejecuta el método 'analyze' de cada estrategia cargada,
        enriqueciendo el DataFrame con los resultados de cada una.
        """
        if not self.strategies:
            log.warning("No hay estrategias cargadas para analizar.")
            return data

        analysis_df = data.copy()

        log.info(f"Ejecutando {len(self.strategies)} estrategias sobre los datos...")
        for strategy in self.strategies:
            try:
                # Cada estrategia añade sus propias columnas al DataFrame
                analysis_df = strategy.analyze(analysis_df, pair=pair)
            except Exception as e:
                log.error(f"Error al ejecutar la estrategia {strategy.__class__.__name__}: {e}")

        return analysis_df
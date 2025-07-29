import pandas as pd
import pandas_ta as ta
from config.logger_config import log

# Importaciones de estrategias
from qfc.strategies.support_resistance_strategy import SupportResistanceStrategy
from qfc.strategies.order_block_strategy import OrderBlockStrategy
from qfc.strategies.fvg_strategy import FvgStrategy
from qfc.strategies.market_structure_shift_strategy import MarketStructureShiftStrategy
from qfc.strategies.ml_prediction_strategy import MLPredictionStrategy
from qfc.strategies.combined_fibo_strategy import CombinedFiboStrategy
from qfc.strategies.bos_choch_ob_strategy import BosChochObStrategy # <-- AÑADIR IMPORTACIÓN

class AnalystAgent:
    """
    Agente 3: El Cerebro Analítico. Coordina y ejecuta múltiples estrategias
    de análisis técnico sobre los datos del mercado para generar señales.
    """
    def __init__(self, config: dict):
        """
        Inicializa el agente con las estrategias configuradas.
        Args:
            config (dict): Diccionario con la configuración del agente,
                           incluyendo 'strategies_to_run' y 'strategy_configs'.
        """
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
            elif strategy_name == "combined_fibo": # <-- AÑADIR BLOQUE ELIF
                 self.strategies.append(CombinedFiboStrategy(conf))
            elif strategy_name == "bos_choch_ob": # <-- AÑADIR BLOQUE ELIF
                 self.strategies.append(BosChochObStrategy(conf)) 
            elif strategy_name == "ml_prediction":
                self.strategies.append(MLPredictionStrategy(conf))
            else:
                log.warning(f"Estrategia '{strategy_name}' no reconocida. Será ignorada.")

        log.info("Agente Analista y estrategias inicializados.")

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        """
        Ejecuta todas las estrategias cargadas sobre el DataFrame de datos.
        Args:
            data (pd.DataFrame): DataFrame con los datos OHLCV del mercado.
            pair (str): El par de divisas que se está analizando (para logs).
        Returns:
            pd.DataFrame: El DataFrame original enriquecido con las columnas
                          de señales de todas las estrategias.
        """
        if not self.strategies:
            log.warning("No hay estrategias cargadas para analizar.")
            # Devolvemos el DataFrame tal cual, pero aseguramos que tenga 'atr'
            analysis_df = data.copy()
            if 'atr' not in analysis_df.columns:
                log.debug(f"Calculando ATRr_14 para {pair} (fallback)...")
                # Llamada segura para calcular ATR
                analysis_df.ta.atr(length=14, append=True)
                # Renombrar para consistencia
                atr_col_name = 'ATRr_14'
                if atr_col_name in analysis_df.columns and 'atr' not in analysis_df.columns:
                    analysis_df.rename(columns={atr_col_name: 'atr'}, inplace=True)
                    log.debug(f"Columna ATR renombrada de '{atr_col_name}' a 'atr' para {pair}.")
                if 'atr' not in analysis_df.columns:
                     log.warning(f"No se pudo calcular ATR para {pair} en análisis vacío. Añadiendo columna NaN.")
                     analysis_df['atr'] = pd.NA
            return analysis_df

        analysis_df = data.copy()
        
        # --- CORRECCIÓN PARA ASEGURAR EL ATR ---
        # 1. Intentar usar el nombre de columna esperado por pandas-ta
        atr_column_name = 'ATRr_14' # Nombre por defecto de pandas-ta para ATR(14)
        
        # 2. Si la columna no existe, calcularla
        if atr_column_name not in analysis_df.columns:
            log.debug(f"Calculando {atr_column_name} para {pair}...")
            # Llamada SIMPLIFICADA y CORRECTA, como se hace en otras partes del código
            # Usamos append=True para añadir la columna al DataFrame
            try:
                # Asegurarse de que las columnas necesarias estén presentes y no tengan NaNs iniciales problemáticos
                # para el cálculo del ATR. pandas-ta maneja esto, pero es bueno ser consciente.
                analysis_df.ta.atr(length=14, append=True)
                # Nota: append=True crea la columna 'ATRr_14'.
            except Exception as e:
                 log.error(f"Error al calcular ATR para {pair}: {e}")
                 # Añadir columna de NaNs como fallback
                 analysis_df[atr_column_name] = pd.NA

        # 3. Verificar si la columna se creó y renombrarla a 'atr' para consistencia
        # (Esto es útil porque otras partes del código, como CoordinatorAgent, esperan 'atr')
        if atr_column_name in analysis_df.columns and 'atr' not in analysis_df.columns:
            analysis_df.rename(columns={atr_column_name: 'atr'}, inplace=True)
            log.debug(f"Columna ATR renombrada de '{atr_column_name}' a 'atr' para {pair}.")

        # 4. Verificación final: ¿Tenemos la columna 'atr' ahora?
        # Si no se pudo crear ni renombrar, creamos una columna vacía para evitar errores posteriores.
        if 'atr' not in analysis_df.columns:
            log.error(f"Fallo crítico: No se pudo crear/generar la columna 'atr' para {pair}. "
                      f"Las columnas disponibles son: {list(analysis_df.columns)}. "
                      f"Añadiendo columna 'atr' con valores NaN.")
            analysis_df['atr'] = pd.NA # O np.nan

        # --- FIN CORRECCIÓN ATR ---

        log.info(f"Ejecutando {len(self.strategies)} estrategias sobre los datos...")
        for strategy in self.strategies:
            try:
                # Pasamos el par a la estrategia también, por si lo necesita
                analysis_df = strategy.analyze(analysis_df, pair=pair)
            except Exception as e:
                log.error(f"Error al ejecutar la estrategia {strategy.__class__.__name__} para {pair}: {e}")
                # No detenemos el proceso por un error en una estrategia
        return analysis_df

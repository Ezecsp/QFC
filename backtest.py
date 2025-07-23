import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy
from qfc.utils.data_fetcher import DataFetcher
from config.logger_config import log
from config import settings

# Importamos TODAS las estrategias que vamos a usar en el análisis
from qfc.strategies.support_resistance_strategy import SupportResistanceStrategy
from qfc.strategies.order_block_strategy import OrderBlockStrategy
from qfc.strategies.fvg_strategy import FvgStrategy
from qfc.strategies.market_structure_shift_strategy import MarketStructureShiftStrategy

# --- PASO 1: FUNCIÓN DE PREPARACIÓN DE DATOS ---
# Toda la lógica de análisis pesado se mueve aquí. Se ejecuta UNA SOLA VEZ por par.
def prepare_data_for_backtest(df: pd.DataFrame, pair: str) -> pd.DataFrame:
    """
    Toma un DataFrame con datos de mercado y le añade todas las columnas
    de señales necesarias para el backtest.
    """
    log.info(f"({pair}) Pre-calculando todas las señales de estrategia...")
    df.columns = [col.lower() for col in df.columns]

    # Instanciamos las estrategias
    sr_analyzer = SupportResistanceStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['support_resistance'])
    ob_analyzer = OrderBlockStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['order_block'])
    fvg_analyzer = FvgStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['fvg'])
    mss_analyzer = MarketStructureShiftStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['market_structure_shift'])
    
    # Aplicamos el análisis de cada estrategia
    df = sr_analyzer.analyze(df, pair)
    df = ob_analyzer.analyze(df, pair)
    df = fvg_analyzer.analyze(df, pair)
    df = mss_analyzer.analyze(df, pair)

    # Añadimos el filtro de tendencia
    log.info(f"({pair}) Calculando y añadiendo filtro de tendencia de 4h...")
    trend_fetcher = DataFetcher(pair=pair, interval='4h')
    df_trend = trend_fetcher.fetch_data(period="730d")
    if not df_trend.empty:
        df_trend['ema_trend'] = ta.ema(df_trend['close'], length=50)
        df['is_uptrend'] = (df_trend['close'] > df_trend['ema_trend']).reindex(df.index, method='ffill')
    else:
        df['is_uptrend'] = True # Si falla, asumimos tendencia alcista para no filtrar todo

    log.info(f"({pair}) Pre-cálculo de datos completado.")
    return df


# --- PASO 2: LA ESTRATEGIA DE BACKTESTING AHORA ES MUY SIMPLE ---
# Solo se encarga de la puntuación y ejecución, usando las columnas ya calculadas.
class QFCSystemBacktest(Strategy):
    pair = "UNKNOWN"
    
    # Parámetros a optimizar (multiplicados por 10)
    weight_sr = 10
    weight_ob = 15
    weight_fvg = 10
    weight_mss = 25
    signal_threshold = 30
    penalty_factor = 3

    def init(self):
        # Referenciamos las columnas pre-calculadas. La librería las pone en mayúsculas.
        self.sr_signal = self.data.Sr_position
        self.ob_signal = self.data.Ob_signal
        self.fvg_signal = self.data.Fvg_signal
        self.mss_signal = self.data.Mss_signal
        self.is_uptrend = self.data.Is_uptrend
        self.atr = self.I(ta.atr, pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(self.data.Close), length=14)

    def next(self):
        if self.position:
            return

        buy_score, sell_score = 0, 0
        
        if self.sr_signal[-1] == 1: buy_score += self.weight_sr / 10
        if self.sr_signal[-1] == -1: sell_score += self.weight_sr / 10
        if self.ob_signal[-1] == 1: buy_score += self.weight_ob / 10
        if self.ob_signal[-1] == -1: sell_score += self.weight_ob / 10
        if self.fvg_signal[-1] == 1: buy_score += self.weight_fvg / 10
        if self.fvg_signal[-1] == -1: sell_score += self.weight_fvg / 10
        if self.mss_signal[-1] == 1: buy_score += self.weight_mss / 10
        if self.mss_signal[-1] == -1: sell_score += self.weight_mss / 10
            
        if self.is_uptrend[-1]: sell_score *= (self.penalty_factor / 10)
        else: buy_score *= (self.penalty_factor / 10)

        threshold = self.signal_threshold / 10
        if buy_score >= threshold and buy_score > sell_score:
            self.buy(sl=self.data.Close[-1] - self.atr[-1] * 1.5, tp=self.data.Close[-1] + self.atr[-1] * 3)
        elif sell_score >= threshold and sell_score > buy_score:
            self.sell(sl=self.data.Close[-1] + self.atr[-1] * 1.5, tp=self.data.Close[-1] - self.atr[-1] * 3)


# --- PASO 3: EL SCRIPT PRINCIPAL QUE ORQUESTA EL PROCESO ---
if __name__ == "__main__":
    log.info("="*60)
    log.info("INICIANDO BACKTESTING Y OPTIMIZACIÓN MULTI-PAR")
    log.info("="*60)

    PAIRS_TO_BACKTEST = settings.TRADING_PAIRS
    all_stats = {}

    for pair in PAIRS_TO_BACKTEST:
        log.info(f"--- PROCESANDO PAR: {pair} ---")
        
        # 1. Obtener los datos crudos
        data_fetcher = DataFetcher(pair=pair, interval='1h')
        df_raw = data_fetcher.fetch_data(period="730d")

        if df_raw.empty or len(df_raw) < 200:
            log.warning(f"No hay suficientes datos para {pair}. Saltando al siguiente.")
            continue

        # 2. Preparar los datos con todas las señales (LA MAGIA OCURRE AQUÍ)
        df_ready = prepare_data_for_backtest(df_raw, pair)
        
        # 3. La librería necesita que las columnas empiecen con mayúscula
        df_ready.columns = [col.capitalize() for col in df_ready.columns]

        # 4. Configurar e iniciar la optimización
        QFCSystemBacktest.pair = pair
        bt = Backtest(df_ready, QFCSystemBacktest, cash=100_000, commission=.001)

        log.info(f"Ejecutando OPTIMIZACIÓN para {pair}... (Esto puede tardar)")
        
        try:
            stats = bt.optimize(
                weight_sr=range(5, 21, 5),      
                weight_ob=range(10, 31, 5),     
                weight_fvg=range(5, 21, 5),      
                weight_mss=range(15, 31, 5),     
                signal_threshold=range(25, 41, 5),  
                penalty_factor=range(1, 6, 2),
                maximize='Sharpe Ratio'
            )
            all_stats[pair] = stats
            
            log.info(f"--- RESULTADOS ÓPTIMOS PARA {pair} ---")
            print(stats)
            log.info(f"--- PARÁMETROS ÓPTIMOS PARA {pair} (recuerda dividir por 10) ---")
            print(stats._strategy)
            
        except Exception as e:
            log.error(f"Ocurrió un error durante la optimización para {pair}: {e}")

    log.info("="*60)
    log.info("RESUMEN FINAL DE OPTIMIZACIÓN MULTI-PAR")
    log.info("="*60)
    if not all_stats:
        log.warning("No se completó ninguna optimización.")
    else:
        for pair, stats in all_stats.items():
            log.info(f"Resultados para {pair}:")
            print(f"  Sharpe Ratio: {stats.get('Sharpe Ratio', 'N/A'):.2f}")
            print(f"  Return [%]: {stats.get('Return [%]', 'N/A'):.2f}")
            print(f"  Win Rate [%]: {stats.get('Win Rate [%]', 'N/A'):.2f}")
            print(f"  Parámetros Óptimos: {stats._strategy}\n")

    log.info("PROCESO DE BACKTESTING COMPLETADO.")
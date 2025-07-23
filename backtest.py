import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy
from qfc.utils.data_fetcher import DataFetcher
from config.logger_config import log
from config import settings # Importamos settings para la lista de pares
# Importamos TODAS las estrategias que generan señales
from qfc.strategies.support_resistance_strategy import SupportResistanceStrategy
from qfc.strategies.order_block_strategy import OrderBlockStrategy
from qfc.strategies.fvg_strategy import FvgStrategy
from qfc.strategies.market_structure_shift_strategy import MarketStructureShiftStrategy

class QFCSystemBacktest(Strategy):
    """
    Estrategia de backtesting que replica la lógica de puntuación completa del agente QFC.
    """
    pair = "UNKNOWN"
    
    # --- PARÁMETROS A OPTIMIZAR (Multiplicados por 10 para usar enteros) ---
    weight_sr = 10
    weight_ob = 15
    weight_fvg = 10
    weight_mss = 25 # Market Structure Shift
    signal_threshold = 30
    penalty_factor = 3 # Penalización contra-tendencia

    def init(self):
        """
        Pre-calcula todas las señales para máxima eficiencia durante el backtest.
        """
        # --- 1. FILTRO DE TENDENCIA DE 4H (espejo de main.py) ---
        log.info(f"Backtester ({self.pair}): Calculando filtro de tendencia de 4h...")
        trend_fetcher = DataFetcher(pair=self.pair, interval='4h')
        df_trend = trend_fetcher.fetch_data(period="730d")
        if not df_trend.empty:
            df_trend['ema_trend'] = ta.ema(df_trend['close'], length=50)
            self.trend_signal = df_trend['close'] > df_trend['ema_trend']
            self.trend_signal = self.trend_signal.reindex(self.data.index, method='ffill').fillna(True)
        else:
            self.trend_signal = pd.Series(True, index=self.data.index)

        # --- 2. PRE-CÁLCULO DE SEÑALES DE ESTRATEGIAS ---
        log.info(f"Backtester ({self.pair}): Pre-calculando señales de todas las estrategias...")
        df = self.data.df.copy()
        df.columns = [col.lower() for col in df.columns]

        sr_analyzer = SupportResistanceStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['support_resistance'])
        ob_analyzer = OrderBlockStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['order_block'])
        fvg_analyzer = FvgStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['fvg'])
        mss_analyzer = MarketStructureShiftStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['market_structure_shift'])
        
        df = sr_analyzer.analyze(df, self.pair)
        df = ob_analyzer.analyze(df, self.pair)
        df = fvg_analyzer.analyze(df, self.pair)
        df = mss_analyzer.analyze(df, self.pair)
        
        self.sr_signal = self.I(lambda: df['sr_position'], name="sr_signal")
        self.ob_signal = self.I(lambda: df['ob_signal'], name="ob_signal")
        self.fvg_signal = self.I(lambda: df['fvg_signal'], name="fvg_signal")
        self.mss_signal = self.I(lambda: df['mss_signal'], name="mss_signal")
        
        self.atr = self.I(ta.atr, pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(self.data.Close), length=14)

    def next(self):
        if self.position:
            return

        # --- 3. LÓGICA DE PUNTUACIÓN (espejo de main.py) ---
        buy_score, sell_score = 0, 0
        
        if self.sr_signal[-1] == 1: buy_score += self.weight_sr / 10
        if self.sr_signal[-1] == -1: sell_score += self.weight_sr / 10
        if self.ob_signal[-1] == 1: buy_score += self.weight_ob / 10
        if self.ob_signal[-1] == -1: sell_score += self.weight_ob / 10
        if self.fvg_signal[-1] == 1: buy_score += self.weight_fvg / 10
        if self.fvg_signal[-1] == -1: sell_score += self.weight_fvg / 10
        if self.mss_signal[-1] == 1: buy_score += self.weight_mss / 10
        if self.mss_signal[-1] == -1: sell_score += self.weight_mss / 10
            
        is_uptrend = self.trend_signal.iloc[-1]
        if is_uptrend: sell_score *= (self.penalty_factor / 10)
        else: buy_score *= (self.penalty_factor / 10)

        threshold = self.signal_threshold / 10
        if buy_score >= threshold and buy_score > sell_score:
            self.buy(sl=self.data.Close[-1] - self.atr[-1] * 1.5, tp=self.data.Close[-1] + self.atr[-1] * 3)
        elif sell_score >= threshold and sell_score > buy_score:
            self.sell(sl=self.data.Close[-1] + self.atr[-1] * 1.5, tp=self.data.Close[-1] - self.atr[-1] * 3)


if __name__ == "__main__":
    log.info("="*60)
    log.info("INICIANDO BACKTESTING Y OPTIMIZACIÓN MULTI-PAR")
    log.info("="*60)

    # El script se ejecutará para todos los pares en esta lista y luego terminará.
    PAIRS_TO_BACKTEST = settings.TRADING_PAIRS
    all_stats = {}

    for pair in PAIRS_TO_BACKTEST:
        log.info(f"--- PROCESANDO PAR: {pair} ---")
        
        data_fetcher = DataFetcher(pair=pair, interval='1h')
        df = data_fetcher.fetch_data(period="730d")

        if df.empty or len(df) < 200: # Requiere un mínimo de datos
            log.warning(f"No hay suficientes datos para {pair}. Saltando al siguiente.")
            continue

        df.columns = [col.capitalize() for col in df.columns]
        QFCSystemBacktest.pair = pair
        
        bt = Backtest(df, QFCSystemBacktest, cash=100_000, commission=.001)

        log.info(f"Ejecutando OPTIMIZACIÓN para {pair}... (Esto puede tardar)")
        
        stats = bt.optimize(
            weight_sr=range(5, 21, 5),      
            weight_ob=range(10, 31, 5),     
            weight_fvg=range(5, 21, 5),      
            weight_mss=range(15, 31, 5),     
            signal_threshold=range(25, 41, 5),  
            penalty_factor=range(1, 6, 2), # Prueba penalizaciones de 0.1, 0.3, 0.5
            maximize='Sharpe Ratio'
        )
        all_stats[pair] = stats
        
        log.info(f"--- RESULTADOS ÓPTIMOS PARA {pair} ---")
        print(stats)
        log.info(f"--- PARÁMETROS ÓPTIMOS PARA {pair} (recuerda dividir por 10) ---")
        print(stats._strategy)
        # bt.plot(filename=f"backtest_{pair.replace('=X', '')}", open_browser=False)

    log.info("="*60)
    log.info("RESUMEN FINAL DE OPTIMIZACIÓN MULTI-PAR")
    log.info("="*60)
    for pair, stats in all_stats.items():
        log.info(f"Resultados para {pair}:")
        print(f"  Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
        print(f"  Return [%]: {stats['Return [%]']:.2f}")
        print(f"  Win Rate [%]: {stats['Win Rate [%]']:.2f}")
        print(f"  Parámetros Óptimos: {stats._strategy}\n")

    log.info("PROCESO DE BACKTESTING COMPLETADO.")
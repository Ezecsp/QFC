import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy
from qfc.utils.data_fetcher import DataFetcher
from config.logger_config import log
from qfc.strategies.support_resistance_strategy import SupportResistanceStrategy
from qfc.strategies.order_block_strategy import OrderBlockStrategy
from qfc.strategies.fvg_strategy import FvgStrategy

class QFCSystemBacktest(Strategy):
    pair = "UNKNOWN"
    
    # --- ¡PARÁMETROS A OPTIMIZAR! ---
    # Nota: backtesting.py prefiere enteros, así que optimizamos valores x10
    weight_sr = 10         # 1.0
    weight_ob = 15         # 1.5
    weight_fvg = 10        # 1.0
    signal_threshold = 25  # 2.5

    def init(self):
        df = self.data.df.copy()
        df.columns = [col.lower() for col in df.columns]

        # Instanciamos y ejecutamos cada estrategia para generar las señales
        sr_analyzer = SupportResistanceStrategy({'lookback_period': 90, 'peak_distance': 5, 'zone_creation_threshold_pct': 0.002})
        ob_analyzer = OrderBlockStrategy({'lookback': 75, 'breakout_candles': 3})
        fvg_analyzer = FvgStrategy({'min_size_pct': 0.001})
        
        df = sr_analyzer.analyze(df, self.pair)
        df = ob_analyzer.analyze(df, self.pair)
        df = fvg_analyzer.analyze(df, self.pair)
        
        self.sr_signal = self.I(lambda: df['sr_position'], name="sr_signal")
        self.ob_signal = self.I(lambda: df['ob_signal'], name="ob_signal")
        self.fvg_signal = self.I(lambda: df['fvg_signal'], name="fvg_signal")
        
        self.atr = self.I(ta.atr, pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(self.data.Close), length=14)

    def next(self):
        if self.position:
            return

        # Replicamos la lógica de puntuación, dividiendo los pesos por 10
        buy_score = 0
        if self.sr_signal[-1] == 1: buy_score += self.weight_sr / 10
        if self.ob_signal[-1] == 1: buy_score += self.weight_ob / 10
        if self.fvg_signal[-1] == 1: buy_score += self.weight_fvg / 10

        sell_score = 0
        if self.sr_signal[-1] == -1: sell_score += self.weight_sr / 10
        if self.ob_signal[-1] == -1: sell_score += self.weight_ob / 10
        if self.fvg_signal[-1] == -1: sell_score += self.weight_fvg / 10
            
        threshold = self.signal_threshold / 10
        
        if buy_score >= threshold and buy_score > sell_score:
            self.buy(sl=self.data.Close[-1] - self.atr[-1] * 1.5, tp=self.data.Close[-1] * 3)
        elif sell_score >= threshold and sell_score > buy_score:
            self.sell(sl=self.data.Close[-1] + self.atr[-1] * 1.5, tp=self.data.Close[-1] * 3)


if __name__ == "__main__":
    PAIR_TO_BACKTEST = 'EURUSD=X'
    log.info(f"Obteniendo datos para la optimización de {PAIR_TO_BACKTEST}...")
    data_fetcher = DataFetcher(pair=PAIR_TO_BACKTEST, interval='1h')
    df = data_fetcher.fetch_data(period="730d")
    df.columns = [col.capitalize() for col in df.columns]
    QFCSystemBacktest.pair = PAIR_TO_BACKTEST
    
    bt = Backtest(df, QFCSystemBacktest, cash=100_000, commission=.001)

    log.info("Ejecutando OPTIMIZACIÓN del sistema de puntuación...")
    
    stats = bt.optimize(
        weight_sr=range(5, 21, 5),          # Prueba pesos 0.5, 1.0, 1.5, 2.0
        weight_ob=range(10, 31, 5),         # Prueba pesos 1.0, 1.5, 2.0, 2.5, 3.0
        weight_fvg=range(5, 21, 5),         # Prueba pesos 0.5, 1.0, 1.5, 2.0
        signal_threshold=range(20, 41, 5),  # Prueba umbrales 2.0, 2.5, 3.0, 3.5, 4.0
        maximize='Sharpe Ratio'
    )

    log.info("--- MEJORES RESULTADOS DE LA OPTIMIZACIÓN ---")
    print(stats)
    log.info("--- PARÁMETROS ÓPTIMOS (PESOS x10 Y UMBRAL x10) ---")
    print(stats._strategy)
    bt.plot()
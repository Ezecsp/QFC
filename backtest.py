import pandas as pd
from backtesting import Backtest, Strategy
from config import settings
from qfc.utils.data_fetcher import DataFetcher
from config.logger_config import log
from scipy.signal import find_peaks


def _cluster_levels_into_zones(levels: list, threshold_pct: float) -> list:
    if not levels: return []
    levels.sort()
    zones = []
    current_zone_start = levels[0]
    for i in range(1, len(levels)):
        if levels[i] > current_zone_start * (1 + threshold_pct):
            zones.append((current_zone_start, levels[i-1]))
            current_zone_start = levels[i]
    zones.append((current_zone_start, levels[-1]))
    return zones

class QFCBacktestStrategy(Strategy):
    pair = "UNKNOWN"
    # --- ¡PARÁMETROS A OPTIMIZAR! ---
    # Les damos un valor por defecto, pero el optimizador los cambiará.
    sr_lookback = 100
    sr_peak_distance = 10
    trend_filter_period = 200

    def init(self):
        self.atr = self.I(lambda x: pd.Series(x).rolling(14).mean(), self.data.High - self.data.Low, name='ATR')
        self.sma_trend = self.I(lambda x: pd.Series(x).rolling(self.trend_filter_period).mean(), self.data.Close, name='SMA_Trend')

    def next(self):
        if len(self.data.Close) < self.trend_filter_period: return

        history = self.data.df.iloc[:len(self.data)-1]
        if len(history) < self.sr_lookback: return

        lookback_data = history.tail(self.sr_lookback)
        resistance_indices, _ = find_peaks(lookback_data['High'], distance=self.sr_peak_distance)
        support_indices, _ = find_peaks(-lookback_data['Low'], distance=self.sr_peak_distance)
        raw_resistances = lookback_data['High'].iloc[resistance_indices].unique().tolist()
        raw_supports = lookback_data['Low'].iloc[support_indices].unique().tolist()
        resistance_zones = _cluster_levels_into_zones(raw_resistances, 0.002)
        support_zones = _cluster_levels_into_zones(raw_supports, 0.002)

        current_price = self.data.Close[-1]
        is_uptrend = current_price > self.sma_trend[-1]
        is_in_support_zone = any(start <= current_price <= end for start, end in support_zones)
        is_in_resistance_zone = any(start <= current_price <= end for start, end in resistance_zones)
        
        if self.position: return

        if is_in_support_zone and is_uptrend:
            self.buy(sl=current_price - (self.atr[-1] * 1.5), tp=current_price + (self.atr[-1] * 3))
        elif is_in_resistance_zone and not is_uptrend:
            self.sell(sl=current_price + (self.atr[-1] * 1.5), tp=current_price - (self.atr[-1] * 3))


if __name__ == "__main__":
    PAIR_TO_BACKTEST = 'BTC-USD'
    log.info(f"Obteniendo datos para la optimización de {PAIR_TO_BACKTEST}...")
    data_fetcher = DataFetcher(pair=PAIR_TO_BACKTEST, interval='1h')
    df = data_fetcher.fetch_data(period="730d", interval_override='1h')
    df.columns = [col.capitalize() for col in df.columns]
    QFCBacktestStrategy.pair = PAIR_TO_BACKTEST
    
    bt = Backtest(df, QFCBacktestStrategy, cash=1_000_000, commission=.002)

    log.info("Ejecutando OPTIMIZACIÓN de la estrategia... (Esto puede tardar varios minutos)")
    
    # Le decimos al backtester qué parámetros probar y en qué rangos
    stats = bt.optimize(
        sr_lookback=range(50, 151, 10),      # Probar lookbacks de 50 a 150, en pasos de 10
        sr_peak_distance=range(5, 21, 5),    # Probar distancias de picos de 5 a 20, en pasos de 5
        trend_filter_period=range(150, 251, 50), # Probar filtros de tendencia de 150 a 250
        maximize='Equity Final [$]',         # El objetivo es maximizar la equidad final
        constraint=lambda p: p.sr_peak_distance * 2 < p.sr_lookback # Restricción lógica
    )

    log.info("--- MEJORES RESULTADOS DE LA OPTIMIZACIÓN ---")
    print(stats)
    log.info("--- PARÁMETROS ÓPTIMOS ---")
    print(stats._strategy)

    log.info("Generando gráfico de la mejor ejecución...")
    bt.plot(plot_drawdown=True, plot_equity=True)
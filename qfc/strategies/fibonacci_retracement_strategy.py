import pandas as pd
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class FibonacciRetracementStrategy(BaseStrategy):
    """
    Estrategia que identifica niveles de Fibonacci y genera señales
    cuando el precio rebota en los niveles clave en las velas más recientes.
    """
    def __init__(self, config: dict):
        super().__init__(config)
        self.lookback_period = self.config.get("lookback_period", 150)
        self.key_ratios = self.config.get("key_ratios", [0.5, 0.618])
        self.touch_proximity_pct = self.config.get("touch_proximity_pct", 0.001)
        # Cuántas de las últimas velas queremos revisar para una señal
        self.candles_to_check = self.config.get("candles_to_check", 3)
        log.info("Estrategia 'FibonacciRetracement' (Optimizada) inicializada.")

    def analyze(self, data: pd.DataFrame) -> pd.DataFrame:
        log.info("Ejecutando análisis de estrategia: FibonacciRetracement...")
        df = data.copy()
        
        # 1. Calcular los niveles de Fibonacci
        lookback_data = df.iloc[-self.lookback_period:]
        swing_high_price = lookback_data['high'].max()
        swing_low_price = lookback_data['low'].min()
        
        is_uptrend = lookback_data['high'].idxmax() > lookback_data['low'].idxmin()
        price_range = swing_high_price - swing_low_price
        
        if price_range == 0:
            return df
        
        # 2. Lógica de Señal Optimizada
        df['fibo_position'] = 0
        
        # Solo revisamos las N últimas velas en lugar de todo el DataFrame.
        recent_candles = df.tail(self.candles_to_check)
        
        for i in range(len(recent_candles)):
            candle = recent_candles.iloc[i]
            
            for ratio in self.key_ratios: # Nos aseguramos de usar los ratios correctos
                level = 0
                if is_uptrend:
                    level = swing_high_price - price_range * ratio
                    if level <= candle['low'] <= level * (1 + self.touch_proximity_pct) and candle['close'] > level:
                        df.at[candle.name, 'fibo_position'] = 1
                        log.info(f"Rebote alcista en Fibo {ratio*100:.1f}% detectado en {candle.name}")
                else:
                    level = swing_low_price + price_range * ratio
                    if level * (1 - self.touch_proximity_pct) <= candle['high'] <= level and candle['close'] < level:
                        df.at[candle.name, 'fibo_position'] = -1
                        log.info(f"Rechazo bajista en Fibo {ratio*100:.1f}% detectado en {candle.name}")
                        
        return df
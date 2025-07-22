import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import asyncio
from config.logger_config import log
from config import settings
from qfc.utils.data_fetcher import DataFetcher
from qfc.utils.telegram_notifier import TelegramNotifier
from qfc.utils.whatsapp_notifier import WhatsAppNotifier
from qfc.agents.analyst_agent import AnalystAgent
from qfc.agents.market_selector_agent import MarketSelectorAgent
from qfc.agents.coordinator_agent import CoordinatorAgent

# (La función visualize_trades no cambia, se puede mantener la de la respuesta anterior)
def visualize_trades(data: pd.DataFrame, pair: str):
    if data.empty: return
    fig, ax = plt.subplots(figsize=(17, 9))
    ax.plot(data.index, data['close'], label='Precio', color='black', alpha=0.8, zorder=5)
    # ... (código de visualización completo de la respuesta anterior)
    if 'position' in data.columns:
        last_signal = data.iloc[-1]
        if last_signal['position'] > 0:
            ax.plot(data.index[-1], last_signal['close'], '^', markersize=15, color='lime', markeredgecolor='black', label='ALERTA COMPRA', zorder=10)
        elif last_signal['position'] < 0:
            ax.plot(data.index[-1], last_signal['close'], 'v', markersize=15, color='red', markeredgecolor='black', label='ALERTA VENTA', zorder=10)
    ax.legend()
    plt.grid(True)


async def main():
    log.info("--- INICIANDO QUANTUM FOREX COLLECTIVE (QFC) ---")
    
    selector_agent = MarketSelectorAgent(config=settings.MARKET_SELECTOR_CONFIG)
    ranked_pairs = selector_agent.rank_pairs_by_volatility(pairs=settings.TRADING_PAIRS)
    if not ranked_pairs: return
    log.info(f"Pares del día: {ranked_pairs}")
        
    log.info("\n>>> Fase de Análisis y Coordinación...")
    analyst_agent = AnalystAgent(config=settings.ANALYST_AGENT_CONFIG)
    coordinator_agent = CoordinatorAgent(config=settings.COORDINATOR_CONFIG)
    telegram_notifier = TelegramNotifier(config=settings.TELEGRAM_CONFIG)
    whatsapp_notifier = WhatsAppNotifier(config=settings.WHATSAPP_CONFIG)
    
    weights = settings.SCORING_CONFIG['weights']
    signal_threshold = settings.SCORING_CONFIG['signal_threshold']
    
    for pair_info in ranked_pairs:
        pair = pair_info['pair']
        log.info(f"--- Procesando {pair} ---")

        # 1. ANÁLISIS DE TENDENCIA EN TIMEFRAME SUPERIOR (4h)
        log.info(f"Analizando tendencia para {pair} en timeframe de 4h...")
        trend_fetcher = DataFetcher(pair=pair, interval='4h')
        df_trend = trend_fetcher.fetch_data(period="730d")
        
        is_uptrend = None
        if not df_trend.empty:
            df_trend['ema_trend'] = ta.ema(df_trend['close'], length=50)
            last_price = df_trend['close'].iloc[-1]
            last_ema = df_trend['ema_trend'].iloc[-1]
            if pd.notna(last_ema):
                is_uptrend = last_price > last_ema
                log.info(f"Tendencia principal para {pair} es: {'ALCISTA' if is_uptrend else 'BAJISTA'}")

        # 2. ANÁLISIS DE SEÑALES EN TIMEFRAME DE TRADING
        data_fetcher = DataFetcher(pair=pair, interval=settings.ANALYST_AGENT_CONFIG['timeframe'])
        historical_data = data_fetcher.fetch_data()
            
        if not historical_data.empty:
            analysis_result = analyst_agent.analyze(historical_data, pair=pair)
            
            if not analysis_result.empty:
                last_signal = analysis_result.iloc[-1]
                buy_score, sell_score = 0, 0
                buy_reasons, sell_reasons = [], []

                # Puntuación de estrategias
                if 'sr_position' in last_signal and last_signal['sr_position'] == 1: buy_score += weights['support_resistance']; buy_reasons.append("Rebote en Soporte")
                if 'sr_position' in last_signal and last_signal['sr_position'] == -1: sell_score += weights['support_resistance']; sell_reasons.append("Rechazo en Resistencia")
                if 'ob_signal' in last_signal and last_signal['ob_signal'] == 1: buy_score += weights['order_block']; buy_reasons.append("Testeo de OB Alcista")
                if 'ob_signal' in last_signal and last_signal['ob_signal'] == -1: sell_score += weights['order_block']; sell_reasons.append("Testeo de OB Bajista")
                if 'fvg_signal' in last_signal and last_signal['fvg_signal'] == 1: buy_score += weights['fvg']; buy_reasons.append("Reacción a FVG Alcista")
                if 'fvg_signal' in last_signal and last_signal['fvg_signal'] == -1: sell_score += weights['fvg']; sell_reasons.append("Reacción a FVG Bajista")

                # 3. APLICACIÓN DEL FILTRO DE TENDENCIA
                if is_uptrend is not None:
                    if is_uptrend:
                        sell_score *= weights['counter_trend_penalty']
                        if buy_score > 0: buy_reasons.append("A Favor de Tendencia 4h")
                    else:
                        buy_score *= weights['counter_trend_penalty']
                        if sell_score > 0: sell_reasons.append("A Favor de Tendencia 4h")

                # (Lógica de ML, Veto y Decisión Final sin cambios)
                # ...
                
    log.info("\n--- QFC: ANÁLISIS DIARIO COMPLETADO ---")
    if settings.SHOW_PLOTS:
        plt.show()

if __name__ == "__main__":
    asyncio.run(main())
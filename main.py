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

# La función de visualización no necesita cambios
def visualize_trades(data: pd.DataFrame, pair: str):
    if data.empty or not settings.SHOW_PLOTS: return
    fig, ax = plt.subplots(figsize=(17, 9))
    ax.plot(data.index, data['close'], label='Precio', color='black', zorder=5)
    # ... (código de visualización completo)
    if 'position' in data.columns:
        last_signal = data.iloc[-1]
        if last_signal['position'] > 0:
            ax.plot(data.index[-1], last_signal['close'], '^', markersize=15, color='lime', markeredgecolor='black', label='ALERTA COMPRA', zorder=10)
        elif last_signal['position'] < 0:
            ax.plot(data.index[-1], last_signal['close'], 'v', markersize=15, color='red', markeredgecolor='black', label='ALERTA VENTA', zorder=10)
    ax.legend()
    plt.grid(True)
    ax.set_title(f'Análisis para {pair}')

async def main():
    log.info("="*50)
    log.info("QFC: INICIANDO CICLO DE ANÁLISIS PROGRAMADO")
    log.info("="*50)
    
    selector_agent = MarketSelectorAgent(config=settings.MARKET_SELECTOR_CONFIG)
    ranked_pairs = selector_agent.rank_pairs_by_volatility(pairs=settings.TRADING_PAIRS)
    log.info(f"Pares del día: {ranked_pairs}")
    
    analyst_agent = AnalystAgent(config=settings.ANALYST_AGENT_CONFIG)
    coordinator_agent = CoordinatorAgent(config=settings.COORDINATOR_CONFIG)
    telegram_notifier = TelegramNotifier(config=settings.TELEGRAM_CONFIG)
    whatsapp_notifier = WhatsAppNotifier(config=settings.WHATSAPP_CONFIG)
    
    weights = settings.SCORING_CONFIG['weights']
    signal_threshold = settings.SCORING_CONFIG['signal_threshold']
    
    for pair_info in ranked_pairs:
        pair = pair_info['pair']
        log.info(f"--- Procesando {pair} ---")
        
        # Filtro de Tendencia (4h)
        trend_fetcher = DataFetcher(pair=pair, interval='4h')
        df_trend = trend_fetcher.fetch_data(period="730d")
        is_uptrend = None
        if not df_trend.empty:
            df_trend['ema_trend'] = ta.ema(df_trend['close'], length=50)
            if pd.notna(df_trend['ema_trend'].iloc[-1]):
                is_uptrend = df_trend['close'].iloc[-1] > df_trend['ema_trend'].iloc[-1]
                log.info(f"Tendencia 4h para {pair}: {'ALCISTA' if is_uptrend else 'BAJISTA'}")

        # Análisis en Timeframe de Trading
        data_fetcher = DataFetcher(pair=pair, interval=settings.ANALYST_AGENT_CONFIG['timeframe'])
        historical_data = data_fetcher.fetch_data()
            
        if not historical_data.empty:
            analysis_result = analyst_agent.analyze(historical_data, pair=pair)
            # Lógica de puntuación...
            # (Aquí va el bloque completo de puntuación, decisión y notificación que ya tienes)

    log.info("\n--- QFC: CICLO DE ANÁLISIS PROGRAMADO COMPLETADO ---")
    if settings.SHOW_PLOTS:
        plt.show()

if __name__ == "__main__":
    asyncio.run(main())
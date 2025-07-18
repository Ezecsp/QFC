import matplotlib.pyplot as plt
import pandas as pd
import asyncio
import logging  # Importamos logging para poder cambiar el nivel
from config.logger_config import log
from config import settings
from qfc.utils.data_fetcher import DataFetcher
from qfc.utils.telegram_notifier import TelegramNotifier
from qfc.utils.whatsapp_notifier import WhatsAppNotifier
from qfc.agents.analyst_agent import AnalystAgent
from qfc.agents.market_selector_agent import MarketSelectorAgent
from qfc.agents.coordinator_agent import CoordinatorAgent

def visualize_trades(data: pd.DataFrame, pair: str):
    """
    Crea un gráfico para visualizar el precio y las señales de trading.
    """
    if data.empty:
        log.warning(f"No hay datos de análisis para visualizar para {pair}.")
        return

    fig = plt.figure(figsize=(15, 7))
    ax = fig.add_subplot(111)

    ax.plot(data.index, data['close'], label='Precio de Cierre', color='black', alpha=0.7)
    short_sma_col = f'sma_{settings.ANALYST_AGENT_CONFIG["sma_short_window"]}'
    long_sma_col = f'sma_{settings.ANALYST_AGENT_CONFIG["sma_long_window"]}'
    ax.plot(data.index, data[short_sma_col], label='SMA Corta', color='blue', alpha=0.9, linestyle='--')
    ax.plot(data.index, data[long_sma_col], label='SMA Larga', color='orange', alpha=0.9, linestyle='--')

    buy_signals = data[data['position'] == 1]
    ax.plot(buy_signals.index, buy_signals['close'], '^', markersize=10, color='green', lw=0, label='Señal de Compra')
    
    sell_signals = data[data['position'] == -1]
    ax.plot(sell_signals.index, sell_signals['close'], 'v', markersize=10, color='red', lw=0, label='Señal de Venta')

    ax.set_title(f'Análisis de Trading para {pair} - Estrategia: {settings.ANALYST_AGENT_CONFIG["strategy_name"]}')
    ax.set_ylabel('Precio')
    ax.legend(loc='best')
    ax.grid(True)


async def main():
    log.info("--- INICIANDO QUANTUM FOREX COLLECTIVE (QFC) ---")
    
    # --- FASE DE SELECCIÓN (AGENTE 2) ---
    log.info(">>> Fase de Selección: Activando Agente 2...")
    selector_agent = MarketSelectorAgent(config=settings.MARKET_SELECTOR_CONFIG)
    ranked_pairs = selector_agent.rank_pairs_by_volatility(pairs=settings.TRADING_PAIRS)
    
    if not ranked_pairs:
        log.critical("El Agente 2 no pudo rankear ningún par. Finalizando ejecución.")
        return

    log.info(f"Pares del día, rankeados por volatilidad: {ranked_pairs}")
        
    # --- FASE DE ANÁLISIS Y COORDINACIÓN (AGENTES 3 Y 4) ---
    log.info("\n>>> Fase de Análisis y Coordinación...")
    analyst_agent = AnalystAgent(config=settings.ANALYST_AGENT_CONFIG)
    coordinator_agent = CoordinatorAgent(config=settings.COORDINATOR_CONFIG)
    telegram_notifier = TelegramNotifier(config=settings.TELEGRAM_CONFIG)
    whatsapp_notifier = WhatsAppNotifier(config=settings.WHATSAPP_CONFIG)
    
    for pair_info in ranked_pairs:
        pair = pair_info['pair']
        log.info(f"--- Procesando {pair} ---")
            
        data_fetcher = DataFetcher(pair=pair, interval=settings.ANALYST_AGENT_CONFIG['timeframe'])
        historical_data = data_fetcher.fetch_data()
            
        if not historical_data.empty:
            analysis_result = analyst_agent.analyze(historical_data)
                
            if not analysis_result.empty:
                last_signal = analysis_result.iloc[-1]
                    
                if last_signal['position'] in [1, -1]:
                    log.info(f"¡NUEVA SEÑAL DETECTADA PARA {pair}!")
                    
                    base_plan = coordinator_agent._create_base_plan(
                        last_signal=last_signal, pair=pair,
                        strategy=settings.ANALYST_AGENT_CONFIG['strategy_name'],
                        analysis_data=analysis_result.copy()
                    )

                    if base_plan:
                        # 2. Formateamos y enviamos a Telegram
                        telegram_plan = coordinator_agent.format_telegram_plan(base_plan)
                        await telegram_notifier.send_message(telegram_plan)

                        # 3. Formateamos y enviamos a WhatsApp
                        whatsapp_plan = coordinator_agent.format_whatsapp_plan(base_plan)
                        await whatsapp_notifier.send_message(whatsapp_plan)
                else:
                    log.info(f"No hay nueva señal de cruce para {pair}. Tendencia actual: {int(last_signal['signal'])}")

                visualize_trades(analysis_result, pair)
            else:
                log.warning(f"El análisis para {pair} no produjo resultados.")
        else:
            log.warning(f"No se pudieron obtener datos históricos para {pair}.")
    
    log.info("\n--- QFC: ANÁLISIS DIARIO COMPLETADO ---")
    plt.show()


if __name__ == "__main__":
    # La línea sobre cambiar el logging level daba error si el agente no existía, la quitamos por simplicidad.
    asyncio.run(main())
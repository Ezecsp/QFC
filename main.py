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
    Crea un gráfico para visualizar el precio, señales y ZONAS de trading.
    """
    if data.empty:
        log.warning(f"No hay datos de análisis para visualizar para {pair}.")
        return

    fig = plt.figure(figsize=(15, 7))
    ax = fig.add_subplot(111)

    ax.plot(data.index, data['close'], label='Precio de Cierre', color='black', alpha=0.7)

    # --- Bloque para SMACrossover ---
    if 'sma_short' in data.columns and 'sma_long' in data.columns:
        ax.plot(data.index, data['sma_short'], label='SMA Corta', color='blue', alpha=0.9, linestyle='--')
        ax.plot(data.index, data['sma_long'], label='SMA Larga', color='orange', alpha=0.9, linestyle='--')
    if 'position' in data.columns:
        buy_signals = data[data['position'] > 0]
        ax.plot(buy_signals.index, buy_signals['close'], '^', markersize=10, color='green', lw=0, label='Cruce SMA Compra')
        sell_signals = data[data['position'] < 0]
        ax.plot(sell_signals.index, sell_signals['close'], 'v', markersize=10, color='red', lw=0, label='Cruce SMA Venta')

    # Dibujamos las zonas como rectángulos semitransparentes
    if 'support_zones' in data.columns and not data['support_zones'].empty:
        s_zones = data['support_zones'].iloc[0]
        for start, end in s_zones:
            ax.axhspan(start, end, color='limegreen', alpha=0.2)
        if s_zones:
            ax.plot([], [], color='limegreen', alpha=0.4, linewidth=5, label='Zona de Soporte')

    if 'resistance_zones' in data.columns and not data['resistance_zones'].empty:
        r_zones = data['resistance_zones'].iloc[0]
        for start, end in r_zones:
            ax.axhspan(start, end, color='tomato', alpha=0.2)
        if r_zones:
            ax.plot([], [], color='tomato', alpha=0.4, linewidth=5, label='Zona de Resistencia')
            
    # --- Configuración final del gráfico ---
    executed_strategies = ', '.join(settings.ANALYST_AGENT_CONFIG.get("strategies_to_run", ["N/A"]))
    ax.set_title(f'Análisis de Trading para {pair} - Estrategias: {executed_strategies}')
    ax.set_ylabel('Precio')
    ax.legend(loc='best')
    ax.grid(True)


async def main():
    log.info("--- INICIANDO QUANTUM FOREX COLLECTIVE (QFC) ---")
    
    # ... (Fase de Selección no cambia) ...
    log.info(">>> Fase de Selección: Activando Agente Selector...")
    selector_agent = MarketSelectorAgent(config=settings.MARKET_SELECTOR_CONFIG)
    ranked_pairs = selector_agent.rank_pairs_by_volatility(pairs=settings.TRADING_PAIRS)
    if not ranked_pairs: return
    log.info(f"Pares del día, rankeados por volatilidad: {ranked_pairs}")
        
    # --- FASE DE ANÁLISIS Y COORDINACIÓN ---
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
            analysis_result = analyst_agent.analyze(historical_data, pair=pair)
                
            if not analysis_result.empty:
                last_signal = analysis_result.iloc[-1]
                
                # --- LÓGICA DE CONFLUENCIA FINAL CON FILTRO DE ML ---
                sr_buy = 'sr_position' in last_signal and last_signal['sr_position'] == 1
                sr_sell = 'sr_position' in last_signal and last_signal['sr_position'] == -1
                ml_confirm_buy = 'ml_position' in last_signal and last_signal['ml_position'] == 1
                ml_confirm_sell = 'ml_position' in last_signal and last_signal['ml_position'] == -1

                signal_reason = None
                
                # Escenario 1: Rebote en Soporte CONFIRMADO por el modelo de ML
                if sr_buy and ml_confirm_buy:
                    signal_reason = "CONFIRMACIÓN ML: Rebote en Zona de Soporte"
                
                # Escenario 2: Rechazo en Resistencia CONFIRMADO por el modelo de ML
                elif sr_sell and ml_confirm_sell:
                    signal_reason = "CONFIRMACIÓN ML: Rechazo en Zona de Resistencia"

                if signal_reason:
                    log.info(f"¡ALERTA DE ALTA PROBABILIDAD (ML) DETECTADA PARA {pair}!")
                    log.info(f"Razón: {signal_reason}")
                    
                    base_plan = coordinator_agent._create_base_plan(last_signal=last_signal, pair=pair, reason=signal_reason, analysis_data=analysis_result.copy())
                    if base_plan:
                        telegram_plan = coordinator_agent.format_telegram_plan(base_plan)
                        await telegram_notifier.send_message(telegram_plan)
                        whatsapp_plan = coordinator_agent.format_whatsapp_plan(base_plan)
                        await whatsapp_notifier.send_message(whatsapp_plan)
                else:
                    log.info(f"No hay señales de confluencia confirmadas por ML para {pair} en la última vela.")

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
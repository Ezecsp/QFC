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
    if data.empty or not settings.SHOW_PLOTS:
        return
    fig, ax = plt.subplots(figsize=(17, 9))
    ax.plot(data.index, data['close'], label='Precio', color='black', zorder=5)
    # ... (código de visualización completo - asumiendo que está en tu versión original)
    # Ejemplo básico de visualización de zonas de soporte/resistencia si existieran
    # (Este bloque es un placeholder, reemplázalo con tu código de visualización completo)
    # if 'sr_zones' in data.columns:
    #     for zone_start, zone_end in data['sr_zones'].iloc[-1]: # Ejemplo para la última vela
    #         ax.axhspan(zone_start, zone_end, color='blue', alpha=0.2)

    # Visualización de señales finales
    if 'position' in data.columns:
        last_signal_index = data.index[-1]
        last_signal_position = data.loc[last_signal_index, 'position']
        last_signal_close = data.loc[last_signal_index, 'close']
        if last_signal_position > 0:
            ax.plot(last_signal_index, last_signal_close, '^', markersize=15, color='lime', markeredgecolor='black', label='ALERTA COMPRA', zorder=10)
        elif last_signal_position < 0:
            ax.plot(last_signal_index, last_signal_close, 'v', markersize=15, color='red', markeredgecolor='black', label='ALERTA VENTA', zorder=10)
    ax.legend()
    plt.grid(True)
    ax.set_title(f'Análisis para {pair}')
    plt.show() # Muestra el gráfico si SHOW_PLOTS es True

async def main():
    log.info("="*50)
    log.info("QFC: INICIANDO CICLO DE ANÁLISIS PROGRAMADO")
    log.info("="*50)
    selector_agent = MarketSelectorAgent(config=settings.MARKET_SELECTOR_CONFIG)
    ranked_pairs = selector_agent.rank_pairs_by_volatility(pairs=settings.TRADING_PAIRS)
    if not ranked_pairs:
        log.error("No se pudieron rankear los pares. Finalizando ciclo.")
        return

    log.info(f"Pares del día: {ranked_pairs}")
    analyst_agent = AnalystAgent(config=settings.ANALYST_AGENT_CONFIG)
    coordinator_agent = CoordinatorAgent(config=settings.COORDINATOR_CONFIG)
    telegram_notifier = TelegramNotifier(config=settings.TELEGRAM_CONFIG)
    whatsapp_notifier = WhatsAppNotifier(config=settings.WHATSAPP_CONFIG)

    weights = settings.SCORING_CONFIG['weights']
    signal_threshold = settings.SCORING_CONFIG['signal_threshold']
    penalty_factor = weights.get('counter_trend_penalty', 0.3) # Obtener el factor de penalización

    for pair_info in ranked_pairs:
        pair = pair_info['pair']
        log.info(f"--- Procesando {pair} ---")

        # --- 1. Filtro de Tendencia (4h) ---
        trend_fetcher = DataFetcher(pair=pair, interval='4h')
        df_trend = trend_fetcher.fetch_data(period="730d")
        is_uptrend = None
        if not df_trend.empty:
            df_trend['ema_trend'] = ta.ema(df_trend['close'], length=50)
            if pd.notna(df_trend['ema_trend'].iloc[-1]):
                is_uptrend = df_trend['close'].iloc[-1] > df_trend['ema_trend'].iloc[-1]
                log.info(f"Tendencia 4h para {pair}: {'ALCISTA' if is_uptrend else 'BAJISTA'}")
            else:
                log.warning(f"No se pudo determinar la tendencia 4h para {pair} (EMA no disponible).")
        else:
            log.warning(f"No se obtuvieron datos de tendencia 4h para {pair}.")

        # --- 2. Análisis en Timeframe de Trading ---
        data_fetcher = DataFetcher(pair=pair, interval=settings.ANALYST_AGENT_CONFIG['timeframe'])
        historical_data = data_fetcher.fetch_data()
        if historical_data.empty:
            log.warning(f"No hay datos para {pair} en el timeframe {settings.ANALYST_AGENT_CONFIG['timeframe']}. Saltando.")
            continue

        analysis_result = analyst_agent.analyze(historical_data, pair=pair)
        if analysis_result.empty:
             log.warning(f"El análisis para {pair} no devolvió resultados. Saltando.")
             continue

        # --- 3. LÓGICA DE PUNTUACIÓN DE SEÑALES ---
        log.info(f"--- Calculando puntuación para {pair} ---")
        if analysis_result.empty:
            log.warning(f"DataFrame de análisis vacío para {pair}. Saltando puntuación.")
            continue

        # Obtener la última vela (la que se evaluará para una señal)
        last_row = analysis_result.iloc[-1]
        last_index = analysis_result.index[-1]

        # Inicializar puntuaciones
        buy_score = 0.0
        sell_score = 0.0

        # --- Sumar puntuaciones según las señales de las estrategias ---
        # Soporte/Resistencia
        sr_signal = last_row.get('sr_position', 0)
        if sr_signal == 1:
            buy_score += weights['support_resistance']
            log.debug(f"{pair}: S/R contribuye a COMPRA (+{weights['support_resistance']})")
        elif sr_signal == -1:
            sell_score += weights['support_resistance']
            log.debug(f"{pair}: S/R contribuye a VENTA (+{weights['support_resistance']})")

        # Order Block
        ob_signal = last_row.get('ob_signal', 0)
        if ob_signal == 1:
            buy_score += weights['order_block']
            log.debug(f"{pair}: OB contribuye a COMPRA (+{weights['order_block']})")
        elif ob_signal == -1:
            sell_score += weights['order_block']
            log.debug(f"{pair}: OB contribuye a VENTA (+{weights['order_block']})")

        # FVG
        fvg_signal = last_row.get('fvg_signal', 0)
        if fvg_signal == 1:
            buy_score += weights['fvg']
            log.debug(f"{pair}: FVG contribuye a COMPRA (+{weights['fvg']})")
        elif fvg_signal == -1:
            sell_score += weights['fvg']
            log.debug(f"{pair}: FVG contribuye a VENTA (+{weights['fvg']})")

        # Market Structure Shift
        mss_signal = last_row.get('mss_signal', 0)
        if mss_signal == 1:
            buy_score += weights['market_structure_shift']
            log.debug(f"{pair}: MSS contribuye a COMPRA (+{weights['market_structure_shift']})")
        elif mss_signal == -1:
            sell_score += weights['market_structure_shift']
            log.debug(f"{pair}: MSS contribuye a VENTA (+{weights['market_structure_shift']})")

        # ML Prediction (Bonificación)
        ml_signal = last_row.get('ml_position', 0) # Asegúrate de que esta columna existe
        if ml_signal == 1:
            buy_score += weights['ml_confirmation_bonus']
            log.debug(f"{pair}: ML confirma COMPRA (+{weights['ml_confirmation_bonus']})")
        elif ml_signal == -1:
            sell_score += weights['ml_confirmation_bonus']
            log.debug(f"{pair}: ML confirma VENTA (+{weights['ml_confirmation_bonus']})")

        # --- Aplicar Penalización por Tendencia Contraria ---
        if is_uptrend is not None:
            if is_uptrend and sell_score > 0:
                # Tendencia Alcista, pero señal de Venta
                original_sell_score = sell_score
                sell_score *= penalty_factor
                log.info(f"{pair}: Señal de VENTA ({original_sell_score:.2f}) penalizada por ir contra tendencia alcista. Nueva puntuación: {sell_score:.2f}")
            elif not is_uptrend and buy_score > 0:
                # Tendencia Bajista, pero señal de Compra
                original_buy_score = buy_score
                buy_score *= penalty_factor
                log.info(f"{pair}: Señal de COMPRA ({original_buy_score:.2f}) penalizada por ir contra tendencia bajista. Nueva puntuación: {buy_score:.2f}")
        else:
             log.info(f"{pair}: No se aplica penalización por tendencia (tendencia desconocida).")

        log.info(f"{pair}: Puntuación final - Compra: {buy_score:.2f}, Venta: {sell_score:.2f}")

        # --- 4. DECIDIR SI ENVIAR ALERTA ---
        final_position = 0
        reason = "Sin señal clara"

        if buy_score >= signal_threshold and buy_score > sell_score:
            final_position = 1
            reason = f"Compra confirmada por múltiples estrategias (Puntaje: {buy_score:.2f})"
            # Detallar estrategias contribuyentes
            contributing_strategies = []
            if sr_signal == 1: contributing_strategies.append("Soporte/Resistencia")
            if ob_signal == 1: contributing_strategies.append("Order Block")
            if fvg_signal == 1: contributing_strategies.append("FVG")
            if mss_signal == 1: contributing_strategies.append("Market Structure Shift")
            if ml_signal == 1: contributing_strategies.append("ML Prediction")
            if contributing_strategies:
                reason += f" [{', '.join(contributing_strategies)}]"

        elif sell_score >= signal_threshold and sell_score > buy_score:
            final_position = -1
            reason = f"Venta confirmada por múltiples estrategias (Puntaje: {sell_score:.2f})"
            # Detallar estrategias contribuyentes
            contributing_strategies = []
            if sr_signal == -1: contributing_strategies.append("Soporte/Resistencia")
            if ob_signal == -1: contributing_strategies.append("Order Block")
            if fvg_signal == -1: contributing_strategies.append("FVG")
            if mss_signal == -1: contributing_strategies.append("Market Structure Shift")
            if ml_signal == -1: contributing_strategies.append("ML Prediction")
            if contributing_strategies:
                reason += f" [{', '.join(contributing_strategies)}]"
        else:
             log.info(f"{pair}: No se generó alerta. Puntuaciones insuficientes o conflictivas. (Compra: {buy_score:.2f}, Venta: {sell_score:.2f}, Umbral: {signal_threshold})")


        # --- 5. CREAR PLAN Y ENVIAR NOTIFICACIONES ---
        if final_position != 0:
            log.info(f"🚨 ALERTA GENERADA para {pair}: {reason}")

            # --- VERIFICACIÓN CRÍTICA DEL ATR ---
            # Accedemos directamente al valor en el DataFrame original `analysis_result`
            # Asegurándonos de que el nombre de la columna sea el correcto ('atr' o 'ATRr_14')
            atr_column_name = 'atr' # El nombre esperado después de la corrección en AnalystAgent
            if atr_column_name not in analysis_result.columns:
                 # Si no está, intentamos con el nombre por defecto de pandas-ta
                 atr_column_name = 'ATRr_14'
            
            if atr_column_name not in analysis_result.columns:
                 log.error(f"{pair}: No se puede crear el plan, la columna ATR ('atr' o 'ATRr_14') no se encuentra en los datos.")
                 # Opcional: Asignar position y visualizar
                 analysis_result.loc[last_index, 'position'] = final_position
                 if settings.SHOW_PLOTS:
                      visualize_trades(analysis_result, pair)
                 continue # Saltar a la siguiente iteración del bucle for pair_info

            last_atr_value = analysis_result.loc[last_index, atr_column_name]
            
            if pd.isna(last_atr_value):
                log.error(f"{pair}: No se puede crear el plan, '{atr_column_name}' es NaN en la última vela. Señal descartada.")
                # Opcional: Asignar position y visualizar
                analysis_result.loc[last_index, 'position'] = final_position
                if settings.SHOW_PLOTS:
                     visualize_trades(analysis_result, pair)
                continue # Saltar a la siguiente iteración del bucle for pair_info
            
            # Si ATR está disponible, proceder.
            # Aseguramos que 'atr' esté en last_row para pasarlo al planificador
            last_signal_dict = last_row.to_dict()
            # Si la columna original era 'ATRr_14', la añadimos como 'atr' para el coordinador
            if atr_column_name == 'ATRr_14' and 'atr' not in last_signal_dict:
                last_signal_dict['atr'] = last_atr_value
            last_signal_dict['position'] = final_position
            # --- FIN VERIFICACIÓN CRÍTICA ---

            # Crear el plan de trading
            plan = coordinator_agent._create_base_plan(
                last_signal=last_signal_dict, # Debe incluir 'close' y 'atr'
                pair=pair,
                reason=reason,
                analysis_data=analysis_result # Puede ser útil si _create_base_plan lo necesita
            )

            if plan:
                # Añadir la posición final al DataFrame para visualización
                analysis_result.loc[last_index, 'position'] = final_position

                # Formatear mensajes
                telegram_message = coordinator_agent.format_telegram_plan(plan)
                whatsapp_message = coordinator_agent.format_whatsapp_plan(plan)

                # Enviar notificaciones de forma asíncrona
                try:
                    await asyncio.gather(
                        telegram_notifier.send_message(telegram_message),
                        whatsapp_notifier.send_message(whatsapp_message)
                    )
                    log.info(f"{pair}: Notificaciones enviadas exitosamente.")
                except Exception as e:
                    log.error(f"{pair}: Error al enviar notificaciones: {e}")

                # Visualizar (opcional)
                if settings.SHOW_PLOTS:
                     # Pasamos una copia para evitar modificar el original en visualize_trades
                     visualize_trades(analysis_result.copy(), pair) 
            else:
                log.error(f"{pair}: No se pudo crear un plan de trading válido para la señal.")
                # Opcional: Asignar position y visualizar
                analysis_result.loc[last_index, 'position'] = final_position
                if settings.SHOW_PLOTS:
                     visualize_trades(analysis_result, pair)

        else: # if final_position == 0
            # Opcional: Limpiar la columna 'position' si existe y no hay señal
            if 'position' in analysis_result.columns:
                 analysis_result.loc[last_index, 'position'] = 0
            # Opcional: Visualizar sin alerta
            if settings.SHOW_PLOTS:
                 visualize_trades(analysis_result, pair)
        # --- FIN LÓGICA DE PUNTUACIÓN Y NOTIFICACIÓN PARA ESTE PAR ---

    log.info("\n--- QFC: CICLO DE ANÁLISIS PROGRAMADO COMPLETADO ---")
    # Si se usan gráficos y se desea que se mantengan abiertos al final
    # if settings.SHOW_PLOTS:
    #     plt.show(block=True) # Bloquea hasta que se cierren las ventanas

if __name__ == "__main__":
    asyncio.run(main())
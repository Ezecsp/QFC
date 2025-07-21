from config.logger_config import log
import pandas as pd 

class CoordinatorAgent:
    def __init__(self, config: dict):
        self.risk_reward_ratio = config.get("risk_reward_ratio", 1.5)
        self.sl_multiplier = config.get("stop_loss_atr_multiplier", 2.0)
        log.info("Agente Coordinador Táctico inicializado.")

    def _create_base_plan(self, last_signal, pair: str, reason: str, analysis_data) -> dict:
        signal_type = "BUY" if last_signal['position'] > 0 else "SELL"
        entry_price = last_signal['close']
        
        if 'atr' not in last_signal or pd.isna(last_signal['atr']):
            log.error("No se puede calcular SL/TP: La columna 'atr' no está disponible o es NaN.")
            return None
            
        last_atr = last_signal['atr']
        
        if signal_type == "BUY":
            stop_loss = entry_price - (last_atr * self.sl_multiplier)
            take_profit = entry_price + (last_atr * self.sl_multiplier * self.risk_reward_ratio)
        else: # SELL
            stop_loss = entry_price + (last_atr * self.sl_multiplier)
            take_profit = entry_price - (last_atr * self.sl_multiplier * self.risk_reward_ratio)

        plan = {
            "pair": pair,
            "signal_type": signal_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reason": reason # Guardamos la razón de la señal
        }
        return plan

    def _format_plan(self, plan: dict) -> str:
        signal_emoji = "📈" if plan['signal_type'] == "BUY" else "📉"
        
        message = (
            f"🚨 *ALERTA DE TRADING QFC* 🚨\n\n"
            f"{signal_emoji} *{plan['signal_type']}* en *{plan['pair']}*\n\n"
            f"Justificación: *{plan['reason']}*\n\n" # Añadimos la justificación
            f"Entrada Sugerida: `{plan['entry_price']:.5f}`\n"
            f"🔴 Stop Loss: `{plan['stop_loss']:.5f}`\n"
            f"🟢 Take Profit: `{plan['take_profit']:.5f}`\n\n"
            f"Ratio Riesgo/Beneficio: `1:{self.risk_reward_ratio}`"
        )
        return message

    def format_telegram_plan(self, plan: dict) -> str:
        # Reutilizamos el formato base, ya que es compatible con Markdown de Telegram
        return self._format_plan(plan)

    def format_whatsapp_plan(self, plan: dict) -> str:
        # El formato de WhatsApp también es compatible con esta estructura
        return self._format_plan(plan)
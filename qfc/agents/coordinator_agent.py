from config.logger_config import log
import pandas as pd 

class CoordinatorAgent:
    def __init__(self, config: dict):
        self.risk_reward_ratio = config.get("risk_reward_ratio", 3)
        self.sl_multiplier = config.get("stop_loss_atr_multiplier", 1.5)
        self.trailing_stop_pct = config.get("trailing_stop_pct", 0.025)
        self.account_capital = config.get("account_capital", 10000)
        self.risk_per_trade_pct = config.get("risk_per_trade_pct", 0.01)
        log.info("Agente Coordinador Táctico (con Gestión de Riesgo Avanzada) inicializado.")

    def _calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        capital_to_risk = self.account_capital * self.risk_per_trade_pct
        price_risk_per_unit = abs(entry_price - stop_loss)
        if price_risk_per_unit == 0: return 0
        position_size = capital_to_risk / price_risk_per_unit
        return position_size

    def _create_base_plan(self, last_signal, pair: str, reason: str, analysis_data) -> dict:
        signal_type = "BUY" if last_signal['position'] > 0 else "SELL"
        entry_price = last_signal['close']
        
        if 'atr' not in last_signal or pd.isna(last_signal['atr']):
            log.error("No se puede calcular SL/TP: 'atr' no disponible.")
            return None
            
        last_atr = last_signal['atr']
        
        if signal_type == "BUY":
            stop_loss = entry_price - (last_atr * self.sl_multiplier)
            take_profit = entry_price + (last_atr * self.sl_multiplier * self.risk_reward_ratio)
        else: # SELL
            stop_loss = entry_price + (last_atr * self.sl_multiplier)
            take_profit = entry_price - (last_atr * self.sl_multiplier * self.risk_reward_ratio)

        position_size = self._calculate_position_size(entry_price, stop_loss)
        
        trailing_activation = entry_price + (entry_price - stop_loss) if signal_type == "BUY" else entry_price - (stop_loss - entry_price)

        plan = {
            "pair": pair, "signal_type": signal_type, "entry_price": entry_price,
            "stop_loss_initial": stop_loss, "take_profit_target": take_profit,
            "reason": reason, "position_size": f"{position_size:.4f} unidades",
            "trailing_stop_activation_price": trailing_activation,
            "trailing_stop_distance_pct": self.trailing_stop_pct,
        }
        return plan

    def _format_plan(self, plan: dict) -> str:
        signal_emoji = "📈" if plan['signal_type'] == "BUY" else "📉"
        
        message = (
            f"🚨 *ALERTA DE TRADING QFC* 🚨\n\n"
            f"{signal_emoji} *{plan['signal_type']}* en *{plan['pair']}*\n\n"
            f"🎯 *Justificación:* {plan['reason']}\n\n"
            f"--- PLAN DE TRADING ---\n"
            f"Entrada Sugerida: `{plan['entry_price']:.5f}`\n"
            f"Tamaño Sugerido: *{plan['position_size']}*\n\n"
            f"--- GESTIÓN DE RIESGO ---\n"
            f"🔴 Stop Loss Inicial: `{plan['stop_loss_initial']:.5f}`\n"
            f"🟢 Take Profit Objetivo: `{plan['take_profit_target']:.5f}`\n"
            f"🔒 Trailing Stop: Se activa en `{plan['trailing_stop_activation_price']:.5f}` con `{(plan['trailing_stop_distance_pct'] * 100):.1f}%` de distancia."
        )
        return message

    def format_telegram_plan(self, plan: dict) -> str: return self._format_plan(plan)
    def format_whatsapp_plan(self, plan: dict) -> str: return self._format_plan(plan)
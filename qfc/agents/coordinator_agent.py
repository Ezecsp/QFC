import pandas as pd
import pandas_ta as ta
from config.logger_config import log

class CoordinatorAgent:
    """
    Agente 4: Recibe una señal de trading y la convierte en un plan accionable,
    calculando Stop Loss y Take Profit.
    """
    def __init__(self, config: dict):
        self.rr_ratio = config.get("risk_reward_ratio", 2)
        self.sl_atr_multiplier = config.get("stop_loss_atr_multiplier", 1)
        # Usaremos el mismo periodo del ATR que usa el Agente 2 para consistencia
        self.atr_period = 14
        log.info("Agente Coordinador Táctico inicializado.")

    def _calculate_risk_parameters(self, data: pd.DataFrame, entry_price: float, trade_type: str) -> dict:
        """Calcula el SL y TP basados en el ATR."""
        
        # Calcula el ATR en el dataframe del análisis para ser preciso al timeframe
        data.ta.atr(length=self.atr_period, append=True)
        atr_col_name = f'ATRr_{self.atr_period}'
        last_atr = data[atr_col_name].iloc[-1]

        stop_loss_pips = self.sl_atr_multiplier * last_atr
        take_profit_pips = stop_loss_pips * self.rr_ratio

        if trade_type == "BUY":
            stop_loss = entry_price - stop_loss_pips
            take_profit = entry_price + take_profit_pips
        elif trade_type == "SELL":
            stop_loss = entry_price + stop_loss_pips
            take_profit = entry_price - take_profit_pips
        else:
            return {}
            
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }

    def _create_base_plan(self, last_signal: pd.Series, pair: str, strategy: str, analysis_data: pd.DataFrame) -> dict:
        """Crea un diccionario con los datos base del plan."""
        trade_type = "BUY" if last_signal['position'] == 1 else "SELL"
        entry_price = last_signal['close']
        
        risk_params = self._calculate_risk_parameters(analysis_data, entry_price, trade_type)
        if not risk_params:
            return {}

        return {
            "trade_type": trade_type,
            "pair": pair.replace('=X', ''),
            "strategy": strategy,
            "entry_price": entry_price,
            "stop_loss": risk_params['stop_loss'],
            "take_profit": risk_params['take_profit'],
            "rr_ratio": self.rr_ratio
        }

    def format_telegram_plan(self, plan_data: dict) -> str:
        """Formatea el plan para Telegram usando Markdown."""
        if not plan_data: return "Error"
        icon = "📈" if plan_data['trade_type'] == "BUY" else "📉"
        return (
            f"🚨 *ALERTA DE TRADING QFC* 🚨\n\n"
            f"{icon} *{plan_data['trade_type']}* en *{plan_data['pair']}*\n\n"
            f"*Estrategia:* `{plan_data['strategy']}`\n"
            f"*Entrada Sugerida:* `{plan_data['entry_price']:.5f}`\n\n"
            f"🔴 *Stop Loss:* `{plan_data['stop_loss']:.5f}`\n"
            f"🟢 *Take Profit:* `{plan_data['take_profit']:.5f}`\n\n"
            f"*Ratio Riesgo/Beneficio:* `1:{plan_data['rr_ratio']}`"
        )

    def format_whatsapp_plan(self, plan_data: dict) -> str:
        """Formatea el plan para WhatsApp usando su sintaxis."""
        if not plan_data: return "Error"
        return (
            f"--- ALERTA DE TRADING QFC ---\n\n"
            f"*{plan_data['trade_type']}* en *{plan_data['pair']}*\n\n"
            f"Estrategia: ```{plan_data['strategy']}```\n"
            f"Entrada Sugerida: ```{plan_data['entry_price']:.5f}```\n\n"
            f"Stop Loss: ```{plan_data['stop_loss']:.5f}```\n"
            f"Take Profit: ```{plan_data['take_profit']:.5f}```\n\n"
            f"Ratio Riesgo/Beneficio: 1:{plan_data['rr_ratio']}"
        )
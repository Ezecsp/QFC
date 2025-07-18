import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Claves de API ---
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# --- Parámetros de Trading ---
# Pares de divisas iniciales a monitorear
TRADING_PAIRS = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X']

MARKET_SELECTOR_CONFIG = {
    "volatility_indicator": "atr",
    "atr_period": 14  # Periodo estándar para el ATR
}

# --- Configuración del Agente Analista ---
# Parámetros para la estrategia de cruce de medias móviles (ejemplo inicial)
ANALYST_AGENT_CONFIG = {
    "strategy_name": "SMACrossover",
    "sma_short_window": 5,
    "sma_long_window": 15,
    "timeframe": "5m" # 15m, 1h, 4h, 1d
}

# --- Configuración del Agente 4: Coordinador Táctico ---
COORDINATOR_CONFIG = {
    "risk_reward_ratio": 1.5,  # Ratio Riesgo:Beneficio (1:1.5)
    "stop_loss_atr_multiplier": 2  # El Stop Loss será 2 veces el ATR
}

# --- Configuración de Telegram ---
# Carga las credenciales desde el archivo .env
TELEGRAM_CONFIG = {
    "token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "chat_id": os.getenv("TELEGRAM_CHAT_ID")
}

WHATSAPP_CONFIG = {
    "id_instance": os.getenv("GREEN_API_ID_INSTANCE"),
    "api_token": os.getenv("GREEN_API_API_TOKEN"),
    "target_number": os.getenv("WHATSAPP_TARGET_NUMBER")
}
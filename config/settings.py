import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Claves de API ---
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# --- Parámetros de Trading ---
# Pares de divisas iniciales a monitorear
TRADING_PAIRS = ['EURUSD=X', 'BTC-USD', 'AUDUSD=X']

MARKET_SELECTOR_CONFIG = {
    "volatility_indicator": "atr",
    "atr_period": 14  # Periodo estándar para el ATR
}

# --- Configuración del Agente Analista ---
# Parámetros para la estrategia de cruce de medias móviles (ejemplo inicial)
ANALYST_AGENT_CONFIG = {
    # Timeframe para la obtención de datos de análisis
    "timeframe": "1h", 
    
    # Lista de las estrategias que queremos ejecutar
    "strategies_to_run": [
        "sma_crossover", 
        "support_resistance",
        #"fibonacci_retracement",
        "ml_prediction",
    ],
    # Diccionario con las configuraciones para cada estrategia
    "strategy_configs": {
        "sma_crossover": {
            "sma_short_window": 20,
            "sma_long_window": 20
        },
        "support_resistance": {
            "lookback_period": 90, 
            "peak_distance": 5,
            "zone_creation_threshold_pct": 0.002,
        },
        #"fibonacci_retracement": {
        #    "lookback_period": 150 # Analizar las últimas 150 velas
        #},
        "ml_prediction": {
            "model_path": "qfc_ml_model.joblib"
        },
    }
}

# --- Configuración del Agente 4: Coordinador Táctico ---
COORDINATOR_CONFIG = {
    "risk_reward_ratio": 3,  # Ratio Riesgo:Beneficio (1:3)
    "stop_loss_atr_multiplier": 1  # El Stop Loss será 1 veces el ATR
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
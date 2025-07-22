import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Claves de API ---
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# --- Parámetros de Trading ---
TRADING_PAIRS = ['EURUSD=X', 'BTC-USD', 'AUDCAD=X']

MARKET_SELECTOR_CONFIG = {
    "volatility_indicator": "atr",
    "atr_period": 14
}

# --- Configuración del Agente Analista ---
ANALYST_AGENT_CONFIG = {
    "timeframe": "15m", 
    "strategies_to_run": [
        "support_resistance", 
        "order_block",
        "fvg",
        "ml_prediction",
    ],
    "strategy_configs": {
        "support_resistance": {
            "lookback_period": 90, 
            "peak_distance": 5,
            "zone_creation_threshold_pct": 0.002,
        },
        "order_block": {
            "lookback": 75,
            "breakout_candles": 3
        },
        "fvg": {
            "min_size_pct": 0.001
        },
        "ml_prediction": {
            "model_path_template": "qfc_model_{pair}.joblib"
        },
    }
}

# --- Configuración del Coordinador ---
COORDINATOR_CONFIG = {
    "risk_reward_ratio": 3,
    "stop_loss_atr_multiplier": 1.5
}

# --- Configuración de Puntuación de Señales ---
SCORING_CONFIG = {
    "signal_threshold": 2.5,
    "weights": {
        "support_resistance": 1.0,
        "order_block": 1.5,
        "fvg": 1.0,
        "ml_confirmation_bonus": 2.0,
        "counter_trend_penalty": 0.3 # Multiplicador para penalizar señales contra-tendencia
    }
}

# --- Configuración de Visualización ---
SHOW_PLOTS = False # Poner en False para desactivar los gráficos

# --- Configuraciones de Notificaciones ---
TELEGRAM_CONFIG = {
    "token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "chat_id": os.getenv("TELEGRAM_CHAT_ID")
}

WHATSAPP_CONFIG = {
    "id_instance": os.getenv("GREEN_API_ID_INSTANCE"),
    "api_token": os.getenv("GREEN_API_API_TOKEN"),
    "target_number": os.getenv("WHATSAPP_TARGET_NUMBER")
}
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
        "market_structure_shift",
        "combined_fibo",
        "bos_choch_ob",
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
        "market_structure_shift": { 
            "lookback": 20,
            "mss_lookback": 10
        },
        "ml_prediction": {
            "model_path_template": "qfc_model_{pair}.joblib"
        },
        "combined_fibo": { # Configuración ajustada
            "cambio_estructura_lookback": 50,
            "cambio_estructura_fibo_threshold_pct": 0.001, # 0.1%
            "cambio_estructura_momentum_confirmation": True,

            "tendencia_basica_period": 14,
            "tendencia_basica_fibo_ratio": 0.618,
            "tendencia_basica_touch_threshold_pct": 0.001, # 0.1%
            "tendencia_basica_momentum_confirmation": True,

            "paridad_volume_threshold": None, # Se calculará dinámicamente
            "paridad_volume_percentile": 0.90,
            "paridad_return_lookback": 15,
            "paridad_return_threshold_pct": 0.001, # 0.1%
            "paridad_return_momentum_confirmation": True,

            "require_multiple_confirmations": True, # Requiere al menos 2 señales
            "min_confirmations_for_signal": 2,
        },
        "bos_choch_ob": { # <-- CONFIGURACIÓN PARA LA NUEVA ESTRATEGIA
            "swing_detection_period": 5,
            "swing_method": "simple", # Opciones: 'simple'
            "use_close_only_for_break": True,
            "level_touch_threshold_pct": 0.001, # 0.1%
            "ob_definition": "level", # Opciones: 'level'
            "ob_return_lookback": 20,
            "ob_return_momentum_confirmation": True,
            "bos_choch_momentum_confirmation": True,
            "signal_type": "combined", # Opciones: 'combined', 'ob_return' (por ahora)
        },
    }
}

# --- Configuración del Coordinador (con Gestión de Riesgo) ---
COORDINATOR_CONFIG = {
    "risk_reward_ratio": 3,
    "stop_loss_atr_multiplier": 1.5,
    "account_capital": 10000, # Capital de la cuenta en USD
    "risk_per_trade_pct": 0.01, # Riesgo del 1% por operación
    "trailing_stop_pct": 0.025, # Trailing Stop del 2.5%
}

# --- Configuración de Puntuación de Señales ---
SCORING_CONFIG = {
    "signal_threshold": 1.5,
    "weights": {
        "support_resistance": 1.0,
        "order_block": 1.5,
        "fvg": 1.0,
        "market_structure_shift": 1.5,
        "ml_confirmation_bonus": 1.0,
        "counter_trend_penalty": 0.5, # Multiplicador para penalizar señales contra-tendencia
        "bos_choch_ob": 1.5,
        "combined_fibo": 1.5
    }
}

# --- Configuración de Visualización ---
SHOW_PLOTS = True # Poner en False para desactivar los gráficos

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
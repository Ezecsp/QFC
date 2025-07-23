import pandas as pd
import pandas_ta as ta
import joblib
from config.logger_config import log
from qfc.strategies.base_strategy import BaseStrategy

class MLPredictionStrategy(BaseStrategy):
    def __init__(self, config: dict):
        super().__init__(config)
        self.model_path_template = config.get("model_path_template", "qfc_model_{pair}.joblib")
        self.models = {}
        self.prediction_map = {0: -1, 1: 0, 2: 1} # Venta, Neutral, Compra
        log.info("Estrategia 'MLPrediction' (con Features Evolucionadas) inicializada.")

    def _get_model(self, pair: str):
        if pair not in self.models:
            model_filename = self.model_path_template.format(pair=pair)
            try:
                self.models[pair] = joblib.load(model_filename)
                log.info(f"Modelo especialista cargado desde: {model_filename}")
            except FileNotFoundError:
                log.error(f"Archivo de modelo no encontrado para {pair}: {model_filename}.")
                self.models[pair] = None
        return self.models[pair]
        
    def _create_features(self, df):
        # --- ESTE BLOQUE DEBE SER IDÉNTICO AL DE train_model.py ---
        log.info("Creando características avanzadas para predicción...")
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, append=True)
        df.ta.atr(length=14, append=True)
        
        df['body_size'] = abs(df['close'] - df['open'])
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['hour_of_day'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        
        df.dropna(inplace=True)
        return df

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis de ML para {pair}...")
        model = self._get_model(pair)
        if model is None:
            data['ml_position'] = 0
            return data
            
        df_features = self._create_features(data.copy())
        
        # Alinear columnas con las usadas en el entrenamiento
        try:
            df_features_ordered = df_features[model.feature_names_in_]
        except (AttributeError, KeyError):
             log.error("Las características del DataFrame no coinciden con las del modelo. Re-entrena el modelo.")
             data['ml_position'] = 0
             return data
        
        predictions_raw = model.predict(df_features_ordered)
        prediction_signals = pd.Series(predictions_raw, index=df_features_ordered.index).map(self.prediction_map)
        
        data['ml_position'] = prediction_signals
        data['ml_position'] = data['ml_position'].fillna(0)
        
        log.info(f"Análisis de ML completado. Última predicción para {pair}: {data['ml_position'].iloc[-1]}")
        return data
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
        self.prediction_map = {0: -1, 1: 0, 2: 1}
        log.info("Estrategia 'MLPrediction' (Multi-Modelo con Memoria) inicializada.")

    def _get_model(self, pair: str):
        if pair not in self.models:
            model_filename = self.model_path_template.format(pair=pair)
            try:
                log.info(f"Cargando modelo especialista desde: {model_filename}")
                self.models[pair] = joblib.load(model_filename)
            except FileNotFoundError:
                log.error(f"No se encontró el archivo del modelo para {pair}: {model_filename}.")
                self.models[pair] = None
        return self.models[pair]
        
    def _create_features(self, df):
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, append=True)
        df.ta.atr(length=14, append=True)
        df.dropna(inplace=True) # Importante dropear NaNs después de crear indicadores
        return df

    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame:
        log.info(f"Ejecutando análisis de MLPrediction para {pair}...")
        df = data.copy()
        
        model = self._get_model(pair)
        if model is None:
            return df
        # 1. Creamos características para TODO el DataFrame
        df_features = self._create_features(df.copy())
        
        # 2. Reordenamos las columnas para que coincidan con el entrenamiento
        df_features_ordered = df_features[model.feature_names_in_]
        
        # 3. Hacemos predicciones para TODA la historia, no solo la última vela
        predictions_raw = model.predict(df_features_ordered)
        
        # 4. Mapeamos las predicciones a nuestras señales [-1, 0, 1]
        prediction_signals = pd.Series(predictions_raw, index=df_features_ordered.index).map(self.prediction_map)
        
        # 5. Unimos las predicciones al DataFrame original
        df['ml_position'] = prediction_signals
        
        # Rellenamos los NaNs que puedan haber surgido al principio
        df['ml_position'].fillna(0, inplace=True)
        
        log.info(f"Análisis de MLPrediction completado. Última predicción para {pair}: {df['ml_position'].iloc[-1]}")
        
        return df
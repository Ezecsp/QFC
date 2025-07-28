import pandas as pd
import pandas_ta as ta
import joblib
from config.logger_config import log
from qfc.utils.data_fetcher import DataFetcher
import xgboost as xgb # Asumimos XGBoost según requirements.txt
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import argparse # Para pasar el par como argumento

# Importamos la función de creación de características desde la estrategia
# Asegúrate de que esta función sea EXACTAMENTE la misma que en ml_prediction_strategy.py
def create_features_for_training(df):
    """Crea las características para el modelo ML. DEBE ser idéntica a _create_features en MLPredictionStrategy."""
    log.info("Creando características avanzadas para ENTRENAMIENTO...")
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.bbands(length=20, append=True)
    df.ta.atr(length=14, append=True)
    df['body_size'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
    df['hour_of_day'] = df.index.hour
    df['day_of_week'] = df.index.dayofweek

    # --- Etiquetado de datos (LABELS) ---
    # Ejemplo simple: Clasificar según el movimiento del precio en las próximas N velas
    look_ahead = 3 # Miramos 3 velas adelante
    df['future_return'] = df['close'].shift(-look_ahead) / df['close'] - 1
    # Definir etiquetas: 0 = Bajista, 1 = Neutral, 2 = Alcista
    # Ajusta estos umbrales según sea necesario
    down_threshold = -0.001 # -0.1%
    up_threshold = 0.001    # +0.1%
    df['label'] = 1 # Inicializar como Neutral
    df.loc[df['future_return'] < down_threshold, 'label'] = 0 # Bajista
    df.loc[df['future_return'] > up_threshold, 'label'] = 2   # Alcista

    df.dropna(inplace=True) # Eliminar filas con NaN (especialmente por el shift)
    log.info(f"Características y etiquetas creadas. Distribución de etiquetas:\n{df['label'].value_counts()}")
    return df

def train_model_for_pair(pair: str, output_path_template: str = "qfc_model_{pair}.joblib"):
    """Entrena y guarda un modelo para un par específico."""
    log.info(f"Iniciando entrenamiento para el par: {pair}")

    # 1. Obtener datos
    data_fetcher = DataFetcher(pair=pair, interval='1h') # Puedes usar otro intervalo si lo prefieres
    df_raw = data_fetcher.fetch_data(period="730d") # Datos de 2 años, por ejemplo
    if df_raw.empty:
        log.error(f"No se pudieron obtener datos para {pair}.")
        return

    # 2. Crear características y etiquetas
    df_features_labeled = create_features_for_training(df_raw.copy())

    # 3. Preparar datos para entrenamiento
    # Separar características (X) y etiquetas (y)
    # Excluir columnas que no son características ni la etiqueta objetivo
    feature_columns = [col for col in df_features_labeled.columns
                       if col not in ['open', 'high', 'low', 'close', 'volume', 'label', 'future_return']]
    X = df_features_labeled[feature_columns]
    y = df_features_labeled['label']

    if X.empty or y.empty:
        log.error(f"No hay datos suficientes para entrenar el modelo para {pair} después de procesar.")
        return

    log.info(f"Forma de los datos de entrenamiento: X={X.shape}, y={y.shape}")

    # Dividir en entrenamiento y prueba
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 4. Entrenar modelo (ejemplo con XGBoost)
    # Puedes ajustar los parámetros
    model = xgb.XGBClassifier(
        objective='multi:softprob', # Para clasificación multiclase con probabilidades
        num_class=3,               # 0, 1, 2
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42
    )

    log.info("Iniciando entrenamiento del modelo...")
    model.fit(X_train, y_train)
    log.info("Entrenamiento completado.")

    # 5. Evaluar el modelo
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    log.info(f"Precisión en el conjunto de prueba para {pair}: {accuracy:.4f}")
    log.info(f"Reporte de clasificación para {pair}:\n{classification_report(y_test, y_pred)}")

    # 6. Guardar el modelo
    model_filename = output_path_template.format(pair=pair)
    try:
        joblib.dump(model, model_filename)
        log.info(f"Modelo guardado exitosamente en: {model_filename}")
    except Exception as e:
        log.error(f"Error al guardar el modelo para {pair}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrenar modelo QFC para un par específico.")
    parser.add_argument("--pair", type=str, required=True, help="El par de trading (e.g., BTC-USD, EURUSD=X)")
    args = parser.parse_args()

    train_model_for_pair(args.pair)

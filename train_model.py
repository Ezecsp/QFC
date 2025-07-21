import pandas as pd
import pandas_ta as ta
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import argparse  # Importamos la librería para argumentos
from qfc.utils.data_fetcher import DataFetcher
from config.logger_config import log

# Los parámetros ahora son constantes que podemos ajustar
PROFIT_TARGET_PCT = 0.005
STOP_LOSS_PCT = 0.003
FUTURE_CANDLES = 10
TIMEFRAME = '1h'

# ... (Las funciones create_features y create_labels no cambian) ...
def create_features(df):
    log.info("Creando características con pandas-ta...")
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.bbands(length=20, append=True)
    df.ta.atr(length=14, append=True)
    df.dropna(inplace=True)
    return df

def create_labels(df):
    log.info("Creando etiquetas de trading...")
    df['future_high'] = df['high'].rolling(window=FUTURE_CANDLES).max().shift(-FUTURE_CANDLES)
    df['future_low'] = df['low'].rolling(window=FUTURE_CANDLES).min().shift(-FUTURE_CANDLES)
    profit_target_price = df['close'] * (1 + PROFIT_TARGET_PCT)
    stop_loss_price = df['close'] * (1 - STOP_LOSS_PCT)
    df['label'] = 0
    df.loc[df['future_high'] >= profit_target_price, 'label'] = 1
    df.loc[df['future_low'] <= stop_loss_price, 'label'] = -1
    df.loc[(df['future_high'] >= profit_target_price) & (df['future_low'] <= stop_loss_price), 'label'] = -1
    return df.dropna()


def train_specialist_model(pair_to_train: str):
    log.info(f"--- Iniciando entrenamiento del modelo especialista para {pair_to_train} ---")
    
    data_fetcher = DataFetcher(pair=pair_to_train, interval=TIMEFRAME)
    df = data_fetcher.fetch_data(period="730d", interval_override=TIMEFRAME)

    if df.empty:
        log.error(f"No se pudieron obtener datos para {pair_to_train}. Abortando entrenamiento.")
        return

    df = create_features(df)
    df = create_labels(df)

    feature_cols = [col for col in df.columns if col.startswith(('RSI', 'MACD', 'BBL', 'BBM', 'BBU', 'BBB', 'BBP', 'ATRr'))]
    X = df[feature_cols]
    y = df['label'].map({-1: 0, 0: 1, 1: 2})

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    log.info(f"Entrenando modelo XGBoost para {pair_to_train} con {len(X_train)} muestras...")
    model = xgb.XGBClassifier(objective='multi:softprob', num_class=3, eval_metric='mlogloss', use_label_encoder=False)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    log.info(f"Precisión del modelo de {pair_to_train} en datos de prueba: {accuracy * 100:.2f}%")

    # ¡CAMBIO CLAVE! Guardamos el modelo con el nombre del par.
    model_filename = f'qfc_model_{pair_to_train}.joblib'
    joblib.dump(model, model_filename)
    log.info(f"¡Modelo especialista para {pair_to_train} guardado como '{model_filename}'!")

if __name__ == "__main__":
    # Creamos un parser para leer argumentos de la terminal
    parser = argparse.ArgumentParser(description="Entrenador de modelos de trading especialistas.")
    parser.add_argument("--pair", type=str, required=True, help="El par de trading para el cual entrenar el modelo (ej. 'EURUSD=X').")
    args = parser.parse_args()
    
    train_specialist_model(args.pair)
# backtest.py

import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy
from qfc.utils.data_fetcher import DataFetcher
from config.logger_config import log
from config import settings

# --- Import ALL strategies used in the analysis ---
# Existing strategies
from qfc.strategies.support_resistance_strategy import SupportResistanceStrategy
from qfc.strategies.order_block_strategy import OrderBlockStrategy
from qfc.strategies.fvg_strategy import FvgStrategy
from qfc.strategies.market_structure_shift_strategy import MarketStructureShiftStrategy
# Newly added strategies
from qfc.strategies.combined_fibo_strategy import CombinedFiboStrategy
from qfc.strategies.bos_choch_ob_strategy import BosChochObStrategy
# ML Strategy import is optional for backtesting, as it requires trained models.
# If you want to include it, uncomment the line below and ensure models exist.
# from qfc.strategies.ml_prediction_strategy import MLPredictionStrategy 

# --- STEP 1: DATA PREPARATION FUNCTION ---
# All heavy analysis logic is moved here. It runs ONCE per pair.
def prepare_data_for_backtest(df: pd.DataFrame, pair: str) -> pd.DataFrame:
    """
    Takes a DataFrame with market data and adds all necessary signal columns
    required for the backtest.
    """
    log.info(f"({pair}) Pre-calculating all strategy signals...")
    df.columns = [col.lower() for col in df.columns]

    # --- Instantiate Strategies ---
    sr_analyzer = SupportResistanceStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['support_resistance'])
    ob_analyzer = OrderBlockStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['order_block'])
    fvg_analyzer = FvgStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['fvg'])
    mss_analyzer = MarketStructureShiftStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['market_structure_shift'])
    
    # --- Instantiate NEW Strategies ---
    combined_fibo_analyzer = CombinedFiboStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['combined_fibo'])
    bos_choch_ob_analyzer = BosChochObStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['bos_choch_ob'])
    
    # Optional: Include ML if models are available and you want to test it
    # Note: This will fail if models are not found, similar to live trading.
    # ml_analyzer = MLPredictionStrategy(settings.ANALYST_AGENT_CONFIG['strategy_configs']['ml_prediction'])

    # --- Apply Strategy Analysis ---
    df = sr_analyzer.analyze(df, pair)
    df = ob_analyzer.analyze(df, pair)
    df = fvg_analyzer.analyze(df, pair)
    df = mss_analyzer.analyze(df, pair)
    
    # --- Apply NEW Strategy Analysis ---
    df = combined_fibo_analyzer.analyze(df, pair)
    df = bos_choch_ob_analyzer.analyze(df, pair)
    
    # Optional: Apply ML Analysis
    # df = ml_analyzer.analyze(df, pair) 

    # --- Add Trend Filter (4h EMA) ---
    log.info(f"({pair}) Calculating and adding 4h EMA trend filter...")
    trend_fetcher = DataFetcher(pair=pair, interval='4h')
    df_trend = trend_fetcher.fetch_data(period="730d")
    if not df_trend.empty:
        df_trend['ema_trend'] = ta.ema(df_trend['close'], length=50)
        # Reindex to align with main df's index, forward-fill for recent data points
        df['is_uptrend'] = (df_trend['close'] > df_trend['ema_trend']).reindex(df.index, method='ffill') 
        # Handle potential NaNs at the start if 4h data starts later
        df['is_uptrend'].fillna(method='bfill', inplace=True) 
        # Default to True if still NaN (fallback)
        df['is_uptrend'].fillna(True, inplace=True) 
    else:
        log.warning(f"({pair}) Could not fetch 4h trend data. Assuming uptrend.")
        df['is_uptrend'] = True 

    log.info(f"({pair}) Pre-calculation of data completed.")
    return df

# --- STEP 2: THE BACKTESTING STRATEGY CLASS ---
# This class is now very simple, only handling scoring and execution using pre-calculated columns.
class QFCSystemBacktest(Strategy):
    pair = "UNKNOWN"
    
    # Parameters to optimize (multiplied by 10 for integer handling in backtesting.py)
    # Existing Weights
    weight_sr = 10
    weight_ob = 15
    weight_fvg = 10
    weight_mss = 25
    # New Weights
    weight_combined_fibo = 15
    weight_bos_choch_ob = 15
    # ML Weight (if included)
    # weight_ml = 20 
    
    signal_threshold = 30 # Multiplied by 10 -> Actual threshold is 3.0
    penalty_factor = 3    # Multiplied by 10 -> Actual factor is 0.3

    def init(self):
        # Reference pre-calculated columns. Backtesting lib uses capitalized names.
        # Existing Signals
        self.sr_signal = self.data.Sr_position
        self.ob_signal = self.data.Ob_signal
        self.fvg_signal = self.data.Fvg_signal
        self.mss_signal = self.data.Mss_signal
        # New Signals
        self.combined_fibo_signal = self.data.Combined_fibo_signal
        self.bos_choch_ob_signal = self.data.Bos_choch_ob_signal
        # ML Signal (if included)
        # self.ml_position = self.data.Ml_position 

        self.is_uptrend = self.data.Is_uptrend
        # ATR for stop loss / take profit
        self.atr = self.I(ta.atr, pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(self.data.Close), length=14)

    def next(self):
        # Prevent opening new positions if already in one
        if self.position:
            return

        # --- Calculate Scores ---
        buy_score, sell_score = 0, 0
        
        # Existing Strategy Scoring
        if self.sr_signal[-1] == 1: buy_score += self.weight_sr / 10
        if self.sr_signal[-1] == -1: sell_score += self.weight_sr / 10
        if self.ob_signal[-1] == 1: buy_score += self.weight_ob / 10
        if self.ob_signal[-1] == -1: sell_score += self.weight_ob / 10
        if self.fvg_signal[-1] == 1: buy_score += self.weight_fvg / 10
        if self.fvg_signal[-1] == -1: sell_score += self.weight_fvg / 10
        if self.mss_signal[-1] == 1: buy_score += self.weight_mss / 10
        if self.mss_signal[-1] == -1: sell_score += self.weight_mss / 10
        
        # --- New Strategy Scoring ---
        # Combined Fibo Strategy (Buy signal only in this implementation)
        if self.combined_fibo_signal[-1] == 1: buy_score += self.weight_combined_fibo / 10
        # Bos/Choch/Ob Strategy (Can generate Buy or Sell signals)
        if self.bos_choch_ob_signal[-1] == 1: buy_score += self.weight_bos_choch_ob / 10
        if self.bos_choch_ob_signal[-1] == -1: sell_score += self.weight_bos_choch_ob / 10

        # --- ML Scoring (if included) ---
        # bonus = 0
        # if self.ml_position[-1] == 1: bonus = self.weight_ml / 10 # Bonus for buy confirmation
        # if self.ml_position[-1] == -1: bonus = -self.weight_ml / 10 # Penalty/adjustment for sell confirmation
        # buy_score += max(0, bonus) # Only add positive bonus to buy
        # sell_score += max(0, -bonus) # Only add positive bonus (from negative bonus value) to sell

        # --- Trend Filter Penalty ---
        # Reduce score for signals going against the 4H trend
        if self.is_uptrend[-1]: # Uptrend
            sell_score *= (self.penalty_factor / 10) # Penalize sell signals
        else: # Downtrend
            buy_score *= (self.penalty_factor / 10)  # Penalize buy signals

        # --- Decision Logic ---
        threshold = self.signal_threshold / 10
        # Buy Condition
        if buy_score >= threshold and buy_score > sell_score:
            # Example SL/TP using ATR
            sl = self.data.Close[-1] - self.atr[-1] * 1.5
            tp = self.data.Close[-1] + self.atr[-1] * 3 # Assuming 1:2 RR, adjust as needed
            self.buy(sl=sl, tp=tp)
        # Sell Condition
        elif sell_score >= threshold and sell_score > buy_score:
            # Example SL/TP using ATR
            sl = self.data.Close[-1] + self.atr[-1] * 1.5
            tp = self.data.Close[-1] - self.atr[-1] * 3 # Assuming 1:2 RR, adjust as needed
            self.sell(sl=sl, tp=tp)

# --- STEP 3: MAIN BACKTESTING ORCHESTRATION SCRIPT ---
if __name__ == "__main__":
    log.info("="*60)
    log.info("INITIATING MULTI-PAIR BACKTESTING & OPTIMIZATION")
    log.info("="*60)

    PAIRS_TO_BACKTEST = settings.TRADING_PAIRS # Use pairs from settings
    all_stats = {}

    for pair in PAIRS_TO_BACKTEST:
        log.info(f"--- PROCESSING PAIR: {pair} ---")
        
        # 1. Fetch Raw Data
        data_fetcher = DataFetcher(pair=pair, interval='1h') # Using 1h as in your main.py example
        df_raw = data_fetcher.fetch_data(period="730d") # Fetch 2Y of data
        if df_raw.empty or len(df_raw) < 200: # Basic check for sufficient data
            log.warning(f"Insufficient data for {pair}. Skipping to next pair.")
            continue

        # 2. Prepare Data with Signals (THE HEAVY LIFTING)
        df_ready = prepare_data_for_backtest(df_raw, pair)

        # 3. Backtesting Library Requirement: Capitalize column names
        df_ready.columns = [col.capitalize() for col in df_ready.columns]

        # 4. Configure and Run Backtest/Optimization
        QFCSystemBacktest.pair = pair # Pass pair name to the strategy class
        bt = Backtest(df_ready, QFCSystemBacktest, cash=100_000, commission=.001) # Example settings

        log.info(f"Running OPTIMIZATION for {pair}... (This may take a while)")
        try:
            # --- OPTIMIZATION ---
            # Define the parameter ranges for optimization.
            # Note: Optimizing many parameters simultaneously can be very slow.
            # Consider optimizing in stages or focusing on key parameters.
            stats = bt.optimize(
                # --- Existing Strategy Weights ---
                weight_sr=range(5, 21, 5),      # 0.5, 1.0, 1.5, 2.0
                weight_ob=range(10, 31, 5),     # 1.0, 1.5, 2.0, 2.5, 3.0
                weight_fvg=range(5, 21, 5),     # 0.5, 1.0, 1.5, 2.0
                weight_mss=range(15, 31, 5),    # 1.5, 2.0, 2.5, 3.0
                # --- NEW Strategy Weights ---
                weight_combined_fibo=range(10, 26, 5), # 1.0, 1.5, 2.0, 2.5
                weight_bos_choch_ob=range(10, 26, 5),  # 1.0, 1.5, 2.0, 2.5
                # --- ML Weight (if included) ---
                # weight_ml=range(15, 31, 5),     # 1.5, 2.0, 2.5, 3.0
                # --- Scoring Parameters ---
                signal_threshold=range(20, 41, 5),  # 2.0, 2.5, 3.0, 3.5, 4.0
                penalty_factor=range(1, 11, 3),     # 0.1, 0.4, 0.7, 1.0
                maximize='Sharpe Ratio' # Or 'Return [%]', 'Win Rate [%]', etc.
            )
            all_stats[pair] = stats
            log.info(f"--- OPTIMAL RESULTS FOR {pair} ---")
            print(stats)
            log.info(f"--- OPTIMAL PARAMETERS FOR {pair} (Remember to divide by 10) ---")
            print(stats._strategy) # This shows the best parameters found

            # --- Optional: Plot the results of the best run ---
            # bt.plot()

        except Exception as e:
            log.error(f"An error occurred during optimization for {pair}: {e}")

    # --- FINAL SUMMARY ---
    log.info("="*60)
    log.info("FINAL MULTI-PAIR OPTIMIZATION SUMMARY")
    log.info("="*60)
    if not all_stats:
        log.warning("No optimizations were completed successfully.")
    else:
        for pair, stats in all_stats.items():
            log.info(f"Results for {pair}:")
            log.info(f"  Sharpe Ratio: {stats.get('Sharpe Ratio', 'N/A'):.2f}")
            log.info(f"  Return [%]: {stats.get('Return [%]', 'N/A'):.2f}")
            log.info(f"  Win Rate [%]: {stats.get('Win Rate [%]', 'N/A'):.2f}")
            log.info(f"  Max Drawdown [%]: {stats.get('Max Drawdown [%]', 'N/A'):.2f}")
            log.info(f"  Optimal Parameters: {stats._strategy}")
            log.info("-" * 40)
    log.info("BACKTESTING PROCESS COMPLETED.")

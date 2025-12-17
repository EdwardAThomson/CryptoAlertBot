import pandas as pd
import os
import sys
import numpy as np
import json
import glob
from datetime import datetime

from src.reporters.markdown_reporter import SIGNAL_REGIMES # Use the same source of truth

def generate_signals_from_8_state(symbol: str) -> pd.DataFrame:
    """
    Loads pre-computed 8-state signals and maps them to BUY/SELL/HOLD,
    incorporating a 100-day SMA trend filter.

    Args:
        symbol: The asset symbol (e.g., 'BTCUSDT').

    Returns:
        A DataFrame with a 'signal' column and date index.
    """
    # --- Load Signal Data ---
    signals_path = f"data/analysis/signals_{symbol}.csv"
    if not os.path.exists(signals_path):
        raise FileNotFoundError(f"Signal file not found for {symbol} at {signals_path}")
    df = pd.read_csv(signals_path, parse_dates=['date'], index_col='date')
    
    if 'price' not in df.columns:
        raise ValueError("Signal data must contain a 'price' column for the trend filter.")

    # --- Add Trend Filter ---
    df['sma_100'] = df['price'].rolling(window=100).mean()
    # Only drop rows where the SMA is NaN, preserving other columns
    df.dropna(subset=['sma_100'], inplace=True)
    
    # --- Define Strategy Rules ---
    entry_signals = ['Initiation (#1)', 'Accumulation (#5)']
    exit_signals = ['Distribution (#4)', 'Breakdown (#6)', 'Bull Trap (#8)']

    df['signal_action'] = 'HOLD'
    position = 'OUT'  # Start with no position

    for i in range(len(df)):
        current_signal = df['signal'].iloc[i]
        price_above_trend = df['price'].iloc[i] > df['sma_100'].iloc[i]

        # Entry logic: signal must be valid AND price must be above long-term trend
        if position == 'OUT' and current_signal in entry_signals and price_above_trend:
            df.iat[i, df.columns.get_loc('signal_action')] = 'BUY'
            position = 'IN'
        # Exit logic: independent of the trend filter
        elif position == 'IN' and current_signal in exit_signals:
            df.iat[i, df.columns.get_loc('signal_action')] = 'SELL'
            position = 'OUT'

    return df[['signal_action']].rename(columns={'signal_action': 'signal'})


def generate_signals_from_momentum(momentum_data: pd.DataFrame) -> pd.DataFrame:
    """
    Generates BUY/SELL/HOLD signals based on a simple momentum strategy.
    
    Args:
        momentum_data: DataFrame from the run_analyzer.
    
    Returns:
        A DataFrame with a 'signal' column containing 'BUY', 'SELL', 'HOLD'.
    """
    print("Generating signals from Momentum Model...")
    
    # This is a placeholder for a momentum strategy.
    # For example, we could use the 'predicted_direction' from our run analysis.
    signals = pd.DataFrame(index=momentum_data.index)
    signals['signal'] = 'HOLD' # Default to HOLD
    
    # A simple example:
    # signals.loc[momentum_data['predicted_direction'] == 'up', 'signal'] = 'BUY'
    # signals.loc[momentum_data['predicted_direction'] == 'down', 'signal'] = 'SELL'
    
    print("Momentum strategy not yet implemented.")
    
    return signals 

def generate_signals_from_momentum(symbol: str, price_data: pd.DataFrame) -> pd.DataFrame:
    """
    Generates BUY/SELL/HOLD signals based on a simple moving average (SMA) crossover strategy.

    Args:
        symbol: The asset symbol (e.g., 'BTCUSDT').
        price_data: DataFrame with historical price data. Must contain a 'price' column.

    Returns:
        A DataFrame with a 'signal' column and date index.
    """
    # --- Define Strategy Parameters ---
    short_window = 20
    long_window = 50

    df = price_data.copy()

    # --- Calculate SMAs ---
    df['sma_short'] = df['price'].rolling(window=short_window).mean()
    df['sma_long'] = df['price'].rolling(window=long_window).mean()
    df.dropna(inplace=True)

    # --- Generate Crossover Signals ---
    # The signal is generated on the day AFTER the crossover occurs.
    df['crossover'] = np.where(df['sma_short'] > df['sma_long'], 1.0, 0.0)
    df['signal_action'] = df['crossover'].diff()
    
    # Map the diff output to BUY/SELL signals
    # 1.0 means short SMA crossed above long SMA -> BUY
    # -1.0 means short SMA crossed below long SMA -> SELL
    signal_map = {1.0: 'BUY', -1.0: 'SELL'}
    df['signal'] = df['signal_action'].map(signal_map).fillna('HOLD')

    return df[['signal']] 

def generate_signals_from_run_analysis(symbol: str, price_data: pd.DataFrame) -> pd.DataFrame:
    """
    Generates BUY/SELL/HOLD signals based on the daily run analysis predictions.
    It finds all available prediction files and bases the signals on that data.
    """
    predictions = []
    
    # Find all prediction files for the symbol
    prediction_files = glob.glob(f"data/predictions/run_analysis_{symbol}_*.json")
    
    for file_path in prediction_files:
        try:
            # Extract date from filename
            date_str = os.path.basename(file_path).split('_')[-1].replace('.json', '')
            trade_date = datetime.strptime(date_str, '%Y%m%d')

            with open(file_path, 'r') as f:
                data = json.load(f)
            
            p_continue = data.get('short_term', {}).get('continuation_probability', 0.5)
            current_direction = data.get('short_term', {}).get('current_direction', 'N/A')
            
            direction = None
            if current_direction != 'N/A':
                predicted_direction = current_direction if p_continue >= 0.5 else ("up" if current_direction == "down" else "down")
                direction = predicted_direction.upper()
            
            if direction:
                predictions.append({'date': trade_date, 'predicted_direction': direction})

        except (json.JSONDecodeError, KeyError, ValueError):
            print(f"Could not parse file: {file_path}")
            continue

    if not predictions:
        print("Warning: No valid prediction files found for run-analysis strategy.")
        return pd.DataFrame(columns=['signal'])

    df = pd.DataFrame(predictions).set_index('date').sort_index()

    # --- Generate Trading Signals from Predictions ---
    df['position'] = np.where(df['predicted_direction'] == 'UP', 1, -1)
    df['signal_action'] = df['position'].diff()

    signal_map = {
        2.0: 'BUY',  # From SELL (-1) to BUY (1)
        -2.0: 'SELL' # From BUY (1) to SELL (-1)
    }
    df['signal'] = df['signal_action'].map(signal_map).fillna('HOLD')

    return df[['signal']] 
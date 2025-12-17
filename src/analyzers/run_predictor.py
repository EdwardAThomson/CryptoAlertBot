import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
import sys
from typing import Dict

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.analyzers.run_analyzer import RunAnalyzer

def _get_prediction_from_analyzer(analyzer: RunAnalyzer, df: pd.DataFrame) -> Dict:
    """Uses a loaded analyzer instance to get a prediction from a dataframe."""
    if not analyzer:
        return {'error': 'Analyzer not loaded'}
    
    # Explicitly create a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Calculate returns and signs for the provided dataframe
    df['ret'] = df['price'].pct_change()
    df['sign'] = np.where(df['ret'] >= 0, 1, -1)
    df = df.dropna(subset=['sign']).copy()
    
    if df.empty:
        return {'error': 'Not enough data for prediction'}

    # Use the analyzer's methods to get the current streak info
    current_streak = analyzer._get_current_streak(df)

    return {
        'current_streak_length': current_streak['length'],
        'current_direction': 'up' if current_streak['direction'] == 1 else 'down',
        'continuation_probability': current_streak['p_continue'],
        'expected_return': current_streak['exp_ret'],
    }

def generate_daily_prediction_file(symbol: str):
    """
    Loads pre-built distribution models to generate the daily prediction file.
    This is the "light" part of the analysis and should be run daily.
    """
    # 1. Load the two distribution models
    analyzer_100d = RunAnalyzer.load_distribution_stats(symbol, '100d')
    analyzer_all = RunAnalyzer.load_distribution_stats(symbol, 'all_time')

    if not analyzer_100d or not analyzer_all:
        print(f"    - Skipping prediction for {symbol}: Distribution models not found. Run the run_analyzer.py script first.")
        # Optionally, we could run the builder here automatically. For now, we just skip.
        # from src.analyzers.run_analyzer import update_all_distributions # Example
        # update_all_distributions()
        return

    # 2. Get the latest historical price data
    from src.collectors.historical_price_collector import get_historical_price_data_filepath
    filepath = get_historical_price_data_filepath(symbol)
    if not os.path.exists(filepath):
        print(f"    - Skipping prediction for {symbol}: Historical data not found.")
        return
        
    df_full = pd.read_csv(filepath).sort_values('date')
    
    # Handle case where price column is 'close' instead of 'price'
    if 'price' not in df_full.columns and 'close' in df_full.columns:
        df_full = df_full.rename(columns={'close': 'price'})

    df_100d = df_full.tail(100).copy()
    df_full_copy = df_full.copy()

    # 3. Get predictions from each model
    results_short = _get_prediction_from_analyzer(analyzer_100d, df_100d)
    results_all = _get_prediction_from_analyzer(analyzer_all, df_full_copy)

    # 4. Create and save the combined JSON file for the reporter
    combined_results = {
        'symbol': symbol,
        'last_updated': datetime.now().strftime('%Y%m%d'),
        'short_term': results_short,
        'all_time': results_all
    }
    
    try:
        os.makedirs('data/predictions', exist_ok=True)
        report_date_str = datetime.now().strftime('%Y%m%d')
        save_path = os.path.join('data/predictions', f"run_analysis_{symbol}_{report_date_str}.json")
        with open(save_path, 'w') as f:
            json.dump(combined_results, f, indent=2)
        # Be less verbose on success to keep the main log clean
        # print(f"    - Successfully created daily run prediction for {symbol}.")
    except Exception as e:
        print(f"    - FAILED to create daily run prediction for {symbol}. Error: {e}")

if __name__ == '__main__':
    # For direct testing of the predictor
    symbols_to_test = ['BTCUSDT', 'ETHUSDT']
    print("========================================================")
    print("== Generating Daily Predictions (Test)...           ==")
    print("========================================================")
    for symbol in symbols_to_test:
        generate_daily_prediction_file(symbol)
    print("\n========================================================")
    print("== Daily Prediction Generation Complete.            ==")
    print("========================================================") 
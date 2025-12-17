import pandas as pd
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import os
import json
from datetime import datetime
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(project_root)

class RunAnalyzer:
    """
    Analyzes price runs (streaks of up/down days) to identify patterns and make probabilistic predictions.
    Uses historical price data to calculate hazard rates and survival probabilities for streaks.
    """
    
    def __init__(self, lookback_days: int = 100):
        """
        Initialize the RunAnalyzer.
        
        Args:
            lookback_days: Number of days to use for analysis (default: 100)
        """
        self.lookback_days = lookback_days
        self.hazard: Dict[int, float] = {}  # P(streak ends | length = k)
        self.survive: Dict[int, float] = {}  # P(streak continues | length = k)
        self.mu_pos: float = 0  # Mean return on up days
        self.mu_neg: float = 0  # Mean return on down days
        self.runs: List[Tuple[int, int]] = []  # List of (direction, length) tuples
        
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Analyze price data and return streak statistics.
        
        Args:
            df: DataFrame with 'price' or 'close' column (daily closes)
            
        Returns:
            Dictionary containing streak analysis results
        """
        # Use 'close' if 'price' is not present
        if 'price' not in df.columns and 'close' in df.columns:
            df = df.rename(columns={'close': 'price'})
        
        # Ensure we have enough data
        if len(df) < 2 or 'price' not in df.columns:
            return {
                'error': 'Insufficient data for analysis',
                'current_streak_length': 0,
                'current_direction': 'unknown',
                'continuation_probability': 0.5,
                'expected_return': 0.0
            }
            
        # 1. Calculate returns and signs
        df['ret'] = df['price'].pct_change()
        df['sign'] = np.where(df['ret'] >= 0, 1, -1)
        df = df.dropna(subset=['sign']).copy()
        
        # 2. Calculate runs
        self.runs = self._calculate_runs(df['sign'])
        
        # 3. Calculate hazard/survival rates
        self._calculate_hazard_survival(self.runs)
        
        # 4. Calculate mean returns
        self.mu_pos = df.loc[df['sign'] == 1, 'ret'].mean()
        self.mu_neg = df.loc[df['sign'] == -1, 'ret'].mean()
        
        # 5. Get current streak info
        current_streak = self._get_current_streak(df)
        
        # 6. Calculate additional statistics
        streak_stats = self._calculate_streak_statistics()
        
        return {
            'current_streak_length': current_streak['length'],
            'current_direction': 'up' if current_streak['direction'] == 1 else 'down',
            'continuation_probability': current_streak['p_continue'],
            'expected_return': current_streak['exp_ret'],
            'hazard_rates': self.hazard,
            'survival_rates': self.survive,
            'streak_statistics': streak_stats,
            'mean_up_return': self.mu_pos,
            'mean_down_return': self.mu_neg
        }
    
    def _calculate_runs(self, sign_series: pd.Series) -> List[Tuple[int, int]]:
        """
        Calculate run lengths and directions.
        
        Args:
            sign_series: Series of 1 (up) and -1 (down) values
            
        Returns:
            List of (direction, length) tuples
        """
        runs = []
        length = 1
        
        for i in range(1, len(sign_series)):
            if sign_series.iloc[i] == sign_series.iloc[i-1]:
                length += 1
            else:
                runs.append((sign_series.iloc[i-1], length))
                length = 1
        runs.append((sign_series.iloc[-1], length))
        return runs
    
    def _calculate_hazard_survival(self, runs: List[Tuple[int, int]]) -> None:
        """
        Calculate hazard and survival rates with Laplace smoothing.
        
        Args:
            runs: List of (direction, length) tuples
        """
        cont = defaultdict(int)
        end = defaultdict(int)
        
        for _, L in runs:
            for k in range(1, L):
                cont[k] += 1
            end[L] += 1
            
        max_k = max(max(cont, default=1), max(end, default=1))
        
        for k in range(1, max_k + 1):
            c = cont.get(k, 0) + 1  # Laplace smoothing
            e = end.get(k, 0) + 1
            self.hazard[k] = e / (c + e)
            self.survive[k] = 1 - self.hazard[k]
    
    def _get_current_streak(self, df: pd.DataFrame) -> Dict:
        """
        Get current streak information and predictions.
        
        Args:
            df: DataFrame with 'sign' column
            
        Returns:
            Dictionary with current streak information
        """
        k = 1
        current_col = df['sign'].iloc[-1]
        
        for i in range(len(df)-2, -1, -1):
            if df['sign'].iloc[i] == current_col:
                k += 1
            else:
                break
                
        p_continue = self.survive.get(k, 0.5)
        p_flip = 1 - p_continue
        
        # Adjust expected return based on current streak direction
        if current_col == 1:  # Up streak
            mu_same = self.mu_pos
            mu_flip = self.mu_neg
        else:  # Down streak
            mu_same = self.mu_neg
            mu_flip = self.mu_pos
        
        exp_ret = p_continue * mu_same + p_flip * mu_flip
        
        return {
            'length': k,
            'direction': current_col,
            'p_continue': p_continue,
            'exp_ret': exp_ret
        }
    
    def _calculate_streak_statistics(self) -> Dict:
        """
        Calculate additional statistics about streaks.
        
        Returns:
            Dictionary with streak statistics
        """
        if not self.runs:
            return {}
            
        up_streaks = [length for direction, length in self.runs if direction == 1]
        down_streaks = [length for direction, length in self.runs if direction == -1]
        
        return {
            'total_streaks': len(self.runs),
            'up_streaks': {
                'count': len(up_streaks),
                'mean_length': np.mean(up_streaks) if up_streaks else 0,
                'max_length': max(up_streaks) if up_streaks else 0,
                'min_length': min(up_streaks) if up_streaks else 0
            },
            'down_streaks': {
                'count': len(down_streaks),
                'mean_length': np.mean(down_streaks) if down_streaks else 0,
                'max_length': max(down_streaks) if down_streaks else 0,
                'min_length': min(down_streaks) if down_streaks else 0
            }
        }

    def save_distribution_stats(self, symbol: str, label: str) -> None:
        """
        Save the distribution statistics to a file with a label.
        These statistics change slowly and don't need daily updates.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            label: A label for the analysis timeframe (e.g., '100d', 'all_time')
        """
        stats = {
            'symbol': symbol,
            'label': label,
            'last_updated': datetime.now().strftime('%Y%m%d'),
            'hazard_rates': self.hazard,
            'survival_rates': self.survive,
            'streak_statistics': self._calculate_streak_statistics(),
            'mean_up_return': self.mu_pos,
            'mean_down_return': self.mu_neg
        }
        
        # Create directory if it doesn't exist
        os.makedirs('data/analysis', exist_ok=True)
        
        # Save to file
        filepath = f'data/analysis/run_distribution_{symbol}_{label}.json'
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
            
    @classmethod
    def load_distribution_stats(cls, symbol: str, label: str) -> Optional['RunAnalyzer']:
        """
        Load distribution statistics from a labeled file.
        
        Args:
            symbol: Trading pair symbol
            label: The label for the analysis timeframe (e.g., '100d', 'all_time')
            
        Returns:
            RunAnalyzer instance with loaded statistics, or None if file doesn't exist
        """
        filepath = f'data/analysis/run_distribution_{symbol}_{label}.json'
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r') as f:
            stats = json.load(f)
            
        analyzer = cls()
        # JSON saves dictionary keys as strings, so we must convert them back to integers
        analyzer.hazard = {int(k): v for k, v in stats['hazard_rates'].items()}
        analyzer.survive = {int(k): v for k, v in stats['survival_rates'].items()}
        analyzer.mu_pos = stats['mean_up_return']
        analyzer.mu_neg = stats['mean_down_return']
        return analyzer

def save_daily_prediction(symbol: str, prediction: Dict) -> None:
    """Saves the daily prediction to a file."""
    os.makedirs('data/analysis', exist_ok=True)
    filename = f"data/analysis/run_prediction_{symbol}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(prediction, f, indent=4)
    except IOError as e:
        print(f"Error saving daily prediction for {symbol}: {e}")

def generate_and_save_daily_prediction(symbol: str):
    """
    Loads saved distribution stats, gets the latest price data, calculates the
    current streak and prediction, and saves it.
    """
    # 1. Load the saved RunAnalyzer instance
    analyzer = RunAnalyzer.load_distribution_stats(symbol, '100d')
    if not analyzer:
        # If no saved stats, run a full analysis to generate them
        print(f"No existing run analysis stats for {symbol}. Running full analysis first.")
        analyze_historical_price_data(symbol)
        analyzer = RunAnalyzer.load_distribution_stats(symbol, '100d')
        if not analyzer:
            print(f"Could not generate run analysis stats for {symbol}. Aborting prediction.")
            return

    # 2. Get the latest price data (we only need signs)
    price_data_path = f"data/daily/price_{symbol}.csv"
    if not os.path.exists(price_data_path):
        print(f"Price data not found for {symbol} at {price_data_path}")
        return

    try:
        df = pd.read_csv(price_data_path, usecols=['date', 'price'], parse_dates=['date'])
        if 'price' not in df.columns and 'close' in df.columns:
            df = df.rename(columns={'close': 'price'})
        
        df = df.sort_values('date').tail(analyzer.lookback_days * 2) # Get more than enough data
        
        df['ret'] = df['price'].pct_change()
        df['sign'] = np.where(df['ret'] >= 0, 1, -1)
        df = df.dropna(subset=['sign']).copy()

        # 3. Get the current streak and prediction
        current_streak_info = analyzer._get_current_streak(df)

        # 4. Save the prediction
        save_daily_prediction(symbol, current_streak_info)
        # print(f"Successfully generated and saved daily run prediction for {symbol}.")

    except Exception as e:
        print(f"Error generating daily prediction for {symbol}: {e}")

def analyze_historical_price_data(symbol: str, lookback_days: int = 100) -> Dict:
    """
    Analyze historical price data for a given symbol.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        lookback_days: Number of days to use in the analysis. If < 0, uses all data.
        
    Returns:
        Dictionary with analysis results, or an error dictionary.
    """
    from src.collectors.historical_price_collector import get_historical_price_data_filepath
    filepath = get_historical_price_data_filepath(symbol)
    
    if not os.path.exists(filepath):
        return {'error': f'No historical price data found for {symbol}'}
        
    try:
        df = pd.read_csv(filepath, parse_dates=['date'])
        
        if 'price' not in df.columns and 'close' in df.columns:
            df = df.rename(columns={'close': 'price'})

        if lookback_days > 0:
            df = df.sort_values('date').tail(lookback_days).copy()
        else:
            df = df.sort_values('date').copy()

        analyzer = RunAnalyzer(lookback_days=lookback_days)
        results = analyzer.analyze(df)
        
        results['symbol'] = symbol
        results['analysis_date'] = df['date'].max().strftime('%Y-%m-%d')
        results['data_points'] = len(df)
        
        return results
        
    except Exception as e:
        return {'error': f'Error analyzing {symbol}: {str(e)}'}

def update_all_distributions():
    """
    This function can be called from other scripts to update the distribution
    models for all assets listed in the config file.
    """
    # Load assets from config file to avoid hardcoding
    try:
        config_path = os.path.join(project_root, 'data', 'config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        symbols = config.get("assets", [])
        if not symbols:
            print("Warning: No assets found in config.json. Exiting.")
            return # Use return instead of sys.exit for a library function
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing config file at {config_path}: {e}")
        return

    print("========================================================")
    print("== Updating Run Analysis Distribution Models...       ==")
    print("========================================================")

    for symbol in symbols:
        print(f"\n--- Processing: {symbol} ---")
        
        try:
            from src.collectors.historical_price_collector import get_historical_price_data_filepath
            filepath = get_historical_price_data_filepath(symbol)
            if not os.path.exists(filepath):
                print(f"  - Skipping {symbol}: Historical data not found.")
                continue

            # --- 100-Day Distribution ---
            print("  - Analyzing 100-day distribution...")
            df_100d = pd.read_csv(filepath).sort_values('date').tail(100)
            analyzer_100d = RunAnalyzer(lookback_days=100)
            analyzer_100d.analyze(df_100d)
            analyzer_100d.save_distribution_stats(symbol, '100d')

            # --- All-Time Distribution ---
            print("  - Analyzing all-time distribution...")
            df_all = pd.read_csv(filepath).sort_values('date')
            analyzer_all = RunAnalyzer(lookback_days=len(df_all))
            analyzer_all.analyze(df_all)
            analyzer_all.save_distribution_stats(symbol, 'all_time')
            
            print(f"  - Successfully saved distributions for {symbol}")

        except Exception as e:
            print(f"  - FAILED to process distributions for {symbol}. Error: {e}")
    
    print("\n========================================================")
    print("== Distribution Model Update Complete.              ==")
    print("========================================================")

def update_daily_run_analysis(symbol: str):
    """
    Runs short-term and all-time run analysis and saves the combined
    prediction file that the reporter uses. This should be run daily.
    """
    # Determine the total number of available days for all-time analysis
    try:
        from src.collectors.historical_price_collector import get_historical_price_data_filepath
        filepath = get_historical_price_data_filepath(symbol)
        all_time_days = -1 # Use all data by default
        if os.path.exists(filepath):
            df_full = pd.read_csv(filepath)
            all_time_days = len(df_full)
    except Exception as e:
        print(f"Could not determine all-time days for {symbol}, using default. Error: {e}")
        all_time_days = -1

    # Run both short-term and all-time analysis
    results_short = analyze_historical_price_data(symbol, lookback_days=100)
    results_all = analyze_historical_price_data(symbol, lookback_days=all_time_days)
    
    # --- Create and Save the Labeled Distribution Files ---
    analyzer_short = RunAnalyzer(lookback_days=100)
    analyzer_short.analyze(pd.read_csv(get_historical_price_data_filepath(symbol)).sort_values('date').tail(100))
    analyzer_short.save_distribution_stats(symbol, '100d')

    analyzer_all = RunAnalyzer(lookback_days=all_time_days)
    analyzer_all.analyze(pd.read_csv(get_historical_price_data_filepath(symbol)).sort_values('date'))
    analyzer_all.save_distribution_stats(symbol, 'all_time')

    # --- Create and Save the Combined JSON file ---
    combined_results = {
        'symbol': symbol,
        'last_updated': datetime.now().strftime('%Y-%m-%d'),
        'short_term': results_short,
        'all_time': results_all
    }
    
    try:
        os.makedirs('data/predictions', exist_ok=True)
        report_date_str = datetime.now().strftime('%Y%m%d')
        save_path = os.path.join('data/predictions', f"run_analysis_{symbol}_{report_date_str}.json")
        with open(save_path, 'w') as f:
            json.dump(combined_results, f, indent=2)
        print(f"    - Successfully updated daily run analysis for {symbol}.")
    except Exception as e:
        print(f"    - FAILED to update daily run analysis for {symbol}. Error: {e}")

if __name__ == '__main__':
    """
    This script can be run directly to generate the underlying distribution
    models for all assets. This is the "heavy" part of the analysis and
    should be run periodically (e.g., weekly).
    """
    update_all_distributions()

    print("========================================================")
    print("== Distribution Model Update Complete.              ==")
    print("========================================================") 
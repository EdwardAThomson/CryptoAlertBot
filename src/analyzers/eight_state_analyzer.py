import pandas as pd
import numpy as np
import os
from src.analyzers.technical_analyzer import get_technical_analysis_output_path

# --- Configuration ---
class SignalConfig:
    """
    Configuration parameters for signal generation.
    """
    PRICE_SMA_SHORT = 3
    OI_SMA = 3
    CVD_SMA = 3
    
# --- New Regime Filter Config ---
USE_REGIME_FILTER = True
# Graduated compression thresholds based on signal strength
STRONG_SIGNAL_THRESHOLD = 20    # Hardest to suppress (Bullish/Bearish Trending)
MEDIUM_SIGNAL_THRESHOLD = 30    # Medium threshold (Contrarian signals)
WEAK_SIGNAL_THRESHOLD = 45      # Easier to suppress (Disagreement/Exhaustion)
DEFAULT_THRESHOLD = 40          # For noise and undefined states

def get_signal_output_path(symbol: str) -> str:
    """Generates the standardized filepath for a given asset's signal file."""
    output_dir = "data/analysis"
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"signals_{symbol}.csv")

def _load_individual_data(path: str) -> pd.DataFrame | None:
    """Loads a single CSV, handling potential missing 'date' column."""
    try:
        # Load without setting index first to inspect columns
        df = pd.read_csv(path)
        
        # Determine the date column
        date_col = 'date'
        if date_col not in df.columns:
            if len(df.columns) > 0:
                # If 'date' column is missing, assume it's the first one
                date_col = df.columns[0]
            else:
                # Handle empty file case
                raise ValueError("CSV file is empty or has no columns.")
        
        # Now parse the determined date column
        df[date_col] = pd.to_datetime(df[date_col])
        df.rename(columns={date_col: 'date'}, inplace=True)
        return df

    except FileNotFoundError:
        print(f"    - Error loading data: File not found at {path}.")
        return None
    except Exception as e:
        print(f"    - An unexpected error occurred while loading {path}: {e}")
        return None

def _load_data(price_path: str, oi_path: str, cvd_path: str, tech_path: str) -> pd.DataFrame | None:
    """Loads and merges price, OI, CVD, and technical analysis data."""
    df_price = _load_individual_data(price_path)
    if df_price is None: return None
    
    df_oi = _load_individual_data(oi_path)
    if df_oi is None: return None
    
    df_cvd = _load_individual_data(cvd_path)
    if df_cvd is None: return None

    df_tech = _load_individual_data(tech_path)
    if df_tech is None: return None

    try:
        # First, merge the core data sources with an inner join
        df = pd.merge(df_price, df_oi, on='date', how='inner')
        df = pd.merge(df, df_cvd, on='date', how='inner')

        # Identify only the indicator columns from the tech analysis dataframe to avoid name collisions
        price_cols = ['open', 'high', 'low', 'close', 'volume']
        indicator_cols = [col for col in df_tech.columns if col not in price_cols]
        
        # Now, left join only the indicators
        df = pd.merge(df, df_tech[indicator_cols], on='date', how='left')
        
        # Forward-fill any NaNs that may have resulted from the left join
        fill_cols = [col for col in indicator_cols if col != 'date']
        df[fill_cols] = df[fill_cols].ffill()

        # Drop any remaining NaNs after ffill (e.g., at the start of the series)
        df.dropna(inplace=True)

        # Sort by date to ensure correct rolling calculations
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"    - An unexpected error occurred during data merging: {e}")
        return None

def _calculate_z_score_state(close_series: pd.Series, sma20_series: pd.Series, window: int = 20, threshold: float = 0.5) -> pd.Series:
    """
    Determines the price state based on a z-score relative to the 20-day SMA.
    States are 'UP', 'DOWN', or 'NEUTRAL'.
    """
    std_dev_20 = close_series.rolling(window=window).std()
    z_score = (close_series - sma20_series) / std_dev_20
    
    conditions = [
        z_score > threshold,
        z_score < -threshold
    ]
    choices = ['UP', 'DOWN']
    return pd.Series(np.select(conditions, choices, default='NEUTRAL'), index=close_series.index)

def generate_signals(price_path: str, oi_path: str, cvd_path: str, symbol: str, column_map: dict):
    """
    Generates trading signals based on an 8-state model derived from price,
    open interest, CVD, and technical analysis data.
    
    The state is determined by the combination of directions (UP/DOWN) of these three metrics.
    A compression regime filter overrides the 8-state model.
    """
    # print(f"  - Generating 8-state signals for {symbol}...")
    
    # Define paths
    tech_analysis_path = os.path.join("data", "analysis", f"technical_analysis_{symbol}.csv")
    output_path = get_signal_output_path(symbol)
    
    # Map friendly names to actual column names
    price_col = column_map.get("price", "close")
    oi_col = column_map.get("oi", "sumOpenInterestValue")
    cvd_col = column_map.get("cvd", "CVD")

    # Load and merge data
    df = _load_data(price_path, oi_path, cvd_path, tech_analysis_path)
    if df is None:
        print(f"    - Signal generation for {symbol} aborted due to data loading failure.")
        return

    # --- State Calculation ---
    # 1. Price State (using Z-Score)
    # Ensure the 'bb_middle' column (SMA20) exists from the technical analysis data
    if 'bb_middle' not in df.columns:
        print(f"    - Error: 'bb_middle' (SMA20) not found in technical analysis data for {symbol}. Aborting.")
        return
    df['price_state'] = _calculate_z_score_state(df[price_col], df['bb_middle'])

    # 2. Open Interest State (using 3-day SMA)
    oi_sma3 = df[oi_col].rolling(window=3).mean()
    df['oi_state'] = np.where(df[oi_col] > oi_sma3, 'UP', 'DOWN')

    # 3. CVD State (using 3-day SMA)
    cvd_sma3 = df[cvd_col].rolling(window=3).mean()
    df['cvd_state'] = np.where(df[cvd_col] > cvd_sma3, 'UP', 'DOWN')

    # --- State Combination ---
    state_map = {
        ('UP', 'UP', 'UP'): 'Bullish Trending',
        ('UP', 'UP', 'DOWN'): 'Bullish Exhaustion',
        ('UP', 'DOWN', 'UP'): 'Contrarian Bullish',
        ('UP', 'DOWN', 'DOWN'): 'Bullish Disagreement',
        ('DOWN', 'UP', 'UP'): 'Bearish Disagreement',
        ('DOWN', 'UP', 'DOWN'): 'Contrarian Bearish',
        ('DOWN', 'DOWN', 'UP'): 'Bearish Exhaustion',
        ('DOWN', 'DOWN', 'DOWN'): 'Bearish Trending',
        # --- Handle NEUTRAL price state from Z-score ---
        ('NEUTRAL', 'UP', 'UP'): 'Noise (Bullish Bias)',
        ('NEUTRAL', 'UP', 'DOWN'): 'Noise (Bearish Bias)',
        ('NEUTRAL', 'DOWN', 'UP'): 'Noise (Bullish Bias)',
        ('NEUTRAL', 'DOWN', 'DOWN'): 'Noise (Bearish Bias)',
    }
    
    df['state'] = df[['price_state', 'oi_state', 'cvd_state']].apply(
        lambda x: state_map.get(tuple(x), 'Undefined'), axis=1
    )

    # --- Graduated Regime Filter Override ---
    # Apply graduated compression filter based on signal strength
    if 'realized_vol_10d_percentile' in df.columns:
        # Define signal strength categories
        strongest_signals = df['state'].isin(['Bullish Trending', 'Bearish Trending'])
        medium_signals = df['state'].isin(['Contrarian Bullish', 'Contrarian Bearish'])
        weak_signals = df['state'].str.contains('Disagreement|Exhaustion')
        noise_signals = df['state'].str.contains('Noise')
        
        # Apply graduated thresholds - stronger signals need lower volatility to be suppressed
        compression_threshold = np.where(strongest_signals, STRONG_SIGNAL_THRESHOLD,
                                       np.where(medium_signals, MEDIUM_SIGNAL_THRESHOLD,
                                              np.where(weak_signals, WEAK_SIGNAL_THRESHOLD, 
                                                     DEFAULT_THRESHOLD)))
        
        # Create compression mask using graduated thresholds
        is_compression = df['realized_vol_10d_percentile'] < compression_threshold
        
        # Store the original state for debugging/analysis
        df['original_state'] = df['state'].copy()
        
        # Override the state for compression periods
        df.loc[is_compression, 'state'] = 'Compression'
        
        # Enhanced logging - show what signals were suppressed
        if not df.empty:
            latest_original = df['original_state'].iloc[-1]
            latest_final = df['state'].iloc[-1]
            latest_vol_percentile = df['realized_vol_10d_percentile'].iloc[-1]
            
            if latest_final == 'Compression':
                print(f"    - Compression applied to {symbol}: '{latest_original}' -> 'Compression' (vol: {latest_vol_percentile:.1f}%)")
            elif latest_original in ['Bullish Trending', 'Bearish Trending']:
                print(f"    - Strong signal preserved for {symbol}: '{latest_original}' (vol: {latest_vol_percentile:.1f}%)")
    else:
        print(f"    - Warning: 'realized_vol_10d_percentile' not found. Cannot apply compression filter.")

    # --- Save Results ---
    # Prepare the output dataframe, renaming columns for consistency with the reporter
    # Include original_state and volatility for analysis if they exist
    base_cols = ['date', 'close', 'state', 'price_state', 'oi_state', 'cvd_state', oi_col, cvd_col]
    if 'original_state' in df.columns:
        base_cols.insert(3, 'original_state')  # Insert after 'state'
    if 'realized_vol_10d_percentile' in df.columns:
        base_cols.append('realized_vol_10d_percentile')  # Add volatility data
    
    df_out = df[base_cols].copy()
    df_out.rename(columns={oi_col: 'oi', cvd_col: 'cvd'}, inplace=True)
    
    # Update output columns list
    output_cols = ['date', 'close', 'state']
    if 'original_state' in df_out.columns:
        output_cols.append('original_state')
    output_cols.extend(['price_state', 'oi_state', 'cvd_state', 'oi', 'cvd'])
    if 'realized_vol_10d_percentile' in df_out.columns:
        output_cols.append('realized_vol_10d_percentile')

    try:
        df_out[output_cols].to_csv(output_path, index=False)
        print(f"    - Signals successfully generated and saved to {output_path}")
    except Exception as e:
        print(f"    - Error saving signals for {symbol}: {e}")

if __name__ == '__main__':
    # This block is for direct testing of this script.
    print("Running eight_state_analyzer.py directly for testing...")
    
    test_symbol = "BTCUSDT"
    
    test_column_map = {
        "price": "close",
        "oi": "sumOpenInterestValue",
        "cvd": "CVD"
    }

    base_path = os.path.join("data", "daily")
    price_path = os.path.join(base_path, f"historical_price_{test_symbol}.csv")
    oi_path = os.path.join(base_path, f"open_interest_{test_symbol}_binance.csv")
    cvd_path = os.path.join(base_path, f"cvd_{test_symbol}_binance.csv")
    
    if all(os.path.exists(p) for p in [price_path, oi_path, cvd_path]):
        generate_signals(price_path, oi_path, cvd_path, test_symbol, test_column_map)
    else:
        print("\nOne or more data files are missing. Cannot run test.")
        if not os.path.exists(price_path): print(f"  - Missing: {price_path}")
        if not os.path.exists(oi_path): print(f"  - Missing: {oi_path}")
        if not os.path.exists(cvd_path): print(f"  - Missing: {cvd_path}") 
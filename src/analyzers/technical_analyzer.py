import pandas as pd
import numpy as np
import os
from src.collectors import historical_price_collector

# --- Configuration ---
class TechAnalysisConfig:
    """
    Configuration parameters for the technical analysis module.
    """
    # SMA Periods
    SMA_PERIODS = [50, 200]

    # Bollinger Bands Parameters
    BBANDS_PERIOD = 20
    BBANDS_STD_DEV = 2

    # Short-term Compression Metrics
    BBANDS_PERIOD_SHORT = 10
    VOL_REALIZED_PERIOD = 10
    COMPRESSION_PERCENTILE_WINDOW = 100

    # MACD Parameters
    MACD_FAST_PERIOD = 12
    MACD_SLOW_PERIOD = 26
    MACD_SIGNAL_PERIOD = 9

    # RSI Parameters
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30

    # BB on MACD Parameters
    BB_ON_MACD_LENGTH = 20
    BB_ON_MACD_STD_DEV = 2

    # UT Bot Alerts Parameters
    UT_BOT_KEY_VALUE = 1.0
    UT_BOT_ATR_PERIOD = 10

def get_technical_analysis_output_path(symbol: str, timeframe: str = 'daily') -> str:
    """Generates the standardized filepath for a given asset's technical analysis."""
    output_dir = "data/analysis"
    os.makedirs(output_dir, exist_ok=True)
    if timeframe == 'weekly':
        return os.path.join(output_dir, f"technical_analysis_{symbol}_weekly.csv")
    return os.path.join(output_dir, f"technical_analysis_{symbol}.csv")

# --- Calculation Functions ---

def _calculate_sma(data: pd.Series, window: int) -> pd.Series:
    """Calculates the Simple Moving Average (SMA)."""
    return data.rolling(window=window).mean()

def _calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """Calculates the Exponential Moving Average (EMA)."""
    return data.ewm(span=window, adjust=False).mean()

def _calculate_bollinger_bands(data: pd.Series, window: int, num_std_dev: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculates Bollinger Bands."""
    sma = _calculate_sma(data, window)
    std_dev = data.rolling(window=window).std()
    upper_band = sma + (std_dev * num_std_dev)
    lower_band = sma - (std_dev * num_std_dev)
    return upper_band, sma, lower_band

def _calculate_macd(data: pd.Series, fast_period: int, slow_period: int, signal_period: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculates the Moving Average Convergence Divergence (MACD)."""
    ema_fast = _calculate_ema(data, window=fast_period)
    ema_slow = _calculate_ema(data, window=slow_period)
    macd_line = ema_fast - ema_slow
    signal_line = _calculate_ema(macd_line, window=signal_period)
    macd_histogram = macd_line - signal_line
    return macd_line, signal_line, macd_histogram

def _calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate the Relative Strength Index (RSI) for a series of prices.
    Note: This expects a price series, not a returns series.
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _calculate_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Heikin Ashi candles from a standard OHLC DataFrame.
    """
    ha_df = df.copy()

    # Heikin Ashi Close
    ha_df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4

    # Heikin Ashi Open
    ha_df['ha_open'] = np.nan
    # The first HA Open is the average of the regular open and close
    ha_df.loc[0, 'ha_open'] = (df.loc[0, 'open'] + df.loc[0, 'close']) / 2
    for i in range(1, len(df)):
        ha_df.loc[i, 'ha_open'] = (ha_df.loc[i-1, 'ha_open'] + ha_df.loc[i-1, 'ha_close']) / 2

    # Heikin Ashi High and Low
    ha_df['ha_high'] = ha_df[['high', 'ha_open', 'ha_close']].max(axis=1)
    ha_df['ha_low'] = ha_df[['low', 'ha_open', 'ha_close']].min(axis=1)

    return ha_df[['ha_open', 'ha_high', 'ha_low', 'ha_close']]

def _calculate_bb_on_macd(macd_line: pd.Series, length: int, std_dev: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculates Bollinger Bands applied to MACD line."""
    upper, basis, lower = _calculate_bollinger_bands(macd_line, length, std_dev)
    return upper, basis, lower

def _calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10) -> pd.Series:
    """Calculate Average True Range (ATR)"""
    # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR is the moving average of True Range
    atr = true_range.rolling(window=period).mean()
    return atr

def _calculate_ut_bot_signals(df: pd.DataFrame, key_value: float = 1.0, atr_period: int = 10, use_heikin_ashi: bool = False) -> dict:
    """Calculate UT Bot Alerts signals"""
    
    # Use Heikin-Ashi or regular candles
    if use_heikin_ashi:
        # Assume Heikin-Ashi columns are already calculated and available in df
        if 'ha_close' in df.columns:
            src = df['ha_close']
        else:
            # Fallback to regular close if HA not available
            src = df['close']
    else:
        src = df['close']
    
    # Calculate ATR
    atr = _calculate_atr(df['high'], df['low'], df['close'], atr_period)
    loss = key_value * atr
    
    # Initialize trailing stop
    trail = pd.Series(index=df.index, dtype=float)
    trail.iloc[0] = src.iloc[0]  # Start with first price
    
    # Calculate trailing stop
    for i in range(1, len(df)):
        prev_trail = trail.iloc[i-1]
        current_src = src.iloc[i]
        current_loss = loss.iloc[i]
        
        if current_src > prev_trail:
            # Uptrend: trail moves up
            trail.iloc[i] = max(prev_trail, current_src - current_loss)
        else:
            # Downtrend: trail moves down
            trail.iloc[i] = min(prev_trail, current_src + current_loss)
    
    # Calculate signals
    long_signal = (src > trail) & (src.shift(1) <= trail.shift(1))
    short_signal = (src < trail) & (src.shift(1) >= trail.shift(1))
    
    # Trend direction
    direction = pd.Series(0, index=df.index)
    direction[src > trail] = 1   # Long
    direction[src < trail] = -1  # Short
    
    return {
        'trail': trail,
        'atr': atr,
        'long_signal': long_signal,
        'short_signal': short_signal,
        'direction': direction
    }

# --- Main Generator ---

def generate_technical_analysis(symbol: str, timeframe: str = 'daily'):
    """
    Generates a file with various technical analysis indicators for a given symbol.

    Args:
        symbol (str): The asset symbol (e.g., 'BTCUSDT').
        timeframe (str): The timeframe to analyze ('daily' or 'weekly').
    """
    print(f"--- Generating Technical Analysis for {symbol} ({timeframe}) ---")
    cfg = TechAnalysisConfig()

    # Define file paths
    if timeframe == 'weekly':
        price_path = historical_price_collector.get_weekly_historical_price_data_filepath(symbol)
    else:
        price_path = historical_price_collector.get_historical_price_data_filepath(symbol)
        
    output_path = get_technical_analysis_output_path(symbol, timeframe)

    # Read data
    try:
        df = pd.read_csv(price_path, parse_dates=['date'])
        if 'close' not in df.columns:
            print(f"  - Skipping {symbol}: 'close' column not found in {price_path}")
            return
    except FileNotFoundError:
        print(f"  - Skipping {symbol}: Price data not found at {price_path}")
        return
    except Exception as e:
        print(f"  - Error reading {price_path} for {symbol}: {e}")
        return
    
    # Ensure data is sorted by date
    df = df.sort_values('date').reset_index(drop=True)
    
    # --- Calculate Heikin Ashi Candles ---
    heikin_ashi_df = _calculate_heikin_ashi(df)
    df = pd.concat([df, heikin_ashi_df], axis=1)

    price_series = df['close']

    # --- Calculate Indicators ---
    # SMAs
    for period in cfg.SMA_PERIODS:
        df[f'sma_{period}'] = _calculate_sma(price_series, period)

    # Bollinger Bands
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = _calculate_bollinger_bands(
        price_series, cfg.BBANDS_PERIOD, cfg.BBANDS_STD_DEV
    )

    # Bollinger Band Width and Percentile
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['bb_width_percentile'] = df['bb_width'].rolling(window=cfg.BBANDS_PERIOD).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100)

    # --- Add Compression Metrics for Regime Analysis ---
    # 1. Bollinger Band Width (10-day) Percentile
    bb_upper_10d, _, bb_lower_10d = _calculate_bollinger_bands(price_series, cfg.BBANDS_PERIOD_SHORT, cfg.BBANDS_STD_DEV)
    bb_width_10d = (bb_upper_10d - bb_lower_10d) / price_series # Use price as middle band for simplicity
    df['bb_width_10d_percentile'] = bb_width_10d.rolling(
        window=cfg.COMPRESSION_PERCENTILE_WINDOW
    ).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100)

    # 2. Realized Volatility (10-day) Percentile
    daily_returns = price_series.pct_change()
    realized_vol_10d = daily_returns.rolling(window=cfg.VOL_REALIZED_PERIOD).std()
    df['realized_vol_10d_percentile'] = realized_vol_10d.rolling(
        window=cfg.COMPRESSION_PERCENTILE_WINDOW
    ).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100)

    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = _calculate_macd(
        price_series, cfg.MACD_FAST_PERIOD, cfg.MACD_SLOW_PERIOD, cfg.MACD_SIGNAL_PERIOD
    )

    # BB on MACD
    df['bb_macd_upper'], df['bb_macd_basis'], df['bb_macd_lower'] = _calculate_bb_on_macd(
        df['macd'], cfg.BB_ON_MACD_LENGTH, cfg.BB_ON_MACD_STD_DEV
    )
    
    # BB on MACD position indicator
    df['bb_macd_position'] = np.where(
        df['macd'] > df['bb_macd_upper'], 'above_upper',
        np.where(df['macd'] < df['bb_macd_lower'], 'below_lower', 'within_bands')
    )

    # RSI
    df['rsi'] = _calculate_rsi(price_series, cfg.RSI_PERIOD)

    # UT Bot Alerts (Regular Candles)
    ut_bot_results = _calculate_ut_bot_signals(
        df, cfg.UT_BOT_KEY_VALUE, cfg.UT_BOT_ATR_PERIOD, use_heikin_ashi=False
    )
    df['ut_bot_trail'] = ut_bot_results['trail']
    df['ut_bot_atr'] = ut_bot_results['atr']
    df['ut_bot_long_signal'] = ut_bot_results['long_signal']
    df['ut_bot_short_signal'] = ut_bot_results['short_signal']
    df['ut_bot_direction'] = ut_bot_results['direction']

    # UT Bot Alerts (Heikin-Ashi Candles)
    ut_bot_ha_results = _calculate_ut_bot_signals(
        df, cfg.UT_BOT_KEY_VALUE, cfg.UT_BOT_ATR_PERIOD, use_heikin_ashi=True
    )
    df['ut_bot_ha_trail'] = ut_bot_ha_results['trail']
    df['ut_bot_ha_long_signal'] = ut_bot_ha_results['long_signal']
    df['ut_bot_ha_short_signal'] = ut_bot_ha_results['short_signal']
    df['ut_bot_ha_direction'] = ut_bot_ha_results['direction']

    # --- Save Results ---
    # Select and reorder columns for clarity
    output_columns = [
        'date', 'open', 'high', 'low', 'close', 'volume'
    ] + [col for col in df.columns if col.startswith('ha_')] + \
      [col for col in df.columns if col not in ['date', 'open', 'high', 'low', 'close', 'volume'] and not col.startswith('ha_')]
    
    df_output = df[output_columns]

    try:
        df_output.to_csv(output_path, index=False)
        print(f"  - Successfully generated and saved analysis to {output_path}")
    except Exception as e:
        print(f"  - Error saving technical analysis for {symbol}: {e}") 
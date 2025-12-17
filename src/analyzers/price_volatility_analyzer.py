import pandas as pd
import numpy as np
import os

# --- Configuration ---
class VolatilityConfig:
    """
    Configuration parameters for volatility analysis.
    Allows for easy tuning of lookback periods and thresholds.
    """
    # Simple Moving Average lookback period for price
    PRICE_SMA_PERIOD = 20
    
    # Standard deviation multiplier for volatility thresholds
    HIGH_VOLATILITY_THRESHOLD = 2.0  # 2 standard deviations above mean
    LOW_VOLATILITY_THRESHOLD = 0.5   # 0.5 standard deviations below mean
    
    # Risk metrics parameters
    RISK_FREE_RATE = 0.0435  # 4.35% annual risk-free rate (10 year treasury yield)
    TRADING_DAYS_PER_YEAR = 365  # Crypto markets trade 24/7
    
    # Sharpe ratio specific parameters
    SHARPE_WINDOWS = [30, 60, 90]  # Multiple windows for more stable Sharpe ratios
    
    # RSI parameters
    RSI_PERIOD = 14  # Standard RSI period
    RSI_OVERBOUGHT = 70  # Traditional overbought threshold
    RSI_OVERSOLD = 30    # Traditional oversold threshold
    
    # Multiple windows for risk metrics
    SORTINO_WINDOWS = [20, 60]  # Short and medium-term Sortino
    MDD_WINDOWS = [20, 60, 120]  # Short, medium, and long-term Max Drawdown
    CVAR_WINDOWS = [20, 60]  # Short and medium-term CVaR
    OMEGA_WINDOWS = [20, 60]  # Short and medium-term Omega
    
    # CVaR parameters
    CVAR_ALPHA = 0.05  # 95% confidence level (5% tail)

def get_volatility_output_path(symbol: str) -> str:
    """Generates the standardized filepath for a given asset's volatility analysis."""
    output_dir = "data/analysis"
    return os.path.join(output_dir, f"volatility_{symbol}.csv")

def _find_date_column(df: pd.DataFrame) -> str | None:
    """Helper function to find the date column in a DataFrame."""
    date_columns = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
    return date_columns[0] if date_columns else None

def _calculate_rsi(returns: pd.Series, period: int) -> float:
    """
    Calculate the Relative Strength Index (RSI) for a series of returns.
    
    Args:
        returns (pd.Series): Series of daily returns
        period (int): RSI calculation period
        
    Returns:
        float: RSI value between 0 and 100
    """
    if len(returns) < period:
        return np.nan
        
    # Calculate gains and losses
    gains = returns.copy()
    losses = returns.copy()
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = abs(losses)
    
    # Calculate average gains and losses
    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1] if not rsi.empty else np.nan

def _calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float, trading_days: int) -> float:
    """
    Calculate the Sharpe Ratio for a series of returns.
    
    Args:
        returns (pd.Series): Series of daily returns
        risk_free_rate (float): Annual risk-free rate
        trading_days (int): Number of trading days in a year
        
    Returns:
        float: Sharpe Ratio
    """
    if len(returns) < 10:  # Need sufficient data points
        return np.nan
        
    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1/trading_days) - 1
    
    # Calculate excess returns
    excess_returns = returns - daily_rf
    
    # Calculate mean and std of excess returns
    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std()
    
    # Guard against division by zero or very small std
    if std_excess == 0 or np.isnan(std_excess):
        return np.nan
        
    # Calculate annualized Sharpe Ratio
    # Use the original trading_days parameter (365 for crypto)
    sharpe = np.sqrt(trading_days) * (mean_excess / std_excess)
        
    return sharpe

def _calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float, trading_days: int) -> float:
    """
    Calculate the Sortino Ratio for a series of returns.
    Only considers downside deviation in the denominator.
    
    Args:
        returns (pd.Series): Series of daily returns
        risk_free_rate (float): Annual risk-free rate
        trading_days (int): Number of trading days in a year
        
    Returns:
        float: Sortino Ratio
    """
    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1/trading_days) - 1
    
    # Calculate excess returns
    excess_returns = returns - daily_rf
    
    if len(excess_returns) > 1:
        # Calculate downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.sqrt(np.mean(downside_returns ** 2))
            if downside_std != 0:
                sortino = np.sqrt(trading_days) * (excess_returns.mean() / downside_std)
                return sortino
    return np.nan

def _calculate_max_drawdown(returns: pd.Series) -> float:
    """
    Calculate the Maximum Drawdown for a series of returns.
    
    Args:
        returns (pd.Series): Series of daily returns
        
    Returns:
        float: Maximum Drawdown as a percentage
    """
    if len(returns) > 1:
        # Calculate cumulative returns
        cum_returns = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cum_returns.cummax()
        
        # Calculate drawdowns
        drawdowns = (cum_returns - running_max) / running_max
        
        # Get maximum drawdown
        max_drawdown = drawdowns.min()
        return abs(max_drawdown)  # Return as positive percentage
    return np.nan

def _calculate_cvar(returns: pd.Series, alpha: float = 0.05) -> float:
    """
    Calculate Conditional Value at Risk (CVaR) or Expected Shortfall.
    
    Args:
        returns (pd.Series): Series of daily returns
        alpha (float): Confidence level (default 0.05 for 95% confidence)
        
    Returns:
        float: CVaR value (negative number representing expected loss)
    """
    if len(returns) < 2:
        return np.nan
        
    # Use numpy's quantile function for more robust calculation
    var = np.quantile(returns, alpha)
    
    # Calculate CVaR as the mean of returns below the VaR
    # Only include returns that are less than or equal to VaR
    tail_returns = returns[returns <= var]
    
    if len(tail_returns) == 0:
        return np.nan
        
    return np.mean(tail_returns)

def _calculate_omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    """
    Calculate the Omega Ratio, which is the ratio of gains to losses above a threshold.
    Uses the textbook definition: sum of gains / sum of losses.
    
    Args:
        returns (pd.Series): Series of daily returns
        threshold (float): Return threshold (default 0.0)
        
    Returns:
        float: Omega Ratio
    """
    if len(returns) < 2:
        return np.nan
        
    # Calculate gains and losses relative to threshold
    gains = returns[returns > threshold] - threshold
    losses = threshold - returns[returns < threshold]
    
    # Handle edge cases
    if len(losses) == 0:
        return np.inf  # No losses, perfect ratio
    if len(gains) == 0:
        return 0.0  # No gains, worst ratio
        
    # Calculate sum of gains and losses (textbook definition)
    sum_gains = np.sum(gains)
    sum_losses = np.sum(losses)
    
    # Guard against division by zero
    if sum_losses == 0:
        return np.inf
        
    return sum_gains / sum_losses

def _calculate_volatility_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates volatility metrics based on the provided configuration.
    
    Args:
        df (pd.DataFrame): DataFrame with price data.
        
    Returns:
        pd.DataFrame: A new DataFrame with the date and volatility metrics.
    """
    cfg = VolatilityConfig()

    # 1. Find the date and price columns
    date_col = _find_date_column(df)
    if not date_col:
        raise ValueError("Could not find a date/timestamp column in the price data.")
        
    # Assuming the close price is the main price column
    if 'close' in df.columns:
        price_col = 'close'
    else:
        numeric_cols = df.select_dtypes(include='number').columns
        if len(numeric_cols) > 0:
            price_col = numeric_cols[0]
        else:
            raise ValueError("Could not find a numeric price column.")

    # 2. Ensure date column is in datetime format
    df[date_col] = pd.to_datetime(df[date_col])
    
    # 3. Calculate daily returns
    df['daily_return'] = df[price_col].pct_change()
    
    # 4. Calculate rolling statistics
    df['return_sma'] = df['daily_return'].rolling(window=cfg.PRICE_SMA_PERIOD).mean()
    df['return_std'] = df['daily_return'].rolling(window=cfg.PRICE_SMA_PERIOD).std()
    
    # 5. Define volatility thresholds
    df['high_vol_threshold'] = df['return_sma'] + (df['return_std'] * cfg.HIGH_VOLATILITY_THRESHOLD)
    df['low_vol_threshold'] = df['return_sma'] - (df['return_std'] * cfg.LOW_VOLATILITY_THRESHOLD)
    
    # 6. Determine the volatility state
    df['volatility_state'] = np.where(
        df['daily_return'] > df['high_vol_threshold'],
        'High',
        np.where(
            df['daily_return'] < df['low_vol_threshold'],
            'Low',
            'Normal'
        )
    )
    
    # 7. Calculate risk metrics with multiple windows
    # Sharpe Ratio with multiple windows for stability
    for window in cfg.SHARPE_WINDOWS:
        df[f'sharpe_ratio_{window}d'] = df['daily_return'].rolling(
            window=window,
            min_periods=window
        ).apply(
            lambda x: _calculate_sharpe_ratio(
                x,
                cfg.RISK_FREE_RATE,
                cfg.TRADING_DAYS_PER_YEAR
            )
        )
    
    # Sortino Ratio with multiple windows
    for window in cfg.SORTINO_WINDOWS:
        df[f'sortino_ratio_{window}d'] = df['daily_return'].rolling(
            window=window,
            min_periods=window
        ).apply(
            lambda x: _calculate_sortino_ratio(
                x,
                cfg.RISK_FREE_RATE,
                cfg.TRADING_DAYS_PER_YEAR
            )
        )
    
    # Max Drawdown with multiple windows
    for window in cfg.MDD_WINDOWS:
        df[f'max_drawdown_{window}d'] = df['daily_return'].rolling(
            window=window,
            min_periods=window
        ).apply(_calculate_max_drawdown)
    
    # CVaR with multiple windows
    for window in cfg.CVAR_WINDOWS:
        df[f'cvar_{window}d'] = df['daily_return'].rolling(
            window=window,
            min_periods=window
        ).apply(lambda x: _calculate_cvar(x, cfg.CVAR_ALPHA))
    
    # Omega Ratio with multiple windows
    for window in cfg.OMEGA_WINDOWS:
        df[f'omega_ratio_{window}d'] = df['daily_return'].rolling(
            window=window,
            min_periods=window
        ).apply(_calculate_omega_ratio)
    
    # 8. Calculate RSI
    df['rsi'] = df['daily_return'].rolling(
        window=cfg.RSI_PERIOD,
        min_periods=cfg.RSI_PERIOD
    ).apply(lambda x: _calculate_rsi(x, cfg.RSI_PERIOD))
    
    # 9. Add RSI state
    df['rsi_state'] = np.where(
        df['rsi'] > cfg.RSI_OVERBOUGHT,
        'Overbought',
        np.where(
            df['rsi'] < cfg.RSI_OVERSOLD,
            'Oversold',
            'Neutral'
        )
    )
    
    # 10. Prepare the final output DataFrame
    # Get all columns except intermediate calculations
    result_columns = [date_col, 'daily_return', 'volatility_state', 'rsi', 'rsi_state']
    
    # Add all risk metric columns
    for window in cfg.SHARPE_WINDOWS:
        result_columns.append(f'sharpe_ratio_{window}d')
    for window in cfg.SORTINO_WINDOWS:
        result_columns.append(f'sortino_ratio_{window}d')
    for window in cfg.MDD_WINDOWS:
        result_columns.append(f'max_drawdown_{window}d')
    for window in cfg.CVAR_WINDOWS:
        result_columns.append(f'cvar_{window}d')
    for window in cfg.OMEGA_WINDOWS:
        result_columns.append(f'omega_ratio_{window}d')
    
    result_df = df[result_columns].copy()
    result_df.rename(columns={date_col: 'date'}, inplace=True)
    
    return result_df

def update_volatility_analysis(price_path: str, symbol: str, last_analysis_date: str | None = None):
    """
    Update volatility analysis with new data.
    If last_analysis_date is provided, only processes data from that date onwards.
    Ensures we have enough historical data for all rolling calculations.
    
    Args:
        price_path (str): Path to the price data file
        symbol (str): Asset symbol
        last_analysis_date (str | None): Last date of previous analysis
    """
    print(f"\n--- Updating Volatility Analysis for {symbol} ---")
    
    try:
        # Load price data
        if not os.path.exists(price_path):
            print(f"Error: Price data not found at {price_path}. Aborting.")
            return
        
        df_price = pd.read_csv(price_path)
        date_col = _find_date_column(df_price)
        if not date_col:
            print("Error: Could not find date column in price data.")
            return
            
        df_price[date_col] = pd.to_datetime(df_price[date_col])
        
        # Determine the lookback period needed for calculations
        cfg = VolatilityConfig()
        lookback_days = max(
            cfg.PRICE_SMA_PERIOD,  # For volatility calculations
            cfg.RSI_PERIOD         # For RSI
        )
        
        if last_analysis_date:
            # Convert last_analysis_date to datetime
            last_date = pd.to_datetime(last_analysis_date)
            
            # Get the start date for our calculations
            # We need 'lookback_days' days before the last analysis date
            calculation_start = last_date - pd.Timedelta(days=lookback_days)
            
            # Filter data to include both the lookback period and new data
            df_price = df_price[df_price[date_col] >= calculation_start]
            
            if df_price.empty:
                print("No new data to analyze.")
                return
                
            print(f"Processing data from {df_price[date_col].min().date()} to {df_price[date_col].max().date()}")
            print(f"Including {lookback_days} days of historical data for calculations")
            
        # Calculate metrics for the data
        df_analysis = _calculate_volatility_metrics(df_price)
        
        # Load existing analysis if it exists
        output_path = get_volatility_output_path(symbol)
        if os.path.exists(output_path):
            df_existing = pd.read_csv(output_path)
            df_existing['date'] = pd.to_datetime(df_existing['date'])
            df_analysis['date'] = pd.to_datetime(df_analysis['date'])
            
            # Combine and remove duplicates
            df_combined = pd.concat([df_existing, df_analysis])
            df_combined = df_combined.drop_duplicates(subset=['date'], keep='last')
            df_combined = df_combined.sort_values('date')
            
            # Save combined results
            df_combined.to_csv(output_path, index=False)
            print(f"Updated volatility analysis for {symbol} saved to {output_path}")
        else:
            # Save new analysis
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            df_analysis.to_csv(output_path, index=False)
            print(f"New volatility analysis for {symbol} saved to {output_path}")
            
    except Exception as e:
        print(f"Error updating volatility analysis for {symbol}: {e}")

def generate_volatility_analysis(price_path: str, symbol: str):
    """
    Main function to generate the volatility analysis for a given asset.
    It loads data, calculates the metrics, and saves the result.
    """
    print(f"\n--- Generating Volatility Analysis for {symbol} ---")
    
    # 1. Load Data
    try:
        if not os.path.exists(price_path):
            print(f"Error: Price data not found at {price_path}. Aborting.")
            return
        
        df = pd.read_csv(price_path)
        
    except Exception as e:
        print(f"Error loading price data for {symbol}: {e}")
        return

    # 2. Calculate Volatility Metrics
    df_analysis = _calculate_volatility_metrics(df)

    # 3. Save Results
    try:
        output_path = get_volatility_output_path(symbol)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the analysis result
        df_analysis.to_csv(output_path, index=False)
        print(f"Volatility analysis for {symbol} saved to {output_path}")

    except Exception as e:
        print(f"Error saving volatility analysis for {symbol}: {e}")


if __name__ == '__main__':
    """
    Allows for direct execution of the script for testing and development.
    """
    print("Running price_volatility_analyzer.py directly for testing...")
    
    # --- Test Configuration ---
    test_symbol = "BTCUSDT"
    test_price_path = os.path.join("data", "daily", f"historical_price_{test_symbol}.csv")
    
    # Check if test data exists before running
    if os.path.exists(test_price_path):
        generate_volatility_analysis(
            price_path=test_price_path,
            symbol=test_symbol
        )
    else:
        print(f"Test failed: Price data file not found at '{test_price_path}'")
        print("Please ensure price data has been collected for the test symbol.") 
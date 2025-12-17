import pandas as pd
import os

# --- Configuration ---
class InstabilityConfig:
    """
    Configuration parameters for instability analysis.
    Allows for easy tuning of lookback periods and thresholds.
    """
    LIQUIDATION_SMA_PERIOD = 10
    LIQUIDATION_STD_DEV_FACTOR = 2.0 # Spike is 2x std dev above the moving average

def get_instability_output_path(symbol: str) -> str:
    """Generates the standardized filepath for a given asset's instability analysis."""
    output_dir = "data/analysis"
    return os.path.join(output_dir, f"instability_{symbol}.csv")

def _find_date_column(df: pd.DataFrame) -> str | None:
    """Finds the most likely date column from a DataFrame."""
    common_names = ['date', 'timestamp', 'time']
    for name in common_names:
        if name in df.columns:
            return name
    return None

def _calculate_liquidation_spikes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates liquidation spikes based on the provided configuration.
    
    Args:
        df (pd.DataFrame): DataFrame with liquidation data.
        
    Returns:
        pd.DataFrame: A new DataFrame with the date and instability_index.
    """
    cfg = InstabilityConfig()

    # 1. Find the date and liquidation columns
    date_col = _find_date_column(df)
    if not date_col:
        raise ValueError("Could not find a date/timestamp column in the liquidation data.")
        
    # Assuming the liquidation volume is the first numeric column if not named 'total_liquidations'
    numeric_cols = df.select_dtypes(include='number').columns
    if 'total_liquidations' in numeric_cols:
        liq_col = 'total_liquidations'
    elif len(numeric_cols) > 0:
        liq_col = numeric_cols[0]
    else:
        raise ValueError("Could not find a numeric liquidation volume column.")

    # 2. Ensure date column is in datetime format
    df[date_col] = pd.to_datetime(df[date_col])
    
    # 3. Calculate SMA and Std Dev
    df['liq_sma'] = df[liq_col].rolling(window=cfg.LIQUIDATION_SMA_PERIOD).mean()
    df['liq_std'] = df[liq_col].rolling(window=cfg.LIQUIDATION_SMA_PERIOD).std()
    
    # 4. Define the spike threshold
    df['spike_threshold'] = df['liq_sma'] + (df['liq_std'] * cfg.LIQUIDATION_STD_DEV_FACTOR)
    
    # 5. Determine the instability index
    # A spike occurs if the liquidation volume exceeds the dynamic threshold
    df['instability_index'] = df.apply(
        lambda row: "High" if row[liq_col] > row['spike_threshold'] else "Normal",
        axis=1
    )
    
    # 6. Prepare the final output DataFrame
    result_df = df[[date_col, liq_col, 'instability_index']].copy()
    result_df.rename(columns={date_col: 'date', liq_col: 'total_liquidations'}, inplace=True)
    
    return result_df

def generate_instability_analysis(liquidation_path: str, symbol: str):
    """
    Main function to generate the instability analysis for a given asset.
    It loads data, calculates the index, and saves the result.
    """
    print(f"\n--- Generating Instability Analysis for {symbol} ---")
    
    # 1. Load Data
    try:
        if not os.path.exists(liquidation_path):
            print(f"Error: Liquidation data not found at {liquidation_path}. Aborting.")
            return
        
        # Ensure the date column is parsed correctly on load
        df = pd.read_csv(liquidation_path)
        
    except Exception as e:
        print(f"Error loading liquidation data for {symbol}: {e}")
        return

    # 2. Calculate Instability Index
    df_analysis = _calculate_liquidation_spikes(df)

    # 3. Save Results
    try:
        output_path = get_instability_output_path(symbol)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the analysis result
        df_analysis.to_csv(output_path, index=False)
        print(f"Instability analysis for {symbol} saved to {output_path}")

    except Exception as e:
        print(f"Error saving instability analysis for {symbol}: {e}")


if __name__ == '__main__':
    """
    Allows for direct execution of the script for testing and development.
    """
    print("Running instability_analyzer.py directly for testing...")
    
    # --- Test Configuration ---
    test_symbol = "BTCUSDT"
    test_liquidation_path = os.path.join("data", "daily", f"liquidations_{test_symbol}_binance.csv")
    
    # Check if test data exists before running
    if os.path.exists(test_liquidation_path):
        generate_instability_analysis(
            liquidation_path=test_liquidation_path,
            symbol=test_symbol
        )
    else:
        print(f"Test failed: Liquidation data file not found at '{test_liquidation_path}'")
        print("Please ensure collectors have been run for the test symbol.") 
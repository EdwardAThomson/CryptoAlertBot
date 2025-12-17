import pandas as pd
import mplfinance as mpf
import os
from src.analyzers.technical_analyzer import get_technical_analysis_output_path as get_analysis_path

def get_heikin_ashi_plot_output_path(symbol: str, timeframe: str = 'daily', ext: str = 'png') -> str:
    """Generates the standardized filepath for a given asset's Heikin Ashi plot."""
    if ext not in ['png', 'svg']:
        raise ValueError("Extension must be 'png' or 'svg'")

    if timeframe == 'weekly':
        filename = f"heikin_ashi_plot_{symbol}_weekly.{ext}"
    else:
        filename = f"heikin_ashi_plot_{symbol}.{ext}"

    if ext == 'svg':
        output_dir = os.path.join("plots", "svg")
    else:
        output_dir = "plots"
        
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)

def generate_heikin_ashi_plot(symbol: str, timeframe: str = 'daily', last_n_periods: int = 180):
    """
    Generates and saves a Heikin Ashi candlestick plot for the given symbol.

    Args:
        symbol (str): The asset symbol (e.g., 'BTCUSDT').
        timeframe (str): The timeframe to plot ('daily' or 'weekly').
        last_n_periods (int): The number of recent periods (days/weeks) to plot.
    """
    timeframe_str = "Weekly" if timeframe == 'weekly' else "Daily"
    print(f"--- Generating {timeframe_str} Heikin Ashi Plot for {symbol} ---")
    
    # Define file paths
    analysis_path = get_analysis_path(symbol, timeframe)

    # Read data
    try:
        df = pd.read_csv(analysis_path, index_col='date', parse_dates=True)
        required_cols = ['ha_open', 'ha_high', 'ha_low', 'ha_close', 'volume']
        if not all(col in df.columns for col in required_cols):
            print(f"  - Skipping plot for {symbol}: Heikin Ashi columns not found in {analysis_path}")
            return
    except FileNotFoundError:
        print(f"  - Skipping plot for {symbol}: Analysis file not found at {analysis_path}")
        return
    except Exception as e:
        print(f"  - Error reading analysis file for {symbol}: {e}")
        return

    # Prepare DataFrame for plotting Heikin Ashi candles
    ha_df = df[required_cols].copy()
    ha_df.rename(columns={
        'ha_open': 'open',
        'ha_high': 'high',
        'ha_low': 'low',
        'ha_close': 'close'
    }, inplace=True)

    # Take the last N periods for a clearer plot
    df_plot = ha_df.tail(last_n_periods)

    if df_plot.empty:
        print(f"  - Skipping plot for {symbol}: No data available for the last {last_n_periods} periods.")
        return

    # --- Generate the Plot ---
    try:
        # Define the output path for the PNG
        output_path_png = get_heikin_ashi_plot_output_path(symbol, timeframe, 'png')

        # Plotting call for PNG
        mpf.plot(
            df_plot,
            type='candle',
            style='yahoo',
            title=f"{timeframe_str} Heikin Ashi Candles for {symbol} ({last_n_periods} periods)",
            ylabel='Price (USD)',
            figscale=1.5,
            volume=True,
            ylabel_lower='Volume',
            savefig=dict(fname=output_path_png, dpi=100)
        )
        print(f"  - Successfully generated and saved PNG to {output_path_png}")

        # Define the output path for the SVG
        output_path_svg = get_heikin_ashi_plot_output_path(symbol, timeframe, 'svg')

        # Plotting call for SVG
        mpf.plot(
            df_plot,
            type='candle',
            style='yahoo',
            title=f"{timeframe_str} Heikin Ashi Candles for {symbol} ({last_n_periods} periods)",
            ylabel='Price (USD)',
            figscale=1.5,
            volume=True,
            ylabel_lower='Volume',
            savefig=dict(fname=output_path_svg, format='svg')
        )
        print(f"  - Successfully generated and saved SVG to {output_path_svg}")

    except Exception as e:
        print(f"  - An error occurred during plotting for {symbol}: {e}") 
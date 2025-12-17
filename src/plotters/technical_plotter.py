import pandas as pd
import mplfinance as mpf
import os
from src.analyzers.technical_analyzer import get_technical_analysis_output_path as get_analysis_path

def get_technical_plot_output_path(symbol: str, timeframe: str = 'daily', ext: str = 'png') -> str:
    """Generates the standardized filepath for a given asset's technical plot."""
    if ext not in ['png', 'svg']:
        raise ValueError("Extension must be 'png' or 'svg'")

    if timeframe == 'weekly':
        filename = f"technical_plot_{symbol}_weekly.{ext}"
    else:
        filename = f"technical_plot_{symbol}.{ext}"

    if ext == 'svg':
        output_dir = os.path.join("plots", "svg")
    else:
        output_dir = "plots"
        
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)

def generate_technical_plot(symbol: str, timeframe: str = 'daily', last_n_periods: int = 180):
    """
    Generates and saves a technical analysis plot for the given symbol.

    Args:
        symbol (str): The asset symbol (e.g., 'BTCUSDT').
        timeframe (str): The timeframe to plot ('daily' or 'weekly').
        last_n_periods (int): The number of recent periods (days/weeks) to plot.
    """
    timeframe_str = "Weekly" if timeframe == 'weekly' else "Daily"
    print(f"--- Generating {timeframe_str} Technical Analysis Plot for {symbol} ---")
    
    # Define file paths
    analysis_path = get_analysis_path(symbol, timeframe)
    output_path_png = get_technical_plot_output_path(symbol, timeframe, 'png')

    # Read data
    try:
        df = pd.read_csv(analysis_path, index_col='date', parse_dates=True)
    except FileNotFoundError:
        print(f"  - Skipping plot for {symbol}: Analysis file not found at {analysis_path}")
        return
    except Exception as e:
        print(f"  - Error reading analysis file for {symbol}: {e}")
        return

    # Take the last N periods for a clearer plot
    df_plot = df.tail(last_n_periods)

    if df_plot.empty:
        print(f"  - Skipping plot for {symbol}: No data available for the last {last_n_periods} periods.")
        return

    # --- Create Additional Plots (APs) for mplfinance ---
    # This list will hold all the subplot definitions
    aps = []

    # SMA Plots (plotted on the main panel)
    if 'sma_50' in df_plot.columns:
        aps.append(mpf.make_addplot(df_plot['sma_50'], color='blue'))
    if 'sma_200' in df_plot.columns:
        aps.append(mpf.make_addplot(df_plot['sma_200'], color='red'))

    # MACD Plot
    if all(col in df_plot.columns for col in ['macd', 'macd_signal']):
        # Plot MACD line and Signal line, and a histogram for the difference
        macd_diff = df_plot['macd'] - df_plot['macd_signal']
        aps.append(mpf.make_addplot(df_plot[['macd', 'macd_signal']], panel=1, ylabel='MACD'))
        aps.append(mpf.make_addplot(macd_diff, type='bar', panel=1, color='gray', alpha=0.5))
    
    # RSI Plot
    if 'rsi' in df_plot.columns:
        # Create a plot for RSI and add overbought/oversold lines
        aps.append(mpf.make_addplot(
            df_plot['rsi'],
            panel=2,
            ylabel='RSI',
            color='purple',
            secondary_y=False
        ))
        # Add horizontal lines for overbought/oversold levels by creating constant plots
        aps.append(mpf.make_addplot([70] * len(df_plot), panel=2, color='r', linestyle='-.', secondary_y=False))
        aps.append(mpf.make_addplot([30] * len(df_plot), panel=2, color='g', linestyle='-.', secondary_y=False))

    # Bollinger Bands
    # mplfinance can plot these directly if columns are named correctly,
    # but we will add them as simple overlays on the main plot for consistency.
    if all(col in df_plot.columns for col in ['bb_upper', 'bb_middle', 'bb_lower']):
         aps.append(mpf.make_addplot(df_plot[['bb_upper', 'bb_lower']], color='gray', alpha=0.4))
         aps.append(mpf.make_addplot(df_plot['bb_middle'], color='orange', linestyle='--'))

    # UT Bot elements removed - now only in dedicated UT Bot plot


    # --- Generate the Plot ---
    try:
        # Plotting call for PNG
        mpf.plot(
            df_plot,
            type='candle',
            style='yahoo',
            title=f"{timeframe_str} Technical Analysis for {symbol} ({last_n_periods} periods)",
            ylabel='Price (USD)',
            addplot=aps,
            panel_ratios=(6, 3, 2), # Ratios for main plot, panel 1 (MACD), panel 2 (RSI)
            figscale=1.5,
            volume=True,
            ylabel_lower='Volume',
            savefig=dict(fname=output_path_png, dpi=100)
        )
        print(f"  - Successfully generated and saved PNG to {output_path_png}")

        # Define the output path for the SVG
        output_path_svg = get_technical_plot_output_path(symbol, timeframe, 'svg')

        # Plotting call for SVG
        mpf.plot(
            df_plot,
            type='candle',
            style='yahoo',
            title=f"{timeframe_str} Technical Analysis for {symbol} ({last_n_periods} periods)",
            ylabel='Price (USD)',
            addplot=aps,
            panel_ratios=(6, 3, 2),
            figscale=1.5,
            volume=True,
            ylabel_lower='Volume',
            savefig=dict(fname=output_path_svg, format='svg')
        )
        print(f"  - Successfully generated and saved SVG to {output_path_svg}")

    except Exception as e:
        print(f"  - An error occurred during plotting for {symbol}: {e}")

def generate_ut_bot_plot(symbol: str, timeframe: str = 'daily', last_n_periods: int = 180):
    """
    Generates a focused UT Bot Alerts plot for the given symbol.
    
    Args:
        symbol (str): The asset symbol (e.g., 'BTCUSDT').
        timeframe (str): The timeframe to plot ('daily' or 'weekly').
        last_n_periods (int): The number of recent periods to plot.
    """
    timeframe_str = "Weekly" if timeframe == 'weekly' else "Daily"
    print(f"--- Generating {timeframe_str} UT Bot Plot for {symbol} ---")
    
    # Define file paths
    analysis_path = get_analysis_path(symbol, timeframe)
    
    # Create output path for UT Bot specific plot
    if timeframe == 'weekly':
        filename = f"ut_bot_plot_{symbol}_weekly.png"
    else:
        filename = f"ut_bot_plot_{symbol}.png"
    output_path = os.path.join("plots", filename)
    os.makedirs("plots", exist_ok=True)

    # Read data
    try:
        df = pd.read_csv(analysis_path, index_col='date', parse_dates=True)
    except FileNotFoundError:
        print(f"  - Skipping UT Bot plot for {symbol}: Analysis file not found at {analysis_path}")
        return
    except Exception as e:
        print(f"  - Error reading analysis file for {symbol}: {e}")
        return

    # Take the last N periods for a clearer plot
    df_plot = df.tail(last_n_periods)

    if df_plot.empty:
        print(f"  - Skipping UT Bot plot for {symbol}: No data available for the last {last_n_periods} periods.")
        return

    # Check if UT Bot columns exist
    required_cols = ['ut_bot_trail', 'ut_bot_long_signal', 'ut_bot_short_signal', 'ut_bot_atr']
    if not all(col in df_plot.columns for col in required_cols):
        print(f"  - Skipping UT Bot plot for {symbol}: UT Bot columns not found in analysis data")
        return

    # --- Create UT Bot Specific Plots ---
    aps = []

    # UT Bot Trailing Stop
    aps.append(mpf.make_addplot(df_plot['ut_bot_trail'], color='red', alpha=0.9))
    
    # UT Bot Signals
    long_signals = df_plot['ut_bot_long_signal']
    short_signals = df_plot['ut_bot_short_signal']
    
    # Long signals - green triangles up
    long_signal_prices = df_plot['close'].where(long_signals, float('nan'))
    aps.append(mpf.make_addplot(long_signal_prices, type='scatter', markersize=120, marker='^', color='green'))
    
    # Short signals - red triangles down
    short_signal_prices = df_plot['close'].where(short_signals, float('nan'))
    aps.append(mpf.make_addplot(short_signal_prices, type='scatter', markersize=120, marker='v', color='red'))

    # UT Bot ATR in separate panel
    aps.append(mpf.make_addplot(
        df_plot['ut_bot_atr'],
        panel=1,
        ylabel='ATR',
        color='purple',
        secondary_y=False
    ))

    # --- Generate the UT Bot Plot ---
    try:
        mpf.plot(
            df_plot,
            type='candle',
            style='yahoo',
            title=f"{timeframe_str} UT Bot Alerts for {symbol} ({last_n_periods} periods)",
            ylabel='Price (USD)',
            addplot=aps,
            panel_ratios=(4, 1), # Main price panel and ATR panel
            figscale=1.5,
            volume=True,
            ylabel_lower='Volume',
            savefig=dict(fname=output_path, dpi=100)
        )
        print(f"  - Successfully generated and saved UT Bot plot to {output_path}")

    except Exception as e:
        print(f"  - An error occurred during UT Bot plotting for {symbol}: {e}")

def generate_bb_macd_plot(symbol: str, timeframe: str = 'daily', last_n_periods: int = 180):
    """
    Generates a focused Bollinger Bands on MACD plot for the given symbol.
    
    Args:
        symbol (str): The asset symbol (e.g., 'BTCUSDT').
        timeframe (str): The timeframe to plot ('daily' or 'weekly').
        last_n_periods (int): The number of recent periods to plot.
    """
    timeframe_str = "Weekly" if timeframe == 'weekly' else "Daily"
    print(f"--- Generating {timeframe_str} BB on MACD Plot for {symbol} ---")
    
    # Define file paths
    analysis_path = get_analysis_path(symbol, timeframe)
    
    # Create output path for BB on MACD specific plot
    if timeframe == 'weekly':
        filename = f"bb_macd_plot_{symbol}_weekly.png"
    else:
        filename = f"bb_macd_plot_{symbol}.png"
    output_path = os.path.join("plots", filename)
    os.makedirs("plots", exist_ok=True)

    # Read data
    try:
        df = pd.read_csv(analysis_path, index_col='date', parse_dates=True)
    except FileNotFoundError:
        print(f"  - Skipping BB on MACD plot for {symbol}: Analysis file not found at {analysis_path}")
        return
    except Exception as e:
        print(f"  - Error reading analysis file for {symbol}: {e}")
        return

    # Take the last N periods for a clearer plot
    df_plot = df.tail(last_n_periods)

    if df_plot.empty:
        print(f"  - Skipping BB on MACD plot for {symbol}: No data available for the last {last_n_periods} periods.")
        return

    # Check if BB on MACD columns exist
    required_cols = ['macd', 'macd_signal', 'bb_macd_upper', 'bb_macd_basis', 'bb_macd_lower']
    if not all(col in df_plot.columns for col in required_cols):
        print(f"  - Skipping BB on MACD plot for {symbol}: Required columns not found in analysis data")
        return

    # --- Create BB on MACD Specific Plots ---
    aps = []

    # Price with SMAs on main panel
    if 'sma_50' in df_plot.columns:
        aps.append(mpf.make_addplot(df_plot['sma_50'], color='blue', alpha=0.7))
    if 'sma_200' in df_plot.columns:
        aps.append(mpf.make_addplot(df_plot['sma_200'], color='red', alpha=0.7))

    # MACD with BB on MACD in panel 1
    aps.append(mpf.make_addplot(df_plot[['macd', 'macd_signal']], panel=1, ylabel='MACD'))
    aps.append(mpf.make_addplot(df_plot['bb_macd_basis'], panel=1, color='gray', alpha=0.8))
    aps.append(mpf.make_addplot(df_plot[['bb_macd_upper', 'bb_macd_lower']], panel=1, color='green', alpha=0.6))
    
    # Fill between BB bands
    # Note: mplfinance doesn't support fill_between directly, so we'll use transparency to show the bands
    
    # Color MACD based on position relative to BB bands
    if 'bb_macd_position' in df_plot.columns:
        above_upper = df_plot['bb_macd_position'] == 'above_upper'
        below_lower = df_plot['bb_macd_position'] == 'below_lower'
        
        # Highlight points where MACD is outside the bands
        if above_upper.any():
            above_upper_prices = df_plot['macd'].where(above_upper, float('nan'))
            aps.append(mpf.make_addplot(above_upper_prices, panel=1, type='scatter', markersize=30, marker='o', color='green', alpha=0.8))
        
        if below_lower.any():
            below_lower_prices = df_plot['macd'].where(below_lower, float('nan'))
            aps.append(mpf.make_addplot(below_lower_prices, panel=1, type='scatter', markersize=30, marker='o', color='red', alpha=0.8))

    # --- Generate the BB on MACD Plot ---
    try:
        mpf.plot(
            df_plot,
            type='candle',
            style='yahoo',
            title=f"{timeframe_str} BB on MACD Analysis for {symbol} ({last_n_periods} periods)",
            ylabel='Price (USD)',
            addplot=aps,
            panel_ratios=(3, 2), # Main price panel and MACD panel
            figscale=1.5,
            volume=True,
            ylabel_lower='Volume',
            savefig=dict(fname=output_path, dpi=100)
        )
        print(f"  - Successfully generated and saved BB on MACD plot to {output_path}")

    except Exception as e:
        print(f"  - An error occurred during BB on MACD plotting for {symbol}: {e}") 
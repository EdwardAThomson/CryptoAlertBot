import os
import pandas as pd
import matplotlib.pyplot as plt

# Define a directory to save plots, relative to the project root
PLOTS_DIR = "plots"

def _read_and_standardize_df(filepath: str, date_col_name: str, value_col_name: str) -> pd.DataFrame | None:
    """Helper to read a CSV, standardize the date column, and select required columns."""
    try:
        df = pd.read_csv(filepath)

        if 'date' in df.columns:
            date_col = 'date'
        elif 'timestamp' in df.columns:
            date_col = 'timestamp'
        else:
            print(f"Error: No 'date' or 'timestamp' column in {filepath}")
            return None
        
        if value_col_name not in df.columns:
            print(f"Error: Value column '{value_col_name}' not found in {filepath}")
            return None

        df.rename(columns={date_col: 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        
        return df[['date', value_col_name]]
        
    except FileNotFoundError:
        print(f"Error: Data file not found at {filepath}")
        return None
    except Exception as e:
        print(f"Error reading or processing file {filepath}: {e}")
        return None

def generate_combined_plot(
    price_path: str, 
    cvd_path: str, 
    oi_path: str, 
    symbol: str
):
    """
    Reads price, CVD, and Open Interest data for a given symbol, and generates a
    single image file containing three separate subplots, one for each metric.
    """
    output_filename = f"combined_plot_{symbol}.png"
    print(f"Attempting to generate combined subplot for {symbol}...")

    # 1. Read and load all three data sources using the helper
    df_price = _read_and_standardize_df(price_path, 'date', 'close')
    df_cvd = _read_and_standardize_df(cvd_path, 'date', 'CVD')
    df_oi = _read_and_standardize_df(oi_path, 'date', 'sumOpenInterest')

    if df_price is None or df_cvd is None or df_oi is None:
        print("Failed to load one or more data files. Aborting combined plot.")
        return

    # 2. Merge the data into a single DataFrame based on the 'date' column
    df_combined = pd.merge(df_price, df_cvd, on='date', how='inner')
    df_combined = pd.merge(df_combined, df_oi, on='date', how='inner')
    
    if df_combined.empty:
        print("Error: Combined DataFrame is empty after merging. Check for common dates in data files.")
        return

    print("Data loaded and merged successfully. Generating subplots...")

    # 3. Create a figure and a set of subplots
    # 3 rows, 1 column. sharex=True links the x-axes.
    fig, axes = plt.subplots(3, 1, figsize=(14, 18), sharex=True)
    
    # --- Plot 1: Price ---
    axes[0].plot(df_combined['date'], df_combined['close'], color='green', label='Price')
    axes[0].set_title('Price (USD)', fontsize=14)
    axes[0].set_ylabel('Price', fontsize=12)
    axes[0].grid(True, linestyle='--', linewidth=0.5)
    axes[0].legend()

    # --- Plot 2: CVD ---
    axes[1].plot(df_combined['date'], df_combined['CVD'], color='blue', label='CVD')
    axes[1].set_title('Cumulative Volume Delta (CVD)', fontsize=14)
    axes[1].set_ylabel('CVD', fontsize=12)
    axes[1].grid(True, linestyle='--', linewidth=0.5)
    axes[1].legend()

    # --- Plot 3: Open Interest ---
    axes[2].plot(df_combined['date'], df_combined['sumOpenInterest'], color='purple', label='Open Interest')
    axes[2].set_title('Open Interest', fontsize=14)
    axes[2].set_ylabel('Open Interest', fontsize=12)
    axes[2].grid(True, linestyle='--', linewidth=0.5)
    axes[2].legend()

    # Set the shared X-axis label only on the bottom plot
    axes[2].set_xlabel('Date', fontsize=12)

    # Add a main title for the entire figure, now including the asset symbol
    fig.suptitle(f'Daily Metrics Overview - {symbol}', fontsize=18, weight='bold')
    
    # Adjust layout to prevent titles and labels from overlapping
    fig.tight_layout(rect=[0, 0.03, 1, 0.96]) # Adjust rect for the new longer title

    # 4. Save the entire figure to a single file
    os.makedirs(PLOTS_DIR, exist_ok=True)
    full_output_path = os.path.join(PLOTS_DIR, output_filename)
    try:
        plt.savefig(full_output_path)
        print(f"Combined plot saved successfully to {full_output_path}")
    except Exception as e:
        print(f"Error saving combined plot to {full_output_path}: {e}")
    
    # 5. Save the figure as an SVG in a separate directory
    SVG_DIR = os.path.join(PLOTS_DIR, "svg")
    os.makedirs(SVG_DIR, exist_ok=True)
    svg_output_filename = output_filename.replace(".png", ".svg")
    svg_output_path = os.path.join(SVG_DIR, svg_output_filename)
    try:
        plt.savefig(svg_output_path, format='svg')
        print(f"SVG version of combined plot saved successfully to {svg_output_path}")
    except Exception as e:
        print(f"Error saving SVG version of combined plot: {e}")
    finally:
        plt.close(fig) # Close the figure to free up memory 
import os
import pandas as pd
import matplotlib.pyplot as plt

# Define a directory to save plots, relative to the project root
PLOTS_DIR = "plots"

def generate_liquidation_plot(data_path: str, symbol: str):
    """
    Reads liquidation data from a specified CSV file for a given symbol and generates a plot.

    Args:
        data_path (str): The full path to the input CSV data file.
        symbol (str): The asset symbol (e.g., 'BTCUSDT') being plotted.
    """
    output_filename = f"liquidation_{symbol}_plot.png"
    print(f"Attempting to generate Liquidation plot for {symbol} from {data_path}...")

    # 1. Ensure the output directory exists
    try:
        os.makedirs(PLOTS_DIR, exist_ok=True)
    except OSError as e:
        print(f"Error creating directory {PLOTS_DIR}: {e}")
        return

    # 2. Read the data using pandas
    try:
        df = pd.read_csv(data_path)

        # Standardize the date column for plotting. Prioritize 'date' over 'timestamp'.
        if 'date' in df.columns:
            date_col = 'date'
        elif 'timestamp' in df.columns:
            date_col = 'timestamp'
        else:
            print(f"Error: Could not find a 'date' or 'timestamp' column in {data_path}")
            return
            
        df[date_col] = pd.to_datetime(df[date_col])
        
    except FileNotFoundError:
        print(f"Error: Data file not found at {data_path}")
        return
    except Exception as e:
        print(f"Error reading or parsing data file {data_path}: {e}")
        return
        
    if 'liquidation_volume' not in df.columns:
        print(f"Error: 'liquidation_volume' column not found in {data_path}")
        return

    df['liquidation_volume'] = pd.to_numeric(df['liquidation_volume'], errors='coerce')
    df.dropna(subset=['liquidation_volume'], inplace=True)
        
    print("Liquidation data loaded successfully. Generating plot...")

    # 3. Create the bar chart using matplotlib
    plt.figure(figsize=(14, 7))
    plt.bar(df[date_col], df['liquidation_volume'], label='Liquidation Volume', color='red', width=0.8)
    
    # 4. Customize the plot (titles, labels, grid, etc.)
    plt.title(f'Daily Liquidation Volume - {symbol} (Coinalyze)', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Liquidation Volume (USD)', fontsize=12)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    
    # 5. Save the plot to a file
    full_output_path = os.path.join(PLOTS_DIR, output_filename)
    try:
        plt.savefig(full_output_path)
        print(f"Plot saved successfully to {full_output_path}")
    except Exception as e:
        print(f"Error saving plot to {full_output_path}: {e}")
    finally:
        plt.close() 
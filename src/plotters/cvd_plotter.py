import os
import pandas as pd
import matplotlib.pyplot as plt

# Define a directory to save plots, relative to the project root
PLOTS_DIR = "plots"

def generate_cvd_plot(data_path: str, symbol: str):
    """
    Reads CVD data from a specified CSV file for a given symbol and generates a time series plot.

    Args:
        data_path (str): The full path to the input CSV data file.
        symbol (str): The asset symbol (e.g., 'BTCUSDT') being plotted.
    """
    output_filename = f"cvd_{symbol}_plot.png"
    print(f"Attempting to generate CVD plot for {symbol} from {data_path}...")

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
        
    if 'CVD' not in df.columns:
        print(f"Error: 'CVD' column not found in {data_path}")
        return

    # Ensure the CVD column is numeric, coercing errors
    df['CVD'] = pd.to_numeric(df['CVD'], errors='coerce')
    df.dropna(subset=['CVD'], inplace=True)
        
    print("Data loaded successfully. Generating plot...")

    # 3. Create the plot using matplotlib
    plt.figure(figsize=(14, 7))
    plt.plot(df[date_col], df['CVD'], label='CVD', color='blue')
    
    # 4. Customize the plot (titles, labels, grid, etc.)
    plt.title(f'Cumulative Volume Delta (CVD) - {symbol}', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('CVD', fontsize=12)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    plt.tight_layout() # Adjust layout to make room for labels
    
    # 5. Save the plot to a file
    full_output_path = os.path.join(PLOTS_DIR, output_filename)
    try:
        plt.savefig(full_output_path)
        print(f"Plot saved successfully to {full_output_path}")
    except Exception as e:
        print(f"Error saving plot to {full_output_path}: {e}")
    finally:
        plt.close() # Close the figure to free up memory

# Example of how you might call this from main.py:
if __name__ == '__main__':
    # This is for testing purposes. Assumes you run this file directly
    # and the data file exists at the specified relative path.
    # In the main app, you'd get the path from the collector or metadata.
    test_symbol = "BTCUSDT"
    cvd_data_path = os.path.join("..", "..", "data", "daily", f"cvd_{test_symbol}_binance.csv")
    if os.path.exists(cvd_data_path):
         generate_cvd_plot(data_path=cvd_data_path, symbol=test_symbol)
    else:
        print(f"Test run failed: Could not find data at {cvd_data_path}") 
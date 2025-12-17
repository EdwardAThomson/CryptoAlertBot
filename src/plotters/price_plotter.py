import os
import pandas as pd
import matplotlib.pyplot as plt

# Define a directory to save plots, relative to the project root
PLOTS_DIR = "plots"

def generate_price_plot(data_path: str, symbol: str):
    """
    Reads Price data from a specified CSV file for a given symbol and generates a time series plot.

    Args:
        data_path (str): The full path to the input CSV data file.
        symbol (str): The asset symbol (e.g., 'BTCUSDT') being plotted.
    """
    output_filename = f"price_{symbol}_plot.png"
    print(f"Attempting to generate Price plot for {symbol} from {data_path}...")

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
        
    # Check for a 'close' column, which is standard for price charts
    if 'close' not in df.columns:
        print(f"Error: 'close' column not found in {data_path}")
        return

    # Ensure the close column is numeric
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df.dropna(subset=['close'], inplace=True)
        
    print("Data loaded successfully. Generating plot...")

    # 3. Create the plot using matplotlib
    plt.figure(figsize=(14, 7))
    plt.plot(df[date_col], df['close'], label='Close Price', color='green')
    
    # 4. Customize the plot (titles, labels, grid, etc.)
    plt.title(f'Price - {symbol}', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Price (USD)', fontsize=12)
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

# Example of how you might call this from main.py:
# if __name__ == '__main__':
#     price_data_path = os.path.join("..", "..", "data", "daily", "price_BTCUSDT_binance.csv")
#     if os.path.exists(price_data_path):
#          generate_price_plot(data_path=price_data_path)
#     else:
#         print(f"Test run failed: Could not find data at {price_data_path}") 
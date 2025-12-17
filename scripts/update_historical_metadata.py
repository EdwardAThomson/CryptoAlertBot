import os
import pandas as pd
import json
import sys

# Add the project root to the Python path to allow importing from 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils import update_metadata_csv

CONFIG_PATH = "data/config.json"
DATA_DIR = "data/daily"

def run():
    """
    Scans for existing historical price data files and updates the metadata.csv accordingly.
    """
    print("--- Starting metadata update for existing historical price files ---")

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        assets = config.get("assets", [])
        if not assets:
            print("No assets found in config file. Nothing to update.")
            return
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing config file at {CONFIG_PATH}: {e}")
        return

    for symbol in assets:
        filepath = os.path.join(DATA_DIR, f"historical_price_{symbol}.csv")
        source_label = f"Historical Price_{symbol}"

        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath)
                if not df.empty and 'date' in df.columns:
                    print(f"Found data for {symbol}. Updating metadata...")
                    update_metadata_csv(source_label, df)
                    print(f"Successfully updated metadata for {source_label}.")
                else:
                    print(f"Skipping empty or invalid file for {symbol} at {filepath}.")
            except Exception as e:
                print(f"Could not process file for {symbol} at {filepath}: {e}")
        else:
            print(f"No historical data file found for {symbol} at {filepath}. Skipping.")

    print("\n--- Metadata update complete ---")

if __name__ == "__main__":
    run() 
import os
import csv
from datetime import date, datetime, timedelta
import requests
import pandas as pd
import json

# --- Constants ---
CONFIG_PATH = "data/config.json"
DATA_DIR = "data/daily"
METADATA_CSV_FILE_PATH = "data/metadata.csv"
METADATA_CSV_HEADERS = ["SourceLabel", "StartDate", "EndDate", "Filename", "Asset"]

COINALYZE_API_URL = "https://api.coinalyze.net/v1/liquidation-history"
COINALYZE_API_KEY = "79bdee54-7244-43bb-9382-7e7c961ed960"

# --- Symbol Mapping ---
# Coinalyze uses a different format. We map our standard symbols here.
SYMBOL_MAP = {
    "BTCUSDT": "BTCUSDT_PERP.A",
    "ETHUSDT": "ETHUSDT_PERP.A",
    "SOLUSDT": "SOLUSDT_PERP.A",
    "BNBUSDT": "BNBUSDT_PERP.A",
    "XRPUSDT": "XRPUSDT_PERP.A",
    "ADAUSDT": "ADAUSDT_PERP.A",
    "TRXUSDT": "TRXUSDT_PERP.A"
}

def get_liquidation_data_filepath(symbol: str) -> str:
    """Generates the standardized filepath for a given asset's liquidation data."""
    return os.path.join(DATA_DIR, f"liquidation_{symbol}_coinalyze.csv")

def get_liquidation_metadata(symbol: str) -> tuple[str | None, str | None, str]:
    """
    Reads the Coinalyze liquidation data CSV for a given symbol to find its start and end dates.
    """
    filepath = get_liquidation_data_filepath(symbol)
    filename = os.path.basename(filepath)
    
    if not os.path.exists(filepath):
        return None, None, filename

    try:
        df = pd.read_csv(filepath)
        if df.empty:
            return None, None, filename

        # Standardize column name to 'date'
        if 'timestamp' in df.columns and 'date' not in df.columns:
            df.rename(columns={'timestamp': 'date'}, inplace=True)

        if 'date' not in df.columns:
            return None, None, filename

        df['date'] = pd.to_datetime(df['date'])
        
        start_date_str = df['date'].min().date().isoformat()
        end_date_str = df['date'].max().date().isoformat()

        return start_date_str, end_date_str, filename

    except Exception as e:
        print(f"Error reading or processing liquidation data file {filepath}: {e}")
        return None, None, filename

def _update_metadata_csv(symbol: str, start_date: str | None, end_date: str | None, data_filename: str):
    """
    Updates or appends the asset-specific 'Liquidations' entry in metadata.csv.
    """
    source_label = f"Liquidations_{symbol}"
    start_date_to_save = start_date if start_date is not None else "--"
    end_date_to_save = end_date if end_date is not None else "--"

    new_row_data = {
        "SourceLabel": source_label,
        "StartDate": start_date_to_save,
        "EndDate": end_date_to_save,
        "Filename": data_filename,
        "Asset": symbol
    }

    df_metadata = None
    if os.path.exists(METADATA_CSV_FILE_PATH):
        try:
            df_metadata = pd.read_csv(METADATA_CSV_FILE_PATH)
        except pd.errors.EmptyDataError:
            df_metadata = pd.DataFrame(columns=METADATA_CSV_HEADERS)
    else:
        df_metadata = pd.DataFrame(columns=METADATA_CSV_HEADERS)

    if "Asset" not in df_metadata.columns:
        df_metadata["Asset"] = None

    existing_row_index = df_metadata[df_metadata["SourceLabel"] == source_label].index
    
    if not existing_row_index.empty:
        for col, value in new_row_data.items():
            df_metadata.loc[existing_row_index, col] = value
    else:
        new_df_entry = pd.DataFrame([new_row_data])
        df_metadata = pd.concat([df_metadata, new_df_entry], ignore_index=True)
    
    os.makedirs(os.path.dirname(METADATA_CSV_FILE_PATH), exist_ok=True)
    df_metadata.to_csv(METADATA_CSV_FILE_PATH, index=False, columns=METADATA_CSV_HEADERS)

def get_source_metadata_from_csv(source_label: str) -> tuple[str, str, str]:
    """
    Reads metadata.csv and returns the StartDate, EndDate, and Filename for a given label.
    """
    if not os.path.exists(METADATA_CSV_FILE_PATH):
        return "--", "--", "--"
    try:
        df_metadata = pd.read_csv(METADATA_CSV_FILE_PATH)
        if df_metadata.empty:
            return "--", "--", "--"
        
        source_row = df_metadata[df_metadata["SourceLabel"] == source_label]
        
        if not source_row.empty:
            start_date = source_row["StartDate"].iloc[0]
            end_date = source_row["EndDate"].iloc[0]
            filename = source_row["Filename"].iloc[0]
            return str(start_date), str(end_date), str(filename)
        else:
            return "--", "--", "--"
    except Exception:
        return "--", "--", "--"

def update_liquidation_data(symbol: str):
    """
    Handles liquidation data updates from the Coinalyze API for a SINGLE ASSET.
    """
    coinalyze_symbol = SYMBOL_MAP.get(symbol)
    if not coinalyze_symbol:
        print(f"Warning: No Coinalyze symbol mapping found for '{symbol}'. Skipping.")
        return

    print(f"\n--- Updating Liquidation data for {symbol} (using {coinalyze_symbol}) ---")

    filepath = get_liquidation_data_filepath(symbol)
    _, current_end_date_str, _ = get_liquidation_metadata(symbol)
    
    end_time = datetime.now()
    if current_end_date_str and current_end_date_str != '--':
        try:
            start_time = datetime.strptime(current_end_date_str, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            print(f"Warning: Could not parse end date '{current_end_date_str}'. Fetching last year.")
            start_time = end_time - timedelta(days=365)
    else:
        print("No existing liquidation data found. Fetching data for the last year.")
        start_time = end_time - timedelta(days=365)
    
    if start_time.date() >= end_time.date():
        print("Liquidation data is already up to date.")
        # Even if up-to-date, ensure metadata is correct
        new_start, new_end, filename = get_liquidation_metadata(symbol)
        _update_metadata_csv(symbol, new_start, new_end, filename)
        return

    from_ts = int(start_time.timestamp())
    to_ts = int(end_time.timestamp())

    params = {"symbols": coinalyze_symbol, "interval": "daily", "from": from_ts, "to": to_ts, "convert_to_usd": "true"}
    headers = {"api-key": COINALYZE_API_KEY}

    try:
        print(f"Fetching from Coinalyze for {symbol} from {start_time.date()} to {end_time.date()}")
        response = requests.get(COINALYZE_API_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status()

        data = response.json()
        if not data or not isinstance(data, list) or not data[0].get("history"):
            print("No new liquidation data returned from Coinalyze API.")
            # Even if no new data, ensure metadata is correct
            new_start, new_end, filename = get_liquidation_metadata(symbol)
            _update_metadata_csv(symbol, new_start, new_end, filename)
            return

        history = data[0].get("history", [])
        if not history:
            print("No new liquidation history in Coinalyze response.")
            new_start, new_end, filename = get_liquidation_metadata(symbol)
            _update_metadata_csv(symbol, new_start, new_end, filename)
            return
            
        df_new = pd.DataFrame([
            # Core Fix: Ensure we are only using the date part of the timestamp
            {'date': datetime.fromtimestamp(e["t"]).date(), 'liquidation_volume': e["l"]} for e in history
        ])

        if df_new.empty:
            print("No new records processed from response.")
        else:
            print(f"Fetched {len(df_new)} new records.")

        if os.path.exists(filepath):
            df_existing = pd.read_csv(filepath)
            
            # Standardize column for existing data
            if 'timestamp' in df_existing.columns and 'date' not in df_existing.columns:
                df_existing.rename(columns={'timestamp': 'date'}, inplace=True)
            
            # Ensure the date column is just a date object for proper merging
            df_existing['date'] = pd.to_datetime(df_existing['date']).dt.date

            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.drop_duplicates(subset=['date'], keep='last', inplace=True)
            df_combined.sort_values(by='date', inplace=True)
            df_combined.to_csv(filepath, index=False)
            print(f"Saved/updated data to {filepath}")
        elif not df_new.empty:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df_new.to_csv(filepath, index=False)
            print(f"Saved new data to {filepath}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching liquidation data from Coinalyze API: {e}")
        return
    except Exception as e:
        print(f"An error occurred while processing Coinalyze data: {e}")
        return
        
    final_start, final_end, filename = get_liquidation_metadata(symbol)
    _update_metadata_csv(symbol, final_start, final_end, filename)

def update_all_liquidation_data():
    """
    Main entry point. Reads config and updates liquidation data for all assets.
    """
    print("\n======================================")
    print("Starting liquidation data update for all configured assets...")
    
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
        
    for asset_symbol in assets:
        update_liquidation_data(symbol=asset_symbol)
        
    print("\nAll liquidation data updates complete.")
    print("======================================\n")
import os
from datetime import date, datetime, timedelta
import requests
import pandas as pd
import csv
import json

# --- Constants for Open Interest Collector ---
CONFIG_PATH = "data/config.json"
DATA_DIR = "data/daily"
METADATA_CSV_FILE_PATH = "data/metadata.csv"
METADATA_CSV_HEADERS = ["SourceLabel", "StartDate", "EndDate", "Filename", "Asset"]

BINANCE_FUTURES_API_URL = "https://fapi.binance.com/futures/data/openInterestHist"
DEFAULT_PERIOD = "1d"

def get_oi_data_filepath(symbol: str) -> str:
    """Generates the standardized filepath for a given asset's Open Interest data."""
    return os.path.join(DATA_DIR, f"open_interest_{symbol}_binance.csv")

def get_oi_metadata(symbol: str) -> tuple[str | None, str | None, str]:
    """
    Reads the primary OI data CSV for a given symbol to find its start and end dates.
    """
    filepath = get_oi_data_filepath(symbol)
    filename = os.path.basename(filepath)
    
    if not os.path.exists(filepath):
        return None, None, filename

    dates_in_file: list[date] = []

    try:
        with open(filepath, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)

            if not header:
                return None, None, filename
            
            for row in reader:
                if row and row[0]:
                    try:
                        date_obj = datetime.strptime(row[0], '%Y-%m-%d').date()
                        dates_in_file.append(date_obj)
                    except (ValueError, IndexError):
                        continue
            
            if not dates_in_file:
                return None, None, filename

            start_date_str = min(dates_in_file).isoformat()
            end_date_str = max(dates_in_file).isoformat()

            return start_date_str, end_date_str, filename

    except Exception as e:
        print(f"Error reading or processing OI data file {filepath}: {e}")
        return None, None, filename

def _update_metadata_csv(symbol: str, start_date: str | None, end_date: str | None, data_filename: str):
    """
    Updates or appends the asset-specific 'Open Interest' entry in metadata.csv.
    """
    source_label = f"Open Interest_{symbol}"
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

def update_oi_data(symbol: str, period: str = DEFAULT_PERIOD, limit: int = 500):
    """
    Handles Open Interest data updates for a SINGLE ASSET.
    """
    print(f"\n--- Updating Open Interest data for {symbol} ---")
    
    filepath = get_oi_data_filepath(symbol)
    current_start_date_str, current_end_date_str, filename = get_oi_metadata(symbol)

    if current_end_date_str:
        print(f"Current data range: {current_start_date_str} to {current_end_date_str}")
    else:
        print("No existing valid data range found. Will perform initial fetch.")

    start_time_ms = None
    requested_start_date = None
    if current_end_date_str:
        try:
            last_date = datetime.strptime(current_end_date_str, '%Y-%m-%d').date()
            start_fetch_date = last_date + timedelta(days=1)
            requested_start_date = start_fetch_date
            start_time_ms = int(datetime.combine(start_fetch_date, datetime.min.time()).timestamp() * 1000)
            print(f"Fetching new data from {start_fetch_date.isoformat()} onwards.")
        except ValueError:
            print(f"Warning: Could not parse end date: {current_end_date_str}. Fetching default range.")

    api_params = { "symbol": symbol, "period": period, "limit": limit }
    if start_time_ms:
        api_params["startTime"] = start_time_ms

    try:
        response = requests.get(BINANCE_FUTURES_API_URL, params=api_params, timeout=10)
        response.raise_for_status()
        
        new_data = response.json()
        if not new_data:
            print("No new Open Interest data available from API.")
            _update_metadata_csv(symbol, current_start_date_str, current_end_date_str, filename)
            return

        df_new = pd.DataFrame(new_data)
        
        df_new["timestamp"] = pd.to_datetime(df_new["timestamp"], unit="ms").dt.strftime('%Y-%m-%d')
        df_to_save = df_new[["timestamp", "sumOpenInterest", "sumOpenInterestValue"]].copy()

        numeric_cols = ["sumOpenInterest", "sumOpenInterestValue"]
        for col in numeric_cols:
            df_to_save[col] = pd.to_numeric(df_to_save[col], errors="coerce")
        df_to_save.dropna(inplace=True)

        # --- Safeguard: Detect unrecoverable gaps due to limited API history ---
        if requested_start_date is not None and not df_to_save.empty:
            try:
                api_first_date = datetime.strptime(df_to_save["timestamp"].min(), "%Y-%m-%d").date()
                gap_days = (api_first_date - requested_start_date).days
                if gap_days > 1:
                    print(
                        f"WARNING: Open Interest data gap detected for {symbol}: expected data from "
                        f"{requested_start_date.isoformat()} based on existing file, but API only returned data from "
                        f"{api_first_date.isoformat()} onward ({gap_days} missing days that cannot be backfilled). "
                        "Consider archiving current data and resetting OI files if you need a clean series."
                    )
            except Exception as e:
                print(f"Warning: Could not validate Open Interest date alignment for {symbol}: {e}")

        print(f"Fetched {len(df_to_save)} new records.")

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            df_existing = pd.read_csv(filepath)
            df_existing['timestamp'] = df_existing['timestamp'].astype(str)
            
            df_combined = pd.concat([df_existing, df_to_save], ignore_index=True)
            df_combined.drop_duplicates(subset=["timestamp"], keep="last", inplace=True)
            
            df_combined['sort_key'] = pd.to_datetime(df_combined['timestamp'])
            df_combined.sort_values(by="sort_key", inplace=True)
            df_combined.drop(columns=['sort_key'], inplace=True)

            df_combined.to_csv(filepath, index=False)
        else:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df_to_save.to_csv(filepath, index=False)
            
        print(f"Successfully saved data to {filepath}.")

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return
    except Exception as e:
        print(f"An error occurred during Open Interest data update: {e}")
        return

    final_start_date, final_end_date, actual_filename = get_oi_metadata(symbol)
    if actual_filename:
        _update_metadata_csv(symbol, final_start_date, final_end_date, actual_filename)

def update_all_oi_data():
    """
    Main entry point. Reads config and updates Open Interest data for all assets.
    """
    print("\n======================================")
    print("Starting Open Interest data update for all configured assets...")
    
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
        update_oi_data(symbol=asset_symbol)
        
    print("\nAll Open Interest data updates complete.")
    print("======================================\n")

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
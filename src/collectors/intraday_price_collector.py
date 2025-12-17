import os
import time
from datetime import date, datetime, timedelta, timezone
import pandas as pd
import ccxt
import json

# --- Constants ---
CONFIG_PATH = "data/config.json"
DATA_DIR = "data/intraday"
TARGET_HOUR_UTC = 9
ASSET_SYMBOL = "BTCUSDT"  # Default asset for testing

def get_intraday_price_filepath(symbol: str) -> str:
    """
    Generates the standardized filepath for a given asset's intraday price data.
    Ensures the data directory exists.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, f"price_{TARGET_HOUR_UTC:02d}00_{symbol}.csv")

def _get_last_date_from_csv(filepath: str) -> date | None:
    """
    Reads the intraday price CSV and returns the last date recorded.
    Returns None if the file doesn't exist or is empty.
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        return None
    try:
        df = pd.read_csv(filepath, header=0)
        if 'date' not in df.columns or df.empty:
            return None
        last_date_str = df['date'].iloc[-1]
        return datetime.strptime(last_date_str, '%Y-%m-%d').date()
    except Exception as e:
        print(f"Error reading last date from {filepath}: {e}")
        return None

def _fetch_single_hour_price(exchange, symbol: str, dt_utc: datetime) -> float | None:
    """
    Fetches the OHLCV candle for a single specific hour and returns the opening price.
    """
    try:
        # Convert the target datetime to a milliseconds timestamp for the API
        timestamp_ms = int(dt_utc.timestamp() * 1000)
        
        # Rate limit to avoid being blocked by the API
        time.sleep(exchange.rateLimit / 1000)
        
        # Fetch 1 candle starting from the specified timestamp
        ohlcv = exchange.fetch_ohlcv(symbol, '1h', since=timestamp_ms, limit=1)
        
        if not ohlcv:
            print(f"No data returned for {symbol} at {dt_utc}")
            return None
        
        # The returned data is [timestamp, open, high, low, close, volume]
        # The 'open' price is the price at the start of the hour.
        return ohlcv[0][1]
        
    except ccxt.NetworkError as e:
        print(f"A network error occurred: {e}")
    except ccxt.ExchangeError as e:
        print(f"An exchange error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during fetch: {e}")
    return None

def update_intraday_price_data(symbol: str):
    """
    Fetches and updates the 09:00 UTC price for a given asset.
    - On first run, it backfills the last 30 days.
    - On subsequent runs, it fills in missing days.
    """
    print(f"\n--- Updating Intraday (09:00 UTC) Price for {symbol} ---")
    
    filepath = get_intraday_price_filepath(symbol)
    last_recorded_date = _get_last_date_from_csv(filepath)
    
    today = datetime.now(timezone.utc).date()
    start_fetch_date: date

    if last_recorded_date is None:
        print("No existing data found. Backfilling last 30 days.")
        start_fetch_date = today - timedelta(days=30)
    else:
        print(f"Last recorded date is {last_recorded_date}. Fetching new data.")
        start_fetch_date = last_recorded_date + timedelta(days=1)

    if start_fetch_date > today:
        print("Data is already up to date. Nothing to do.")
        return

    print(f"Fetching data from {start_fetch_date} to {today}...")

    exchange = ccxt.binance()
    new_records = []

    current_date = start_fetch_date
    while current_date <= today:
        # Define the target datetime in UTC
        target_dt = datetime(
            current_date.year, 
            current_date.month, 
            current_date.day, 
            TARGET_HOUR_UTC, 
            tzinfo=timezone.utc
        )
        
        # Fetch the price for that specific hour
        price = _fetch_single_hour_price(exchange, symbol, target_dt)
        
        if price is not None:
            new_records.append({'date': current_date.isoformat(), 'price': price})
            print(f"  Successfully fetched price for {current_date}: {price}")
        else:
            print(f"  Failed to fetch price for {current_date}")
            
        current_date += timedelta(days=1)

    if not new_records:
        print("No new records were fetched.")
        return

    # Save the new records to the CSV
    df_new = pd.DataFrame(new_records)
    
    # If file doesn't exist, write with header. Otherwise, append without header.
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0
    df_new.to_csv(filepath, mode='a', header=not file_exists, index=False)
    
    print(f"\nSuccessfully saved {len(new_records)} new records to {filepath}.")

def update_all_intraday_price_data():
    """
    Main entry point. Reads the config file and updates intraday price data for all assets.
    """
    print("\n======================================")
    print(f"Starting intraday ({TARGET_HOUR_UTC:02d}:00 UTC) price update for all configured assets...")
    
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
        update_intraday_price_data(symbol=asset_symbol)
        
    print(f"\nAll intraday ({TARGET_HOUR_UTC:02d}:00 UTC) price updates complete.")
    print("======================================\n")

if __name__ == '__main__':
    """
    This allows the script to be run directly for testing and data collection.
    """
    update_all_intraday_price_data() 
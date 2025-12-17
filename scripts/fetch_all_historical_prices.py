import os
import json
import pandas as pd
import ccxt
import time
import sys
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.utils import update_metadata_csv

CONFIG_PATH = "data/config.json"
DATA_DIR = "data/daily"

# Define start dates for specific assets
ASSET_START_DATES = {
    'BTCUSDT': '2012-01-01T00:00:00Z',  # Bitcoin's early days
    'ETHUSDT': '2015-08-01T00:00:00Z',  # Ethereum's launch
    # Add more specific start dates for other assets as needed
}
DEFAULT_START_DATE = '2017-01-01T00:00:00Z'  # Default for other assets

def fetch_historical_data(exchange, symbol, timeframe='1d'):
    """
    Fetch ALL historical OHLCV data from the appropriate start date for each asset.
    """
    print(f"Fetching all historical data for {symbol}...")
    all_data = []
    
    # Get the appropriate start date for this asset
    start_date = ASSET_START_DATES.get(symbol, DEFAULT_START_DATE)
    print(f"Starting from {start_date}")
    
    current_since = exchange.parse8601(start_date)
    limit = 1000  # Maximum allowed by most exchanges
    
    while True:
        try:
            # Fetch a chunk of data
            chunk = exchange.fetch_ohlcv(
                symbol,
                timeframe,
                since=current_since,
                limit=limit
            )
            
            if not chunk:
                break
                
            all_data.extend(chunk)
            print(f"Fetched {len(chunk)} records, total: {len(all_data)}")
            
            # Update since timestamp for next chunk
            current_since = chunk[-1][0] + 1
            
            # If we got less than the limit, we've reached the end
            if len(chunk) < limit:
                break
                
            # Add a small delay to avoid rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching data chunk for {symbol}: {e}")
            break
    
    if not all_data:
        return pd.DataFrame()
        
    # Convert the list of lists to a DataFrame
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
    return df

def main():
    print("Starting historical price data fetch...")
    
    # Create data directory if it doesn't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Initialize exchange
    exchange = ccxt.binance()
    
    # Load assets from config
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        assets = config.get('assets', [])
        if not assets:
            print("No assets found in config file.")
            return
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading config file: {e}")
        return
    
    # Process each asset
    for symbol in assets:
        print(f"\nProcessing {symbol}...")
        
        # Fetch all historical data
        df = fetch_historical_data(exchange, symbol)
        
        if df.empty:
            print(f"No data found for {symbol}")
            continue
            
        # Save to file
        output_filename = os.path.join(DATA_DIR, f"historical_price_{symbol}.csv")
        df.to_csv(output_filename, index=False)
        print(f"Saved {len(df)} records to {output_filename}")
        
        # Update metadata
        source_label = f"Historical Price_{symbol}"
        update_metadata_csv(source_label, df)
        print(f"Updated metadata for {source_label}")
        
        # Add a delay between assets to avoid rate limits
        time.sleep(1)
    
    print("\nHistorical price data fetch complete!")

if __name__ == "__main__":
    main() 
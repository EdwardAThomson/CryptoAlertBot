import ccxt
import pandas as pd
import os
import json
from datetime import datetime
from src.utils import get_metadata_from_csv, update_metadata_csv
import time

class _HistoricalPriceCollector:
    """Internal class to handle historical price collection logic."""
    def __init__(self, data_path='data/daily', config_path='data/config.json'):
        self.data_path = data_path
        self.config_path = config_path
        self.assets = self._load_assets()
        self.exchange = ccxt.binance()

    def _load_assets(self):
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            # The 'assets' in config are a list of strings, not dicts.
            return config.get('assets', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing config file: {e}")
            return []

    def fetch_historical_data(self, symbol, since=None, limit=1000, timeframe='1d'):
        """
        Fetch historical OHLCV data in chunks to get more historical data.
        """
        all_data = []
        current_since = since
        
        if current_since is None:
            # Start from 2017 (Bitcoin's major bull run)
            current_since = self.exchange.parse8601('2017-01-01T00:00:00Z')
        
        while True:
            try:
                # Fetch a chunk of data
                chunk = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=current_since,
                    limit=limit
                )
                
                if not chunk:
                    break
                    
                all_data.extend(chunk)
                
                # Update since timestamp for next chunk
                # Add 1 millisecond to avoid duplicate data
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

    def _generate_weekly_data(self, symbol: str):
        """Resamples the daily historical data to weekly OHLCV data."""
        daily_filepath = get_historical_price_data_filepath(symbol)
        if not os.path.exists(daily_filepath):
            print(f"Cannot generate weekly data for {symbol}: daily file not found.")
            return

        print(f"  - Generating weekly data for {symbol}...")
        try:
            df = pd.read_csv(daily_filepath)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # Define resampling aggregation rules
            agg_rules = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }

            weekly_df = df.resample('W-MON').agg(agg_rules).dropna()
            weekly_df.index.name = 'date'

            # Ensure the output directory exists
            weekly_data_path = 'data/weekly'
            os.makedirs(weekly_data_path, exist_ok=True)
            
            output_filename = os.path.join(weekly_data_path, f"historical_price_{symbol}_weekly.csv")
            weekly_df.to_csv(output_filename)
            print(f"    - Successfully saved weekly data to {output_filename}")

        except Exception as e:
            print(f"    - Error generating weekly data for {symbol}: {e}")

    def run_update(self):
        print("Starting historical price data update...")
        for symbol in self.assets:
            print(f"Fetching data for {symbol}...")
            
            output_filename = os.path.join(self.data_path, f"historical_price_{symbol}.csv")
            source_label = f"Historical Price_{symbol}"
            
            since = None
            existing_df = pd.DataFrame()
            if os.path.exists(output_filename):
                existing_df = pd.read_csv(output_filename)
                if not existing_df.empty:
                    existing_df['date'] = pd.to_datetime(existing_df['date'])
                    last_date = existing_df['date'].max()
                    since = self.exchange.parse8601(last_date.strftime('%Y-%m-%d %H:%M:%S'))
                    print(f"Found existing data for {symbol}. Fetching new data since {last_date.date()}.")
            else:
                 print(f"No existing data for {symbol}. Fetching all available recent data.")

            try:
                new_data_df = self.fetch_historical_data(symbol, since=since)
                if not new_data_df.empty:
                    if not existing_df.empty:
                        existing_df['date'] = pd.to_datetime(existing_df['date']).dt.date
                    new_data_df['date'] = pd.to_datetime(new_data_df['date']).dt.date

                    combined_df = pd.concat([existing_df, new_data_df]).drop_duplicates(subset=['date'], keep='last')
                    combined_df.sort_values(by='date', inplace=True)
                    combined_df.to_csv(output_filename, index=False)
                    print(f"Successfully updated and saved data for {symbol} to {output_filename}")

                    update_metadata_csv(source_label, combined_df)
                    
                    # Generate weekly data after updating daily data
                    self._generate_weekly_data(symbol)

            except Exception as e:
                print(f"Could not fetch or process data for {symbol}: {e}")
        print("Historical price data update finished.")

# --- Public Functions ---

def get_source_metadata_from_csv(source: str):
    """Public function to get metadata for this collector."""
    return get_metadata_from_csv(source)

def get_historical_price_data_filepath(symbol: str) -> str:
    """Public function to get the filepath for historical price data."""
    return os.path.join('data/daily', f"historical_price_{symbol}.csv")

def get_weekly_historical_price_data_filepath(symbol: str) -> str:
    """Public function to get the filepath for weekly historical price data."""
    return os.path.join('data/weekly', f"historical_price_{symbol}_weekly.csv")

def update_all_historical_data():
    """Public function to run the collector update process."""
    collector = _HistoricalPriceCollector()
    collector.run_update()

if __name__ == '__main__':
    update_all_historical_data() 
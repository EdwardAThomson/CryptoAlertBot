import pandas as pd
import os
from datetime import date

METADATA_FILE = "data/metadata.csv"
METADATA_COLUMNS = ["SourceLabel", "StartDate", "EndDate", "Filename", "Asset"]

def get_metadata_from_csv(source: str, metadata_file: str = METADATA_FILE):
    """
    Given a source name, return the start date, end date, and filename from the metadata CSV.
    Uses the standardized column headers.
    """
    try:
        df = pd.read_csv(metadata_file)
        # Ensure date columns are parsed correctly, even if they contain "--"
        df['StartDate'] = pd.to_datetime(df['StartDate'], errors='coerce').dt.date
        df['EndDate'] = pd.to_datetime(df['EndDate'], errors='coerce').dt.date

        record = df[df['SourceLabel'] == source]
        if not record.empty:
            start_date = record['StartDate'].iloc[0]
            end_date = record['EndDate'].iloc[0]
            filename = record['Filename'].iloc[0]
            # Format for display, handling NaT (Not a Time) from coerce
            start_str = start_date.isoformat() if pd.notna(start_date) else "--"
            end_str = end_date.isoformat() if pd.notna(end_date) else "--"
            return start_str, end_str, filename
    except FileNotFoundError:
        pass  # Will return the default "--" values
    except Exception as e:
        print(f"Error reading metadata for {source}: {e}")
    
    return "--", "--", "--"


def update_metadata_csv(source_name: str, df: pd.DataFrame, metadata_file: str = METADATA_FILE):
    """
    Updates the metadata CSV file with the start and end dates for a given source.
    Uses the standardized column headers.
    """
    if df.empty or 'date' not in df.columns:
        return

    df['date'] = pd.to_datetime(df['date'])
    
    start_date = df['date'].min().date()
    end_date = df['date'].max().date()
    asset = ""
    
    # --- Determine Filename and Asset from source_name ---
    parts = source_name.split('_')
    if len(parts) > 1:
        # Assumes format like "Price_BTCUSDT", "CVD_ETHUSDT", etc.
        asset = parts[-1]
    
    filename = f"{source_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}.csv" # Default fallback

    if "price" in source_name.lower() and "historical" not in source_name.lower():
        filename = f"price_{asset}.csv"
    elif "cvd" in source_name.lower():
        filename = f"cvd_{asset}_binance.csv"
    elif "open interest" in source_name.lower():
        filename = f"open_interest_{asset}_coinalyze.csv"
    elif "liquidations" in source_name.lower():
        filename = f"liquidations_{asset}_coinalyze.csv"
    elif "historical price" in source_name.lower():
        filename = f"historical_price_{asset}.csv"

    try:
        if os.path.exists(metadata_file):
            meta_df = pd.read_csv(metadata_file)
        else:
            meta_df = pd.DataFrame(columns=METADATA_COLUMNS)

        # Ensure all standard columns exist
        for col in METADATA_COLUMNS:
            if col not in meta_df.columns:
                meta_df[col] = None

        record_index = meta_df[meta_df['SourceLabel'] == source_name].index

        new_record = {
            'SourceLabel': source_name,
            'StartDate': start_date.isoformat(),
            'EndDate': end_date.isoformat(),
            'Filename': filename,
            'Asset': asset
        }

        if not record_index.empty:
            meta_df.loc[record_index, list(new_record.keys())] = list(new_record.values())
        else:
            meta_df = pd.concat([meta_df, pd.DataFrame([new_record])], ignore_index=True)

        meta_df.to_csv(metadata_file, index=False)

    except Exception as e:
        print(f"Failed to update metadata for {source_name}: {e}") 
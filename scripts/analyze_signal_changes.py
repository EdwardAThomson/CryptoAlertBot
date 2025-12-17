#!/usr/bin/env python3
"""
Analysis script to compare old vs new signal generation logic.
Shows what signals would have been captured with the graduated threshold approach.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.analyzers.eight_state_analyzer import generate_signals
from src.collectors.historical_price_collector import get_historical_price_data_filepath
from src.collectors.oi_collector import get_oi_data_filepath
from src.collectors.cvd_collector import get_cvd_data_filepath

def analyze_signal_changes(symbol: str = "BTCUSDT", days_back: int = 30):
    """
    Analyze how the new graduated threshold logic would have affected signals
    over the past N days compared to the old fixed threshold.
    """
    print(f"\n=== Signal Analysis for {symbol} (Last {days_back} days) ===")
    
    # Define paths
    price_path = get_historical_price_data_filepath(symbol)
    oi_path = get_oi_data_filepath(symbol)
    cvd_path = get_cvd_data_filepath(symbol)
    
    # Column mapping
    column_map = {
        "price": "close",
        "oi": "sumOpenInterestValue", 
        "cvd": "CVD"
    }
    
    # Check if all data files exist
    if not all(os.path.exists(p) for p in [price_path, oi_path, cvd_path]):
        print("❌ Missing required data files:")
        if not os.path.exists(price_path): print(f"  - Missing: {price_path}")
        if not os.path.exists(oi_path): print(f"  - Missing: {oi_path}")
        if not os.path.exists(cvd_path): print(f"  - Missing: {cvd_path}")
        return
    
    # Generate signals with new logic
    print("\n1. Generating signals with NEW graduated threshold logic...")
    generate_signals(price_path, oi_path, cvd_path, symbol, column_map)
    
    # Read the generated signals
    signals_path = f"data/analysis/signals_{symbol}.csv"
    if not os.path.exists(signals_path):
        print(f"❌ Signals file not found at {signals_path}")
        return
        
    df = pd.read_csv(signals_path, parse_dates=['date'])
    
    # Filter to last N days
    cutoff_date = datetime.now() - timedelta(days=days_back)
    df_recent = df[df['date'] >= cutoff_date].copy()
    
    if df_recent.empty:
        print(f"❌ No recent data found for the last {days_back} days")
        return
    
    print(f"\n2. Analysis Results ({len(df_recent)} days from {df_recent['date'].min().strftime('%Y-%m-%d')} to {df_recent['date'].max().strftime('%Y-%m-%d')}):")
    
    # Show signal distribution
    print(f"\n📊 Signal Distribution:")
    signal_counts = df_recent['state'].value_counts()
    for signal, count in signal_counts.items():
        percentage = (count / len(df_recent)) * 100
        print(f"  {signal}: {count} days ({percentage:.1f}%)")
    
    # Show signals that were preserved vs compressed
    if 'original_state' in df_recent.columns:
        print(f"\n🔍 Compression Analysis:")
        
        # Count compressions
        compressed = df_recent[df_recent['state'] == 'Compression']
        preserved_strong = df_recent[
            (df_recent['original_state'].isin(['Bullish Trending', 'Bearish Trending'])) &
            (df_recent['state'] != 'Compression')
        ]
        
        print(f"  Total compressed signals: {len(compressed)} days")
        print(f"  Strong signals preserved: {len(preserved_strong)} days")
        
        if len(compressed) > 0:
            print(f"\n  📉 Signals that were compressed:")
            compressed_summary = compressed['original_state'].value_counts()
            for original, count in compressed_summary.items():
                print(f"    {original}: {count} days")
        
        if len(preserved_strong) > 0:
            print(f"\n  💪 Strong signals that were preserved:")
            for _, row in preserved_strong.iterrows():
                vol = row.get('realized_vol_10d_percentile', 'N/A')
                print(f"    {row['date'].strftime('%Y-%m-%d')}: {row['state']} (vol: {vol}%)")
    
    # Show recent signal transitions
    print(f"\n📈 Recent Signal Timeline:")
    print("Date       | Price    | Final Signal        | Original Signal     | Vol%")
    print("-" * 75)
    
    for _, row in df_recent.tail(10).iterrows():
        date_str = row['date'].strftime('%Y-%m-%d')
        price_str = f"${row['close']:,.0f}"
        final_signal = row['state']
        original_signal = row.get('original_state', 'N/A')
        vol_pct = row.get('realized_vol_10d_percentile', 'N/A')
        
        # Add emoji indicators
        if final_signal == 'Bullish Trending':
            emoji = "🚀"
        elif final_signal == 'Bearish Trending':
            emoji = "📉"
        elif final_signal == 'Compression':
            emoji = "😴"
        elif 'Bullish' in final_signal:
            emoji = "📈"
        elif 'Bearish' in final_signal:
            emoji = "📊"
        else:
            emoji = "❓"
            
        print(f"{date_str} | {price_str:>8} | {emoji} {final_signal:<15} | {original_signal:<15} | {vol_pct}")
    
    # Highlight key insights
    print(f"\n💡 Key Insights:")
    
    # Check for missed bull moves
    strong_bullish = df_recent[df_recent['state'] == 'Bullish Trending']
    if len(strong_bullish) > 0:
        print(f"  ✅ {len(strong_bullish)} 'Bullish Trending' signals captured")
        latest_bullish = strong_bullish.iloc[-1]
        print(f"     Most recent: {latest_bullish['date'].strftime('%Y-%m-%d')} at ${latest_bullish['close']:,.0f}")
    
    # Check for recent price movements
    if len(df_recent) > 1:
        price_change = ((df_recent['close'].iloc[-1] / df_recent['close'].iloc[0]) - 1) * 100
        print(f"  📊 Price change over period: {price_change:+.1f}%")
    
    return df_recent

def compare_thresholds(symbol: str = "BTCUSDT"):
    """
    Compare what would happen with different threshold values.
    """
    print(f"\n=== Threshold Sensitivity Analysis for {symbol} ===")
    
    signals_path = f"data/analysis/signals_{symbol}.csv"
    if not os.path.exists(signals_path):
        print(f"❌ Run analyze_signal_changes() first to generate signals")
        return
    
    df = pd.read_csv(signals_path, parse_dates=['date'])
    
    if 'original_state' not in df.columns:
        print("❌ No original_state column found - run with new analyzer first")
        return
    
    # Filter to last 30 days
    cutoff_date = datetime.now() - timedelta(days=30)
    df_recent = df[df['date'] >= cutoff_date].copy()
    
    print(f"\nTesting different thresholds on last 30 days of data:")
    
    thresholds_to_test = [15, 20, 25, 30, 35, 40, 45, 50]
    
    for threshold in thresholds_to_test:
        # Simulate compression with this threshold
        if 'realized_vol_10d_percentile' in df_recent.columns:
            would_compress = df_recent['realized_vol_10d_percentile'] < threshold
            compressed_count = would_compress.sum()
            strong_signals_compressed = df_recent[
                would_compress & 
                df_recent['original_state'].isin(['Bullish Trending', 'Bearish Trending'])
            ]
            
            print(f"  Threshold {threshold:2d}%: {compressed_count:2d} compressed, {len(strong_signals_compressed):2d} strong signals lost")

if __name__ == "__main__":
    # Run the analysis
    symbol = "BTCUSDT"
    
    print("🔬 Analyzing Signal Generator Changes")
    print("=" * 50)
    
    # Main analysis
    recent_data = analyze_signal_changes(symbol, days_back=30)
    
    # Threshold sensitivity
    compare_thresholds(symbol)
    
    print(f"\n✅ Analysis complete! Check the results above.")
    print(f"📁 Detailed signals saved to: data/analysis/signals_{symbol}.csv") 
#!/usr/bin/env python3
"""
Quick script to test the summary table generation without triggering LLM calls.
This helps debug the signal strength logic and market tone determination.
"""

import pandas as pd
import os
import json
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.reporters.markdown_reporter import (
    _get_latest_regime_and_persistence,
    _get_latest_instability,
    _get_latest_volatility_metrics,
    _get_signal_strength_summary,
    _get_signal_detail,
    _colorize_text
)

def test_summary_table():
    """Generate just the summary table for testing."""
    
    # Load asset list from config
    config_path = "data/config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        assets = config.get("assets", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading config file: {e}")
        return

    print("## Market Summary Test\n")
    print("*Signal Strength: 🚀 = Bull Trend, 📈 = Bull Bias, 🔻 = Bear Trend, 📉 = Bear Bias, ➿ = Mixed")
    print("✅ = Active Market, 💤 = Quiet Market\n")
    print("| Asset   | Market Phase | Days in Phase | Signal Detail | Strength | Vol% | Liquidations | Sharpe (20d) |")
    print("|:--------|:---------------|:----:|:--------------|:---------|:----:|:------------|:-------------|")

    analysis_dir = "data/analysis"
    
    for symbol in assets:
        signals_path = os.path.join(analysis_dir, f"signals_{symbol}.csv")
        instability_path = os.path.join(analysis_dir, f"instability_{symbol}.csv")
        volatility_path = os.path.join(analysis_dir, f"volatility_{symbol}.csv")
        
        # Get all the data
        regime, persistence = _get_latest_regime_and_persistence(signals_path)
        instability = _get_latest_instability(instability_path)
        volatility_metrics = _get_latest_volatility_metrics(volatility_path)
        signal_strength_indicator, vol_pct = _get_signal_strength_summary(signals_path)
        signal_detail = _get_signal_detail(signals_path)
        
        # Format metrics
        sharpe = f"{volatility_metrics.get('sharpe', 'N/A'):.2f}" if volatility_metrics.get('sharpe') is not None else 'N/A'
        
        # Print the row
        print(f"| {symbol} | {_colorize_text(regime)} | {persistence} | {signal_detail} | {signal_strength_indicator} | {vol_pct} | {_colorize_text(instability)} | {sharpe} |")
        
        # Also print debug info for XRP specifically
        if symbol == "XRPUSDT":
            print(f"\n--- DEBUG INFO FOR {symbol} ---")
            if os.path.exists(signals_path):
                df = pd.read_csv(signals_path, parse_dates=['date'])
                if not df.empty:
                    latest = df.iloc[-1]
                    print(f"Current state: {latest['state']}")
                    print(f"Original state: {latest.get('original_state', 'N/A')}")
                    print(f"Volatility: {latest.get('realized_vol_10d_percentile', 'N/A')}%")
                    print(f"Signal strength indicator: {signal_strength_indicator}")
                    print(f"Vol percentage: {vol_pct}")
            print("--- END DEBUG ---\n")

if __name__ == '__main__':
    test_summary_table() 
import pandas as pd
import sys
import os
import argparse

# --- Add project root to sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
# ---------------------------------------

from src.backtesters.engine import BacktestEngine
from src.backtesters.strategies import generate_signals_from_8_state, generate_signals_from_momentum, generate_signals_from_run_analysis

def load_price_data(symbol: str) -> pd.DataFrame:
    """
    Loads historical price data for a given symbol.
    """
    price_path = f"data/daily/historical_price_{symbol}.csv"
    if not os.path.exists(price_path):
        raise FileNotFoundError(f"Historical price data not found for {symbol} at {price_path}")
    
    df = pd.read_csv(price_path, parse_dates=['date'], index_col='date')
    
    # Standardize column name to 'price'
    if 'close' in df.columns:
        df = df.rename(columns={'close': 'price'})
    
    if 'price' not in df.columns:
        raise ValueError("Price data must contain a 'price' or 'close' column.")
        
    return df

def main():
    """
    Main function to run the backtest from the command line.
    """
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Run a backtest for a given symbol and strategy.")
    parser.add_argument('symbol', type=str, help="The trading symbol to backtest (e.g., 'BTCUSDT').")
    parser.add_argument('-t', '--strategy', type=str, default='momentum', choices=['8-state', 'momentum', 'run-analysis'], help="The strategy to use for the backtest.")
    parser.add_argument('-sl', '--stoploss', type=float, default=None, help="The static stop-loss percentage (e.g., 0.1 for 10%).")
    parser.add_argument('-tsl', '--trailing_stoploss', type=float, default=None, help="The trailing stop-loss percentage (e.g., 0.1 for 10%).")
    args = parser.parse_args()
        
    symbol = args.symbol.upper()
    strategy_name = args.strategy
    stop_loss_pct = args.stoploss
    trailing_stop_loss_pct = args.trailing_stoploss
    
    print(f"\n--- Starting Backtest ---")
    print(f"Asset: {symbol}")
    print(f"Strategy: {strategy_name}")
    if stop_loss_pct and not trailing_stop_loss_pct:
        print(f"Static Stop-Loss: {stop_loss_pct:.1%}")
    if trailing_stop_loss_pct:
        print(f"Trailing Stop-Loss: {trailing_stop_loss_pct:.1%}")
    print("--------------------------\n")
    
    try:
        # 1. Load Data
        print("Loading price data...")
        price_data = load_price_data(symbol)
        
        # 2. Generate Signals
        print("Generating trading signals...")
        if strategy_name == '8-state':
            signals = generate_signals_from_8_state(symbol)
        elif strategy_name == 'momentum':
            signals = generate_signals_from_momentum(symbol, price_data)
        elif strategy_name == 'run-analysis':
            signals = generate_signals_from_run_analysis(symbol, price_data)
        else:
            print(f"Error: Strategy '{strategy_name}' not recognized.")
            sys.exit(1)
        
        # 3. Initialize and Run Backtest Engine
        engine = BacktestEngine(
            data=price_data,
            signals=signals,
            initial_capital=10000.0,
            transaction_cost=0.001, # 0.1% fee
            stop_loss_pct=stop_loss_pct,
            trailing_stop_loss_pct=trailing_stop_loss_pct
        )
        
        engine.run()
        
        # 4. Calculate and Display Performance
        engine.calculate_performance()
        
        # 5. Plot and Save Equity Curve
        plot_name = f"{symbol}_{strategy_name}"
        if trailing_stop_loss_pct:
            plot_name += f"_tsl_{int(trailing_stop_loss_pct*100)}pct"
        elif stop_loss_pct:
            plot_name += f"_sl_{int(stop_loss_pct*100)}pct"
            
        engine.plot_equity_curve(symbol=symbol, strategy_name=plot_name)

    except (FileNotFoundError, ValueError) as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
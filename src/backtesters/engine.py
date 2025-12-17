import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class BacktestEngine:
    """
    A simple event-driven backtesting engine.
    Handles portfolio management and performance calculation.
    """
    def __init__(self, data: pd.DataFrame, signals: pd.DataFrame, initial_capital=10000.0, transaction_cost=0.001, stop_loss_pct=None, trailing_stop_loss_pct=None):
        """
        Initializes the backtesting engine.

        Args:
            data: DataFrame with historical price data, indexed by date. Must contain 'price' column.
            signals: DataFrame with 'signal' (BUY, SELL, HOLD) column, indexed by date.
            initial_capital: The starting capital for the backtest.
            transaction_cost: The cost per transaction (e.g., 0.001 for 0.1%).
            stop_loss_pct: The static stop-loss percentage.
            trailing_stop_loss_pct: The trailing stop-loss percentage.
        """
        self.data = data
        self.signals = signals
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_loss_pct = trailing_stop_loss_pct
        
        # --- Internal State ---
        self.cash = initial_capital
        self.asset_quantity = 0.0
        self.portfolio_history = []
        self.entry_price = 0.0
        self.highest_price_since_entry = 0.0 # For trailing stop-loss

    def run(self):
        """
        Runs the backtest from the start date to the end date.
        """
        print("Running backtest...")
        
        # Align data and signals
        df = self.data.join(self.signals, how='left').fillna(value={'signal': 'HOLD'})
        
        for index, row in df.iterrows():
            date = index.date()
            price = row['price']
            signal = row['signal']
            
            # --- Check for Stop-Loss Triggers ---
            if self.asset_quantity > 0:
                # 1. Update highest price for trailing stop-loss
                if price > self.highest_price_since_entry:
                    self.highest_price_since_entry = price
                
                # 2. Check for trailing stop-loss
                if self.trailing_stop_loss_pct is not None:
                    stop_price = self.highest_price_since_entry * (1 - self.trailing_stop_loss_pct)
                    if price < stop_price:
                        signal = 'SELL'
                        print(f"  - TRAILING STOP-LOSS TRIGGERED on {date} at price {price:.2f} (Stop Price: {stop_price:.2f})")

                # 3. Check for static stop-loss (only if trailing stop isn't active)
                elif self.stop_loss_pct is not None:
                    if price < self.entry_price * (1 - self.stop_loss_pct):
                        signal = 'SELL'
                        print(f"  - STATIC STOP-LOSS TRIGGERED on {date} at price {price:.2f}")

            # --- Execute trade based on signal ---
            self._execute_trade(signal, price)
            
            # --- Update portfolio value ---
            portfolio_value = self.cash + (self.asset_quantity * price)
            self.portfolio_history.append({'date': date, 'value': portfolio_value})

        self.portfolio_history = pd.DataFrame(self.portfolio_history).set_index('date')
        print("Backtest complete.")
        return self.portfolio_history

    def _execute_trade(self, signal, price):
        """
        Executes a trade based on the signal using an all-in/all-out approach.
        """
        # On BUY signal, if we have cash, buy as much as possible
        if signal == 'BUY' and self.cash > 0:
            investment = self.cash * (1 - self.transaction_cost)
            self.asset_quantity = investment / price
            self.cash = 0.0
            self.entry_price = price
            self.highest_price_since_entry = price # Initialize for trailing stop
            
        # On SELL signal, if we hold the asset, sell all of it
        elif signal == 'SELL' and self.asset_quantity > 0:
            proceeds = self.asset_quantity * price
            self.cash = proceeds * (1 - self.transaction_cost)
            self.asset_quantity = 0.0
            self.entry_price = 0.0
            self.highest_price_since_entry = 0.0 # Reset

    def calculate_performance(self):
        """
        Calculates and prints key performance metrics.
        """
        if self.portfolio_history.empty:
            print("Portfolio history is empty. Cannot calculate performance.")
            return

        # 1. Total Return
        total_return = (self.portfolio_history['value'].iloc[-1] / self.initial_capital) - 1
        
        # 2. Buy & Hold Return
        buy_hold_return = (self.data['price'].iloc[-1] / self.data['price'].iloc[0]) - 1
        
        # 3. Max Drawdown
        rolling_max = self.portfolio_history['value'].cummax()
        daily_drawdown = self.portfolio_history['value'] / rolling_max - 1.0
        max_drawdown = daily_drawdown.min()

        print("\n--- Backtest Performance ---")
        print(f"Total Strategy Return: {total_return:.2%}")
        print(f"Buy & Hold Return:     {buy_hold_return:.2%}")
        print(f"Max Drawdown:          {max_drawdown:.2%}")
        # More metrics (Sharpe Ratio, etc.) can be added here.
        
    def plot_equity_curve(self, symbol, strategy_name):
        """
        Plots the portfolio's equity curve against a 'Buy and Hold' benchmark.
        """
        if self.portfolio_history.empty:
            print("Portfolio history is empty. Cannot plot equity curve.")
            return
            
        print("Plotting equity curve...")
        
        # Calculate Buy & Hold equity curve
        buy_hold_equity = self.data['price'] / self.data['price'].iloc[0] * self.initial_capital
        
        # Plotting
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(14, 8))
        
        ax.plot(self.portfolio_history.index, self.portfolio_history['value'], label=f'{strategy_name} Strategy', color='royalblue', lw=2)
        ax.plot(buy_hold_equity.index, buy_hold_equity, label='Buy & Hold', color='gray', linestyle='--', lw=2)
        
        ax.set_title(f"Equity Curve: {strategy_name} vs. Buy & Hold for {symbol}", fontsize=16)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Portfolio Value ($)", fontsize=12)
        ax.legend(fontsize=12)
        ax.grid(True)
        
        # Save the plot
        output_dir = "plots/backtests"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{symbol}_{strategy_name}_equity_curve.png"
        filepath = os.path.join(output_dir, filename)
        
        plt.savefig(filepath)
        plt.close(fig) # Close the figure to free up memory
        
        print(f"Equity curve plot saved to {filepath}") 
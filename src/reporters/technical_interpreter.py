import pandas as pd
import os

def _get_latest_data(symbol: str) -> tuple[pd.Series | None, pd.Series | None]:
    """Fetches the last row of data from technical analysis and signals files."""
    tech_path = f"data/analysis/technical_analysis_{symbol}.csv"
    signals_path = f"data/analysis/signals_{symbol}.csv"

    latest_tech = None
    latest_signal = None

    if os.path.exists(tech_path):
        try:
            tech_df = pd.read_csv(tech_path, parse_dates=['date'])
            if not tech_df.empty:
                latest_tech = tech_df.iloc[-1]
        except Exception as e:
            print(f"Error reading technical analysis file for {symbol}: {e}")

    if os.path.exists(signals_path):
        try:
            signals_df = pd.read_csv(signals_path, parse_dates=['date'])
            if not signals_df.empty:
                latest_signal = signals_df.iloc[-1]
        except Exception as e:
            print(f"Error reading signals file for {symbol}: {e}")
            
    return latest_tech, latest_signal

def _interpret_trend(price, sma_50, sma_200) -> str:
    """Interprets the long-term trend based on price and SMAs."""
    if pd.isna(price) or pd.isna(sma_50) or pd.isna(sma_200):
        return "Long-term trend data is not yet available (SMAs are still calculating)."

    if price > sma_50 > sma_200:
        return f"The asset is in a **strong uptrend**, with the current price (${price:,.2f}) above both the 50-day SMA (${sma_50:,.2f}) and the 200-day SMA (${sma_200:,.2f})."
    elif price < sma_50 < sma_200:
        return f"The asset is in a **strong downtrend**, with the current price (${price:,.2f}) below both the 50-day SMA (${sma_50:,.2f}) and the 200-day SMA (${sma_200:,.2f})."
    elif sma_50 > sma_200 and price < sma_50:
        return f"The asset is in a long-term uptrend (50-day SMA is above 200-day SMA), but is currently experiencing a **pullback** with the price (${price:,.2f}) below the 50-day SMA (${sma_50:,.2f})."
    elif sma_50 < sma_200 and price > sma_50:
        return f"The asset is in a long-term downtrend (50-day SMA is below 200-day SMA), but is currently experiencing a **relief rally** with the price (${price:,.2f}) above the 50-day SMA (${sma_50:,.2f})."
    else:
        return "The trend is mixed, with the price and moving averages consolidating."

def _interpret_volatility(bb_width_percentile, realized_vol_percentile) -> str:
    """Interprets the market volatility and compression state."""
    if pd.isna(bb_width_percentile) or pd.isna(realized_vol_percentile):
        return "Volatility compression data is not available."
        
    avg_percentile = (bb_width_percentile + realized_vol_percentile) / 2

    if avg_percentile < 30:
        return "Volatility is **extremely low** (compression percentile < 30%), suggesting the market is coiling and building energy for a potentially sharp move."
    elif avg_percentile < 50:
        return "Volatility is lower than average, indicating a period of consolidation."
    else:
        return "Volatility is elevated, suggesting active and trending market conditions."

def _interpret_momentum(rsi, macd, macd_signal, macd_hist) -> str:
    """Interprets momentum indicators RSI and MACD."""
    momentum_narrative = []
    
    # RSI interpretation
    if pd.notna(rsi):
        if rsi > 70:
            rsi_text = f"RSI is at **{rsi:.1f}**, indicating overbought conditions."
        elif rsi < 30:
            rsi_text = f"RSI is at **{rsi:.1f}**, indicating oversold conditions."
        else:
            rsi_text = f"RSI is neutral at **{rsi:.1f}**."
        momentum_narrative.append(rsi_text)
    else:
        momentum_narrative.append("RSI data is not available.")

    # MACD interpretation - more flexible handling
    if pd.notna(macd) and pd.notna(macd_signal):
        if pd.notna(macd_hist):
            # Full MACD interpretation with histogram
            if macd > macd_signal and macd_hist > 0:
                macd_text = "MACD shows **bullish momentum**, with the MACD line above its signal line and a positive histogram."
            elif macd < macd_signal and macd_hist < 0:
                macd_text = "MACD shows **bearish momentum**, with the MACD line below its signal line and a negative histogram."
            else:
                macd_text = "MACD momentum is currently unclear or transitioning."
        else:
            # MACD interpretation without histogram
            if macd > macd_signal:
                macd_text = "MACD shows **bullish momentum**, with the MACD line above its signal line."
            elif macd < macd_signal:
                macd_text = "MACD shows **bearish momentum**, with the MACD line below its signal line."
            else:
                macd_text = "MACD signals are neutral."
        momentum_narrative.append(macd_text)
    else:
        momentum_narrative.append("MACD data is not available.")

    return " ".join(momentum_narrative)

def generate_technical_summary(symbol: str) -> str:
    """
    Generates a human-readable technical summary for a given asset.
    """
    latest_tech, latest_signal = _get_latest_data(symbol)

    if latest_tech is None:
        return "Could not generate technical summary: No technical analysis data found."

    summary_parts = []

    # Part 1: Current State
    if latest_signal is not None:
        current_state = latest_signal.get('state', 'Unknown')
        summary_parts.append(f"The current 8-state model signal is **{current_state}**.")
    
    # Part 2: Long-Term Trend
    price = latest_tech.get('close')
    sma_50 = latest_tech.get('sma_50')
    sma_200 = latest_tech.get('sma_200')
    if pd.notna(price):
        summary_parts.append(_interpret_trend(price, sma_50, sma_200))

    # Part 3: Volatility / Compression
    bb_width_perc = latest_tech.get('bb_width_10d_percentile')
    realized_vol_perc = latest_tech.get('realized_vol_10d_percentile')
    summary_parts.append(_interpret_volatility(bb_width_perc, realized_vol_perc))
    
    # Part 4: Momentum
    rsi = latest_tech.get('rsi')
    macd = latest_tech.get('macd')
    macd_signal = latest_tech.get('macd_signal')
    macd_hist = latest_tech.get('macd_hist')
    summary_parts.append(_interpret_momentum(rsi, macd, macd_signal, macd_hist))

    # Combine into a final paragraph
    return " ".join(filter(None, summary_parts)) 
import pandas as pd
import os
import json
from datetime import date, datetime
import pdfkit
import markdown
import sys
import re

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.collectors import intraday_price_collector
from src.reporters.technical_interpreter import generate_technical_summary

# from src.reporters.reporter_utils import ReporterUtils # This file does not exist
# from src.reporters.narratives import (
#     SIGNAL_NARRATIVES,
#     INSTABILITY_NARRATIVES,
#     VOLATILITY_NARRATIVES
# )
from src.analyzers.run_analyzer import analyze_historical_price_data

# --- Constants ---
CONFIG_PATH = "data/config.json"
ANALYSIS_DIR = "data/analysis"
REPORTS_DIR = "reports"
CSS_PATH = "src/reporters/assets/report_style.css"

# This dictionary will hold the narrative descriptions for each signal.
# We can populate this from your 8_rules.md file.
SIGNAL_NARRATIVES = {
    # --- Foundational Bullish States ---
    "Bullish Trending": {
        "summary": "Price, Open Interest, and CVD are all signaling a strong upward trend. This is a high-conviction bullish signal suggesting broad market participation.",
        "outlook": "Bullish continuation is likely. Watch for OI or CVD to falter as an early warning sign of weakness."
    },
    "Bullish Exhaustion": {
        "summary": "Price and Open Interest are rising, but aggressive selling (CVD down) is present. This suggests that while new money is entering, it's being met with significant selling pressure (absorption).",
        "outlook": "The upward move may be vulnerable to a pullback. If buyers overcome the selling (CVD turns up), the trend can resume. Otherwise, expect a stall or reversal."
    },
    "Contrarian Bullish": {
        "summary": "Price and CVD are rising, but Open Interest is falling. This suggests the rally is fueled by short-sellers being forced to cover their positions, not by new organic longs.",
        "outlook": "This rally has limited fuel. Once short-covering is exhausted, the price is likely to stall. This is not a signal of a sustainable, healthy uptrend."
    },
    # --- Foundational Bearish States ---
    "Bearish Trending": {
        "summary": "Price, Open Interest, and CVD are all signaling a strong downward trend. This is a high-conviction bearish signal.",
        "outlook": "The bearish trend is likely to continue. For a potential bottom, watch for CVD to flatten or turn up first."
    },
    "Bearish Exhaustion": {
        "summary": "Price and Open Interest are falling, but CVD is rising. This suggests that while weak hands are capitulating, larger players may be quietly accumulating positions.",
        "outlook": "An early sign of potential bottoming. A sustained rise in CVD could signal a bullish reversal is forming."
    },
    "Contrarian Bearish": {
        "summary": "Price is falling while Open Interest is rising and CVD is falling. This indicates that new short positions are being opened and are actively pushing the price down.",
        "outlook": "Strong bearish continuation is expected until new shorts stop entering the market."
    },
    # --- States of Disagreement or Uncertainty ---
    "Bullish Disagreement": {
        "summary": "Price is rising, but both Open Interest and CVD are falling. This suggests the up-move is weak, lacks broad participation, and is being sold into. It has the classic signs of a 'Bull Trap'.",
        "outlook": "A sharp reversal is common. This rally should be treated with extreme suspicion as it is unlikely to be sustained."
    },
    "Bearish Disagreement": {
        "summary": "Price is falling, but both Open Interest and CVD are rising. This indicates a fierce battle where strong buyers are being met with even stronger overhead supply (sellers).",
        "outlook": "A significant spike in volatility is highly likely as the market is 'coiled'. The direction of the break is uncertain, but a decisive move is often imminent."
    },
    # --- Noise & Compression States ---
    "Noise (Bullish Bias)": {
        "summary": "The price move was not statistically significant (z-score < 0.5), indicating noise. However, the underlying OI and CVD flows show a bullish bias.",
        "outlook": "The market is consolidating without clear directional price intent. Wait for a breakout with a z-score > 0.5 before trusting the move."
    },
    "Noise (Bearish Bias)": {
        "summary": "The price move was not statistically significant (z-score < 0.5), indicating noise. However, the underlying OI and CVD flows show a bearish bias.",
        "outlook": "The market is consolidating without clear directional price intent. Wait for a breakdown with a z-score < -0.5 before trusting the move."
    },
    "Compression": {
        "summary": "The market is in a state of extremely low realized volatility. This indicates a 'compression' regime where the market is coiling and building energy.",
        "outlook": "Directional trades are low probability. Wait for volatility to expand, signaling the start of a new, more reliable move."
    },
    "Undefined": {
        "summary": "The combination of price, OI, and CVD states does not match any predefined pattern.",
        "outlook": "Market conditions are unclear and choppy. It is best to wait for a recognizable signal to emerge."
    }
}

# --- Regime Mapping ---
SIGNAL_REGIMES = {
    'Bullish Trending': 'Bullish',
    'Bullish Exhaustion': 'Bullish',
    'Contrarian Bullish': 'Bullish',
    'Bearish Trending': 'Bearish',
    'Bearish Exhaustion': 'Bearish',
    'Contrarian Bearish': 'Bearish',
    'Bullish Disagreement': 'Neutral',
    'Bearish Disagreement': 'Neutral',
    'Noise (Bullish Bias)': 'Neutral',
    'Noise (Bearish Bias)': 'Neutral',
    'Compression': 'Neutral',
    'Undefined': 'Neutral'
}

# A dictionary for the contextual narratives based on Regime + Instability
INSTABILITY_NARRATIVES = {
    "Bullish": {
        "High": "This bullish trend is accompanied by high instability from liquidations. This suggests the move may be volatile and prone to sharp corrections.",
        "Normal": "The bullish trend is proceeding with normal levels of liquidations, suggesting stable and organic price action."
    },
    "Bearish": {
        "High": "The bearish trend is being amplified by significant liquidations, indicating a potential capitulation event. Risk of a sharp, volatile move is elevated.",
        "Normal": "The bearish trend is proceeding with normal levels of liquidations, suggesting an orderly decline."
    },
    "Neutral": {
        "High": "The market lacks clear direction but is experiencing high instability from liquidations. This is a sign of extreme uncertainty and high risk for erratic price moves.",
        "Normal": "The market is in a quiet, neutral state with no unusual liquidation pressure."
    }
}

def _colorize_text(text: str) -> str:
    """Replaces keywords in text with colored HTML spans."""
    # Using a dictionary to avoid replacing parts of already replaced strings
    replacements = {}
    
    bullish_keywords = [
        'Bullish', 'UP', 'up', 'Rising', 'Overbought', 'Excellent', 'Good', 'Strong',
        'upward', 'uptrend', 'rally', 'bounce', 'accumulating', 'gains'
    ]
    bearish_keywords = [
        'Bearish', 'DOWN', 'down', 'Falling', 'Oversold', 'Poor', 'Weak', 'Severe',
        'High tail risk', 'downward', 'downtrend', 'pullback', 'reversal',
        'capitulation', 'drawdown', 'vulnerable', 'losses', 'risk'
    ]

    # Find all occurrences and mark them for replacement
    for keyword in bullish_keywords:
        # Case-insensitive search for whole words
        for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            replacements[match.span()] = f"<span style='color: green;'>{match.group(0)}</span>"
    
    for keyword in bearish_keywords:
        for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            replacements[match.span()] = f"<span style='color: red;'>{match.group(0)}</span>"
    
    # Apply replacements from end to start to not mess up indices
    sorted_spans = sorted(replacements.keys(), key=lambda item: item[0], reverse=True)
    
    for start, end in sorted_spans:
        text = text[:start] + replacements[(start, end)] + text[end:]
        
    return text

def _get_rules_appendix():
    """Generates the rule definitions appendix from the SIGNAL_NARRATIVES dictionary."""
    
    table = [
        "| Signal | Summary | Outlook |",
        "|:---|:---|:---|"
    ]
    
    for signal, narrative in SIGNAL_NARRATIVES.items():
        summary = narrative.get('summary', 'N/A').replace('|', '\\|')
        outlook = narrative.get('outlook', 'N/A').replace('|', '\\|')
        table.append(f"| **{signal}** | {summary} | {outlook} |")
        
    return "\n".join(table)

def _get_latest_regime_and_persistence(analysis_path: str) -> (str, int):
    """Reads the analysis file and returns the most recent regime and its persistence."""
    if not os.path.exists(analysis_path):
        return "Unknown", 0
    try:
        df = pd.read_csv(analysis_path, parse_dates=['date'])
        if len(df) < 2:
            return "No Data", 0
        
        # Use data from the most recent day.
        latest_signal = df['state'].iloc[-1]
        latest_regime = SIGNAL_REGIMES.get(latest_signal, 'Neutral')
        
        persistence = 0
        # Iterate backwards from the last row
        for i in range(len(df) - 1, -1, -1):
            signal = df['state'].iloc[i]
            regime = SIGNAL_REGIMES.get(signal, 'Neutral')
            if regime == latest_regime:
                persistence += 1
            else:
                break
        return latest_regime, persistence
    except Exception as e:
        print(f"Could not read or process analysis file {analysis_path}: {e}")
        return "Error", 0

def _get_latest_instability(instability_path: str) -> str:
    """Reads the instability analysis file and returns the most recent status."""
    if not os.path.exists(instability_path):
        return "Unknown"
    try:
        df = pd.read_csv(instability_path)
        if df.empty:
            return "No Data"
        # Assuming the last row is the most recent
        return df['instability_index'].iloc[-1]
    except Exception as e:
        print(f"Could not read or process instability file {instability_path}: {e}")
        return "Error"

def _get_latest_volatility_metrics(volatility_path: str) -> dict:
    """Reads the volatility analysis file and returns the most recent metrics."""
    if not os.path.exists(volatility_path):
        return {}
    try:
        df = pd.read_csv(volatility_path)
        if df.empty:
            return {}
        # Get the last row (most recent data)
        latest = df.iloc[-1]
        return {
            'sharpe': latest.get('sharpe_ratio', None),
            'sortino_20d': latest.get('sortino_ratio_20d', None),
            'sortino_60d': latest.get('sortino_ratio_60d', None),
            'cvar_20d': latest.get('cvar_20d', None),
            'cvar_60d': latest.get('cvar_60d', None),
            'omega_20d': latest.get('omega_ratio_20d', None),
            'omega_60d': latest.get('omega_ratio_60d', None),
            'mdd_20d': latest.get('max_drawdown_20d', None),
            'mdd_60d': latest.get('max_drawdown_60d', None),
            'mdd_120d': latest.get('max_drawdown_120d', None),
            'rsi': latest.get('rsi', None),
            'rsi_state': latest.get('rsi_state', None),
            'volatility_state': latest.get('volatility_state', None),
            'daily_return': latest.get('daily_return', None)
        }
    except Exception as e:
        print(f"Could not read or process volatility file {volatility_path}: {e}")
        return {}

def _get_volatility_interpretation(metrics: dict) -> str:
    """Generates interpretation text for volatility metrics."""
    if not metrics:
        return "No volatility data available."
        
    interpretations = []
    
    # Volatility State interpretation
    if metrics.get('volatility_state'):
        interpretations.append(f"**Volatility State**: {metrics['volatility_state']}")
    
    # RSI interpretation
    if metrics.get('rsi') is not None:
        rsi = metrics['rsi']
        if rsi > 70:
            interpretations.append("**RSI**: Overbought conditions")
        elif rsi < 30:
            interpretations.append("**RSI**: Oversold conditions")
        else:
            interpretations.append("**RSI**: Neutral conditions")
    
    # Sharpe Ratio interpretation (using 20d for quick view)
    if metrics.get('sharpe') is not None:
        sharpe = metrics['sharpe']
        if sharpe > 2:
            interpretations.append("**Sharpe Ratio (20d)**: Excellent risk-adjusted returns")
        elif sharpe > 1:
            interpretations.append("**Sharpe Ratio (20d)**: Good risk-adjusted returns")
        else:
            interpretations.append("**Sharpe Ratio (20d)**: Poor risk-adjusted returns")
    
    # Sortino Ratio interpretation (using 20d for quick view)
    if metrics.get('sortino_20d') is not None:
        sortino = metrics['sortino_20d']
        if sortino > 2:
            interpretations.append("**Sortino Ratio (20d)**: Strong downside-adjusted returns")
        elif sortino > 1:
            interpretations.append("**Sortino Ratio (20d)**: Moderate downside-adjusted returns")
        else:
            interpretations.append("**Sortino Ratio (20d)**: Weak downside-adjusted returns")
    
    # CVaR interpretation (using 20d for quick view)
    if metrics.get('cvar_20d') is not None:
        cvar = metrics['cvar_20d']
        if cvar < -0.05:
            interpretations.append("**CVaR (20d)**: High tail risk")
        elif cvar < -0.02:
            interpretations.append("**CVaR (20d)**: Moderate tail risk")
        else:
            interpretations.append("**CVaR (20d)**: Low tail risk")
    
    # Omega Ratio interpretation (using 20d for quick view)
    if metrics.get('omega_20d') is not None:
        omega = metrics['omega_20d']
        if omega > 2:
            interpretations.append("**Omega Ratio (20d)**: Strong gain/loss ratio")
        elif omega > 1:
            interpretations.append("**Omega Ratio (20d)**: Moderate gain/loss ratio")
        else:
            interpretations.append("**Omega Ratio (20d)**: Weak gain/loss ratio")
    
    # Max Drawdown interpretation (using 20d for quick view)
    if metrics.get('mdd_20d') is not None:
        mdd = metrics['mdd_20d']
        # Ensure mdd is negative for correct interpretation
        if mdd > 0: mdd = -mdd
        if mdd < -0.15:
            interpretations.append("**Max Drawdown (20d)**: Severe recent drawdown")
        elif mdd < -0.05:
            interpretations.append("**Max Drawdown (20d)**: Moderate recent drawdown")
        else:
            interpretations.append("**Max Drawdown (20d)**: Minor recent drawdown")
    
    # Join with newlines and add bullet points
    return "\n".join([f"* {interpretation}" for interpretation in interpretations])

def _get_run_analysis_predictions(symbol: str) -> dict:
    """Reads the combined run analysis file and returns key metrics for both timeframes."""
    report_date_str = date.today().strftime('%Y%m%d')
    prediction_path = os.path.join("data/predictions", f"run_analysis_{symbol}_{report_date_str}.json")
    if not os.path.exists(prediction_path):
        return {'error': 'Prediction file not found'}
    
    try:
        with open(prediction_path, 'r') as f:
            data = json.load(f)

        short_term_data = data.get('short_term', {})
        all_time_data = data.get('all_time', {})

        # --- Short-term Prediction ---
        p_continue_short = short_term_data.get('continuation_probability', 0.5)
        direction_short = short_term_data.get('current_direction', 'N/A')
        predicted_direction_short = direction_short if p_continue_short >= 0.5 else ("up" if direction_short == "down" else "down")
        prob_short = p_continue_short if p_continue_short >= 0.5 else 1 - p_continue_short
        
        # --- All-time Prediction ---
        p_continue_all = all_time_data.get('continuation_probability', 0.5)
        direction_all = all_time_data.get('current_direction', 'N/A')
        predicted_direction_all = direction_all if p_continue_all >= 0.5 else ("up" if direction_all == "down" else "down")
        prob_all = p_continue_all if p_continue_all >= 0.5 else 1 - p_continue_all

        return {
            'streak_str': f"{short_term_data.get('current_streak_length', 'N/A')}d {direction_short}",
            'pred_short_str': f"**{predicted_direction_short.upper()}**",
            'prob_short_str': f"{prob_short:.1%}",
            'pred_all_str': f"**{predicted_direction_all.upper()}**",
            'prob_all_str': f"{prob_all:.1%}",
        }
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing prediction file for {symbol}: {e}")
        return {'error': 'Could not parse prediction file'}

def _get_latest_intraday_price(symbol: str) -> tuple[float | None, str | None]:
    """Reads the intraday price file and returns the most recent price and its timestamp."""
    filepath = intraday_price_collector.get_intraday_price_filepath(symbol)
    if not os.path.exists(filepath):
        return None, None
    try:
        df = pd.read_csv(filepath)
        if df.empty:
            return None, None
        
        latest = df.iloc[-1]
        price = latest.get('price')
        date_str = latest.get('date')
        
        if pd.isna(price) or pd.isna(date_str):
            return None, None
            
        # Format the timestamp for display
        target_hour = intraday_price_collector.TARGET_HOUR_UTC
        display_timestamp = f"{date_str} {target_hour:02d}:00 UTC"
        
        return float(price), display_timestamp
        
    except Exception as e:
        print(f"Could not read or process intraday price file {filepath}: {e}")
        return None, None

def _humanize_number(n: float) -> str:
    """Formats a number into a human-readable string with a suffix (k, M, B)."""
    if n is None:
        return "N/A"
    if abs(n) < 1000:
        return f"{n:,.2f}"
    
    abs_n = abs(n)
    if abs_n >= 1_000_000_000:
        val = n / 1_000_000_000
        suffix = 'B'
    elif abs_n >= 1_000_000:
        val = n / 1_000_000
        suffix = 'M'
    else:
        val = n / 1_000
        suffix = 'k'
        
    return f"{val:,.2f}{suffix}"

def _generate_narrative_analysis(df: pd.DataFrame) -> list[str]:
    """
    Analyzes the recent history of signals to identify longer-term patterns and generate narratives.
    """
    narratives = []
    if len(df) < 7:  # Need at least 7 days for any meaningful pattern
        return narratives

    window = df.tail(20).copy()
    window.reset_index(drop=True, inplace=True)

    # --- Pattern 1: False Breakout from Compression ---
    # State machine to find the pattern: Compression -> Non-Compression -> Compression
    # This pattern must happen recently, so we check if the pattern completes in the last few days.
    in_compression_currently = window.iloc[-1]['state'] == 'Compression'
    if in_compression_currently:
        scan_state = 0 # 0=Start, 1=In-Breakout, 2=Found-Pattern
        breakout_days = []
        # We scan backwards from the second-to-last day
        for i in range(len(window) - 2, -1, -1):
            row = window.iloc[i]
            is_compression = row['state'] == 'Compression'
            
            if scan_state == 0 and not is_compression:
                scan_state = 1
                breakout_days.append(row)
            elif scan_state == 1:
                if is_compression:
                    scan_state = 2 # Pattern found
                    break
                else:
                    breakout_days.append(row)
        
        if scan_state == 2 and (1 <= len(breakout_days) <= 4):
            # The days are reversed, so the first day is at the end of the list
            first_breakout_day = breakout_days[-1]
            breakout_date = pd.to_datetime(first_breakout_day['date']).strftime('%Y-%m-%d')
            regime_on_breakout = SIGNAL_REGIMES.get(first_breakout_day['state'], 'Neutral')
            direction = 'uncertain'
            if regime_on_breakout == 'Bullish': direction = 'upward'
            elif regime_on_breakout == 'Bearish': direction = 'downward'
            narratives.append(
                f"**False Breakout Detected ({breakout_date})**: The market's attempt at an {direction} breakout from compression "
                f"failed to find follow-through, quickly returning to a low-volatility state. "
                "This rejection suggests a lack of conviction and reinforces the current range-bound thesis."
            )

    # --- Pattern 2: Trend Exhaustion ---
    # Look for a long trend followed by weaker signals.
    # To avoid conflicting with a "False Breakout", we only run this if no breakout was detected.
    if not narratives:
        strong_trend_streak = 0
        trend_type = None
        trend_start_date = None
        
        for i in range(len(window) -1, -1, -1):
            state = window.iloc[i]['state']
            date = window.iloc[i]['date']

            if state in ["Bullish Trending", "Bearish Trending"]:
                current_trend_type = "Bullish" if "Bullish" in state else "Bearish"
                if trend_type is None:
                    trend_type = current_trend_type
                    trend_start_date = date
                
                if trend_type == current_trend_type:
                    strong_trend_streak += 1
                else: # Trend flipped
                    break
            else: # Streak broken
                # Check if the streak was long enough and the break is recent
                if strong_trend_streak >= 5 and i == len(window) - 2:
                     exhaustion_date = pd.to_datetime(window.iloc[i+1]['date']).strftime('%Y-%m-%d')
                     trend_start_str = pd.to_datetime(trend_start_date).strftime('%Y-%m-%d')
                     narratives.append(
                        f"**Trend Exhaustion ({exhaustion_date})**: After a **{strong_trend_streak}-day {trend_type.lower()} trend** that began on {trend_start_str}, the market's momentum has faded. "
                        "This suggests the prior trend is losing conviction and may be due for a pullback or consolidation."
                     )
                break # Exit after the first break of a streak

    # --- Pattern 3: Confirmed Breakout ---
    # Look for a breakout from compression that is sustained.
    is_trending_currently = window.iloc[-1]['state'] in ["Bullish Trending", "Bearish Trending"]
    if is_trending_currently:
        trend_duration = 0
        breakout_from_compression = False
        breakout_start_date = None
        current_trend_type = "Bullish" if "Bullish" in window.iloc[-1]['state'] else "Bearish"

        for i in range(len(window) - 1, -1, -1):
            row = window.iloc[i]
            state = row['state']
            
            if state in ["Bullish Trending", "Bearish Trending"] and ("Bullish" if "Bullish" in state else "Bearish") == current_trend_type:
                trend_duration += 1
                breakout_start_date = row['date']
            else:
                # The day before the trend started, was it compression?
                if state == 'Compression':
                    breakout_from_compression = True
                break
        
        if breakout_from_compression and (2 <= trend_duration <= 3):
            breakout_start_str = pd.to_datetime(breakout_start_date).strftime('%Y-%m-%d')
            narratives.append(
                f"**Confirmed Breakout ({breakout_start_str})**: The market has executed a **confirmed {current_trend_type.lower()} breakout** from a prior compression phase. "
                f"The trend has sustained for **{trend_duration} days**, suggesting conviction behind the move."
            )

    # --- Pattern 4: Stealth Accumulation / Distribution ---
    # Look for flat price action with rising/falling CVD
    is_consolidating = window.iloc[-5:]['state'].isin(['Compression', 'Noise (Bullish Bias)', 'Noise (Bearish Bias)']).all()
    if is_consolidating:
        try:
            # We need numpy for linear regression to find the trend in CVD
            import numpy as np
            
            consolidation_window = window.tail(7) # Analyze CVD over the last 7 days
            start_date_str = pd.to_datetime(consolidation_window.iloc[0]['date']).strftime('%Y-%m-%d')
            cvd_values = consolidation_window['cvd']
            
            # Simple linear regression to find the slope of the CVD
            x = np.arange(len(cvd_values))
            slope, _ = np.polyfit(x, cvd_values, 1)
            
            # Normalize the slope by the average magnitude of CVD to make it comparable
            avg_cvd_magnitude = cvd_values.abs().mean()
            normalized_slope = slope / avg_cvd_magnitude if avg_cvd_magnitude != 0 else 0

            if normalized_slope > 0.15: # Threshold for significant positive slope
                 narratives.append(
                    f"**Stealth Accumulation (since {start_date_str})**: While the price has remained in a consolidation range, "
                    "the Cumulative Volume Delta (CVD) has been steadily rising. This suggests quiet accumulation may be underway."
                 )
            elif normalized_slope < -0.15: # Threshold for significant negative slope
                narratives.append(
                    f"**Stealth Distribution (since {start_date_str})**: While the price has remained in a consolidation range, "
                    "the Cumulative Volume Delta (CVD) has been steadily falling. This suggests quiet distribution may be underway."
                 )
        except ImportError:
            # Silently fail if numpy is not available, as it's a non-critical enhancement.
            pass
        except Exception:
            # Also fail silently on any unexpected analysis error to not crash the report.
            pass

    return narratives

def generate_report():
    """
    Generates a Markdown report from the latest signal analysis for all configured assets.
    """
    print("Generating market analysis report...")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    report_date = date.today()
    report_title = f"# Crypto Market Analysis - {report_date.isoformat()}\n\n"
    
    # 1. Load asset list from config
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        assets = config.get("assets", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing config file: {e}")
        return

    # 2. Build Market Summary Table
    summary_table = [
        "## Market Summary\n\n",
        "*The following table summarizes the market's phase based on a multi-factor model including Price, Open Interest, and CVD.*\n\n",
        "| Asset   | Market Phase | Days in Regime | Liquidations | Sharpe (20d) | Sortino (20d) | CVaR (20d) |\n",
        "|:--------|:---------------|:---------------|:------------|:-------------|:--------------|:-----------|\n"
    ]
    asset_details_map = {} # To store data for detailed sections

    for symbol in assets:
        signals_path = os.path.join(ANALYSIS_DIR, f"signals_{symbol}.csv")
        instability_path = os.path.join(ANALYSIS_DIR, f"instability_{symbol}.csv")
        volatility_path = os.path.join(ANALYSIS_DIR, f"volatility_{symbol}.csv")
        
        regime, persistence = _get_latest_regime_and_persistence(signals_path)
        instability = _get_latest_instability(instability_path)
        volatility_metrics = _get_latest_volatility_metrics(volatility_path)
        
        sharpe = f"{volatility_metrics.get('sharpe', 'N/A'):.2f}" if volatility_metrics.get('sharpe') is not None else 'N/A'
        sortino = f"{volatility_metrics.get('sortino_20d', 'N/A'):.2f}" if volatility_metrics.get('sortino_20d') is not None else 'N/A'
        
        cvar_val = volatility_metrics.get('cvar_20d')
        cvar = f"{cvar_val:.2%}" if cvar_val is not None else 'N/A'
        
        summary_table.append(f"| {symbol} | {_colorize_text(regime)} | {persistence} days | {_colorize_text(instability)} | {sharpe} | {sortino} | {cvar} |\n")
        asset_details_map[symbol] = {
            'signals_path': signals_path,
            'instability': instability,
            'volatility_path': volatility_path
        }

    # --- Build Run Analysis Table ---
    # summary_table.append("\n\n### Market Momentum (Run Analysis)")
    # summary_table.append("\n\n*The following table tracks simple momentum based on consecutive days of price moves.*\n")
    # summary_table.append("*The 100d prediction is based on the last 100 days of data, while the All Time prediction is based on all available data.*\n\n")
    # summary_table.append("| Asset | Price Streak | Predicted (100d) | Prob. | Predicted (All Time) | Prob. |\n")
    # summary_table.append("|:------|:---------------|:------------------|:------|:----------------|:------|\n")

    # for symbol in assets:
    #     preds = _get_run_analysis_predictions(symbol)
        
    #     if 'error' in preds:
    #         summary_table.append(f"| {symbol} | {preds['error']} | - | - | - | - |\n")
    #     else:
    #         summary_table.append(f"| {symbol} | {preds['streak_str']} | {_colorize_text(preds['pred_short_str'])} | {preds['prob_short_str']} | {_colorize_text(preds['pred_all_str'])} | {preds['prob_all_str']} |\n")

    # 3. Build Detailed Analysis Sections
    detailed_sections = [
        '\n<div style="page-break-before: always;"></div>\n\n',
        # "## Detailed Analysis\n\n"
    ]
    for i, (symbol, details) in enumerate(asset_details_map.items()):
        if not os.path.exists(details['signals_path']):
            print(f"    - Warning: Signal file not found at {details['signals_path']}. Skipping.")
            continue
        
        # Add page break before each asset except the first one
        if i > 0:
            detailed_sections.append('\n<div style="page-break-before: always;"></div>\n\n')
            
        asset_section = _generate_asset_section(symbol, details['signals_path'], details['instability'], details['volatility_path'])
        if asset_section:
            detailed_sections.append(asset_section)

    # 4. Assemble the full report
    appendix = _get_rules_appendix()
    
    # Add page break before appendices
    report_content = [report_title] + summary_table + detailed_sections
    report_content.append('\n<div style="page-break-before: always;"></div>\n\n')
    report_content.append("# Appendix: Rule Definitions\n\n")
    report_content.append(appendix)
    
    # Add page break before volatility metrics appendix
    report_content.append('\n<div style="page-break-before: always;"></div>\n\n')
    report_content.append("# Appendix: Volatility Metrics\n\n")
    report_content.append("""
### Risk Metrics Glossary

- **Volatility State**: Current market volatility level (High/Normal/Low) based on return deviations.
- **RSI (Relative Strength Index)**: Momentum oscillator measuring speed and change of price movements. Range: 0-100.
- **Sharpe Ratio**: Measures risk-adjusted returns relative to total volatility. Higher values indicate better risk-adjusted performance.
- **Sortino Ratio**: Measures risk-adjusted returns, focusing on downside volatility. Higher values indicate better risk-adjusted performance.
- **CVaR (Conditional Value at Risk)**: Expected loss in the worst 5% of cases. More negative values indicate higher tail risk.
- **Omega Ratio**: Ratio of gains to losses above a threshold. Values > 1 indicate more gains than losses.
- **Max Drawdown**: Largest peak-to-trough decline. More negative values indicate larger price drops.

### Interpretation Guidelines

**Volatility State**:
                            
- **High**: Returns exceeding 2 standard deviations
- **Normal**: Returns within normal range
- **Low**: Returns below 0.5 standard deviations

**RSI**:
                            
- **> 70**: Overbought conditions
- **< 30**: Oversold conditions
- **30-70**: Neutral conditions

**Sharpe Ratio**:
                            
- **> 2**: Excellent risk-adjusted returns
- **1-2**: Good risk-adjusted returns
- **< 1**: Poor risk-adjusted returns

**Sortino Ratio**:
                            
- **> 2**: Excellent risk-adjusted returns
- **1-2**: Good risk-adjusted returns
- **< 1**: Poor risk-adjusted returns

**CVaR**:
                            
- **> -2%**: Low tail risk
- **-2% to -5%**: Moderate tail risk
- **< -5%**: High tail risk

**Omega Ratio**:
                            
- **> 2**: Strong gain/loss ratio
- **1-2**: Moderate gain/loss ratio
- **< 1**: Weak gain/loss ratio

**Max Drawdown**:
                            
- **> -5%**: Minor drawdown
- **-5% to -15%**: Moderate drawdown
- **< -15%**: Severe drawdown

### Time Windows

Metrics are calculated over multiple time windows to provide different perspectives:
                            
- **20 days**: Short-term view
- **60 days**: Medium-term view
- **120 days**: Long-term view (for Max Drawdown)
""")
    
    # 5. Write files
    report_filename_date = report_date.strftime("%Y%m%d")
    report_filename = f"market_report_{report_filename_date}.md"
    report_path = os.path.join(REPORTS_DIR, report_filename)
    pdf_path = os.path.join(REPORTS_DIR, report_filename.replace(".md", ".pdf"))
    
    final_markdown_content = "".join(report_content)
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(final_markdown_content)
        print(f"\nReport generated successfully at {report_path}")

        # --- Convert Markdown to PDF ---
        try:
            html_content = markdown.markdown(final_markdown_content, extensions=['tables'])
            
            # Load CSS and prepend it to the HTML
            try:
                with open(CSS_PATH, 'r', encoding='utf-8') as f:
                    css = f.read()
                html_with_style = f'<html><head><meta charset="UTF-8"><style>{css}</style></head><body>{html_content}</body></html>'
            except FileNotFoundError:
                print(f"Warning: CSS file not found at {CSS_PATH}. PDF will be unstyled.")
                html_with_style = html_content

            # Set PDFKit options to ensure UTF-8 encoding
            options = {
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }
            pdfkit.from_string(html_with_style, pdf_path, options=options)
            print(f"PDF version generated successfully at {pdf_path}")
        except Exception as e:
            print(f"\nCould not generate PDF. Please ensure 'wkhtmltopdf' is installed and in your system's PATH.")
            print(f"Error details: {e}")

    except IOError as e:
        print(f"Error writing report file: {e}")

def _generate_asset_section(symbol: str, signals_path: str, instability: str, volatility_path: str) -> str | None:
    """
    Generates a detailed analysis section for a single asset.
    """
    if not os.path.exists(signals_path):
        return f"### {symbol}\n\n- _Signal data not found._\n"
    
    try:
        df = pd.read_csv(signals_path, parse_dates=['date'])
        if df.empty:
            return None
        
        # Use the most recent row for the signal
        latest = df.iloc[-1]
        
        # --- Generate Narrative Analysis ---
        narrative_analysis = _generate_narrative_analysis(df)
        
        # Get volatility metrics
        volatility_metrics = _get_latest_volatility_metrics(volatility_path)
        
        # Get the latest intraday price
        intraday_price, intraday_timestamp = _get_latest_intraday_price(symbol)
        
        # --- Formatting for Display ---

        # Format intraday price display
        intraday_price_display = "N/A"
        if intraday_price is not None:
            intraday_price_display = f"${intraday_price:,.2f} <br/><small>({intraday_timestamp})</small>"

        # Latest raw values for the snapshot table
        latest_oi_display = f"${_humanize_number(latest['oi'])}"
        latest_cvd_display = f"{_humanize_number(latest['cvd'])} coins"

        # Get the narrative for the current signal
        narrative = SIGNAL_NARRATIVES.get(latest['state'], SIGNAL_NARRATIVES['Undefined'])
        
        # Get the contextual instability narrative
        instability_text = INSTABILITY_NARRATIVES.get(SIGNAL_REGIMES.get(latest['state'], 'Neutral'), {}).get(instability, "")

        # Get volatility metrics and interpretation
        volatility_interpretation = _get_volatility_interpretation(volatility_metrics)

        # Calculate regime persistence
        current_regime = SIGNAL_REGIMES.get(latest['state'], 'Neutral')
        regime_persistence_count = 0
        
        # Iterate backwards from the last row
        for i in range(len(df) - 1, -1, -1):
            signal_on_day = df.iloc[i]['state']
            regime_on_day = SIGNAL_REGIMES.get(signal_on_day, 'Neutral')
            if regime_on_day == current_regime:
                regime_persistence_count += 1
            else:
                break

        # Format regime persistence text
        if regime_persistence_count <= 1:
            regime_text = f"The market has been in a **{current_regime}** state for **1 day.**"
        else:
            regime_text = f"The market has been in a **{current_regime}** state for **{regime_persistence_count} consecutive days**."

        # --- Colorize text for the report ---
        current_signal_colored = _colorize_text(latest['state'])
        regime_text_colored = _colorize_text(regime_text)
        summary_colored = _colorize_text(narrative['summary'])
        outlook_colored = _colorize_text(narrative['outlook'])
        instability_text_colored = _colorize_text(instability_text)
        volatility_interpretation_colored = _colorize_text(volatility_interpretation)

        # --- Build Signal Table ---
        # Show the last 5 days of signals for recent context
        last_5_days = df.tail(5)
        table_md = "| Date | Close | State | Price State | OI State | CVD State |\n"
        table_md += "|:---|---:|:---|:---|:---|:---|\n"
        for _, row in last_5_days.iterrows():
            date_str = pd.to_datetime(row['date']).strftime('%Y-%m-%d')
            close_str = f"{row['close']:,.2f}"
            
            # Colorize the state columns
            state_colored = _colorize_text(row['state'])
            price_state_colored = _colorize_text(row['price_state'])
            oi_state_colored = _colorize_text(row['oi_state'])
            cvd_state_colored = _colorize_text(row['cvd_state'])

            table_md += f"| {date_str} | {close_str} | {state_colored} | {price_state_colored} | {oi_state_colored} | {cvd_state_colored} |\n"

        # --- Assemble the Markdown content for this asset ---
        section = [
            f"## {symbol} Analysis\n\n",
            f"**Current Signal:** {current_signal_colored}\n\n",
            f"**Prevailing Regime:** {regime_text_colored}\n\n",

            # --- Table 1: Latest Values Snapshot ---
            "**Latest Market Values:**\n\n",
            "| Price (Intraday) | Open Interest | CVD |\n",
            "|:---|:---|:---|\n",
            f"| {intraday_price_display} | {latest_oi_display} | {latest_cvd_display} |\n\n",

            # Asset Summary
            "**Asset Summary:**\n\n",
            f"* {summary_colored}\n\n",

            # What to Watch For
            "**What to Watch For:**\n\n",
            f"* {outlook_colored}\n\n",
        ]
        
        # --- NEW: Long-Term Observations ---
        if narrative_analysis:
            section.append("**Longer-Term Observations:**\n\n")
            for text in narrative_analysis:
                section.append(f"* {_colorize_text(text)}\n\n")

        section.extend([
            # Instability Index
            "**Instability Index:**\n\n",
            f"* The current instability level is **{_colorize_text(instability)}**. This index measures the risk of liquidations in the market. {instability_text_colored}\n\n",

            # Risk Metrics
            f"**Risk Metrics:**\n\n{volatility_interpretation_colored}\n\n",

            # --- Build Signal Table ---
            # Show the last 5 days of signals for recent context
            "**Recent Signals:**\n\n",
            table_md,
            f"\n\n",

            # --- Intraday Price Section ---
            # "**Intraday Price:**\n\n",
            # f"* The latest intraday price is **{intraday_price_display}**\n\n",
        ])
        
        # Add detailed risk metrics if available
        if volatility_metrics:
            # Market State Table
            section.append("### Market State\n\n")
            section.append("| Metric | Value |\n")
            section.append("|:-------|:------|\n")
            
            if volatility_metrics.get('daily_return') is not None:
                section.append(f"| Daily Return (20d Avg) | {_colorize_text(f'{volatility_metrics['daily_return']:.2%}')} |\n")
            if volatility_metrics.get('volatility_state'):
                section.append(f"| Volatility State | {_colorize_text(volatility_metrics['volatility_state'])} |\n")
            if volatility_metrics.get('rsi') is not None:
                section.append(f"| RSI | {volatility_metrics['rsi']:.1f} ({_colorize_text(volatility_metrics.get('rsi_state', 'Unknown'))}) |\n")
            
            section.append("\n\n")
            
            # Risk-Adjusted Returns Table
            section.append("### Risk-Adjusted Returns\n\n")
            section.append("| Metric | Value |\n")
            section.append("|:-------|:------|\n")
            
            if volatility_metrics.get('sharpe') is not None:
                section.append(f"| Sharpe Ratio (20d) | {volatility_metrics['sharpe']:.2f} |\n")
            
            # Sortino Ratios
            section.append("| Sortino Ratio |\n")
            if volatility_metrics.get('sortino_20d') is not None:
                section.append(f"| - 20-day | {volatility_metrics['sortino_20d']:.2f} |\n")
            if volatility_metrics.get('sortino_60d') is not None:
                section.append(f"| - 60-day | {volatility_metrics['sortino_60d']:.2f} |\n")
            
            section.append("\n")
            
            # Risk Metrics Table
            section.append("### Risk Metrics\n\n")
            section.append("| Metric | 20-day | 60-day | 120-day |\n")
            section.append("|:-------|:-------|:-------|:--------|\n")
            
            # CVaR
            cvar_20d = f"{volatility_metrics.get('cvar_20d', 'N/A'):.2%}" if volatility_metrics.get('cvar_20d') is not None else 'N/A'
            cvar_60d = f"{volatility_metrics.get('cvar_60d', 'N/A'):.2%}" if volatility_metrics.get('cvar_60d') is not None else 'N/A'
            section.append(f"| CVaR | {cvar_20d} | {cvar_60d} | - |\n")
            
            # Omega Ratio
            omega_20d = f"{volatility_metrics.get('omega_20d', 'N/A'):.2f}" if volatility_metrics.get('omega_20d') is not None else 'N/A'
            omega_60d = f"{volatility_metrics.get('omega_60d', 'N/A'):.2f}" if volatility_metrics.get('omega_60d') is not None else 'N/A'
            section.append(f"| Omega Ratio | {omega_20d} | {omega_60d} | - |\n")
            
            # Max Drawdown
            mdd_20d_val = volatility_metrics.get('mdd_20d')
            mdd_60d_val = volatility_metrics.get('mdd_60d')
            mdd_120d_val = volatility_metrics.get('mdd_120d')

            mdd_20d = f"{-abs(mdd_20d_val):.2%}" if mdd_20d_val is not None else 'N/A'
            mdd_60d = f"{-abs(mdd_60d_val):.2%}" if mdd_60d_val is not None else 'N/A'
            mdd_120d = f"{-abs(mdd_120d_val):.2%}" if mdd_120d_val is not None else 'N/A'
            section.append(f"| Max Drawdown | {mdd_20d} | {mdd_60d} | {mdd_120d} |\n")
            
            section.append("\n---\n\n")
        
        # --- Add Technical Interpretation ---
        section.append("\\n### Technical Interpretation\\n")
        technical_summary = generate_technical_summary(symbol)
        section.append(technical_summary)
        # ------------------------------------

        section.append("\\n### Instability Analysis\\n")
        instability_narrative = INSTABILITY_NARRATIVES.get(current_regime, {}).get(instability, "No specific narrative for this combination.")
        section.append(instability_narrative)

        return "".join(section)

    except Exception as e:
        print(f"    - Error processing signal file for {symbol}: {e}")
        return None

if __name__ == '__main__':
    # This allows the script to be run directly for testing purposes.
    generate_report() 
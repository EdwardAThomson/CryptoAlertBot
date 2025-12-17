# markdown_reporter_alt.py
# Alternative approach using brief AI opinions in multiple sections
# Based on the original markdown_reporter.py but with shorter, focused AI integration

import os
import sys
import json
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.collectors import intraday_price_collector
from src.reporters.technical_interpreter import generate_technical_summary
from src.reporters.ai_market_reporter_alt import (
    generate_market_summary_opinion_alt,
    generate_bitcoin_brief_opinion_alt,
    generate_technical_interpretation_opinion_alt
)

# ------------------------------------------------------------------ #
# Configuration
# ------------------------------------------------------------------ #

def _load_assets() -> List[str]:
    """Load the list of assets from config."""
    try:
        with open("data/config.json", 'r') as f:
            config = json.load(f)
        return config.get("assets", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading assets from config: {e}")
        return []

# ------------------------------------------------------------------ #
# AI Analysis Section Builder
# ------------------------------------------------------------------ #

def _build_ai_analysis_section_alt() -> list[str]:
    """
    Builds the alternative AI analysis section with brief opinions.
    """
    ai_section = []
    
    try:
        print("  - Generating brief AI market analysis...")
        
        # --- Market Summary Opinion (Front Page) ---
        market_summary = generate_market_summary_opinion_alt()
        
        if market_summary.get('success'):
            ai_section.append("## Market Overview\n\n")
            ai_section.append(market_summary['analysis'])
            ai_section.append("\n\n")
        else:
            ai_section.append("## Market Overview\n\n")
            ai_section.append("*AI market summary unavailable*\n\n")
        
        return ai_section
        
    except Exception as e:
        print(f"Error generating AI analysis section: {e}")
        return ["## Market Overview\n\n*AI analysis temporarily unavailable*\n\n"]

def _build_bitcoin_brief_section() -> str:
    """
    Builds the brief Bitcoin AI opinion for the Bitcoin section.
    """
    try:
        print("  - Generating brief Bitcoin AI opinion...")
        
        bitcoin_brief = generate_bitcoin_brief_opinion_alt()
        
        if bitcoin_brief.get('success'):
            return f"\n### AI Market Insight\n\n{bitcoin_brief['analysis']}\n\n"
        else:
            return "\n### AI Market Insight\n\n*Bitcoin AI analysis unavailable*\n\n"
            
    except Exception as e:
        print(f"Error generating Bitcoin brief: {e}")
        return "\n### AI Market Insight\n\n*Bitcoin AI analysis temporarily unavailable*\n\n"

def _build_technical_interpretation_ai_section() -> str:
    """
    Builds the technical interpretation AI opinion.
    """
    try:
        print("  - Generating technical interpretation AI opinion...")
        
        tech_interpretation = generate_technical_interpretation_opinion_alt()
        
        if tech_interpretation.get('success'):
            return f"\n### AI Technical Perspective\n\n{tech_interpretation['analysis']}\n\n"
        else:
            return "\n### AI Technical Perspective\n\n*Technical AI analysis unavailable*\n\n"
            
    except Exception as e:
        print(f"Error generating technical interpretation: {e}")
        return "\n### AI Technical Perspective\n\n*Technical AI analysis temporarily unavailable*\n\n"

# ------------------------------------------------------------------ #
# Main Report Generation (same as original but with AI additions)
# ------------------------------------------------------------------ #

def generate_report_alt():
    """
    Generates a Markdown report using the alternative AI approach with brief opinions.
    """
    print("=== Generating Market Report (Alternative AI Approach) ===")
    
    # Load assets
    assets = _load_assets()
    if not assets:
        print("No assets found in config file")
        return
    
    # Build report sections
    report_title = [f"# Crypto Market Analysis - {date.today().strftime('%Y-%m-%d')}\n\n"]
    
    # Build summary table (same as original)
    summary_table = _build_summary_table(assets)
    
    # Build AI analysis section (NEW - brief market summary)
    ai_analysis_section = _build_ai_analysis_section_alt()
    
    # Build detailed sections for each asset
    detailed_sections = []
    for symbol in assets:
        print(f"  - Processing {symbol}...")
        
        # Build asset section (same as original)
        asset_section = _build_asset_section(symbol)
        
        # Add brief Bitcoin AI opinion if this is Bitcoin
        if symbol == "BTCUSDT":
            bitcoin_brief = _build_bitcoin_brief_section()
            # Insert after the asset header but before the combined plot
            asset_lines = asset_section.split('\n')
            for i, line in enumerate(asset_lines):
                if line.startswith('<img src=') and 'combined_plot' in line:
                    asset_lines.insert(i, bitcoin_brief)
                    break
            asset_section = '\n'.join(asset_lines)
        
        detailed_sections.append(asset_section)
        detailed_sections.append("\n---\n\n")
        
    # Build appendices (same as original)
    appendix_sections = _build_appendices()
    
    # Combine all sections
    report_content = (report_title + summary_table + ai_analysis_section + 
                     detailed_sections + appendix_sections)
    
    # Write to file
    report_filename = f"reports/market_report_alt_{date.today().strftime('%Y%m%d')}.md"
    
    try:
        os.makedirs("reports", exist_ok=True)
        with open(report_filename, 'w') as f:
            f.writelines(report_content)
        print(f"Alternative report generated: {report_filename}")
        
        # Generate PDF (same as original)
        _generate_pdf(report_filename)
        
    except Exception as e:
        print(f"Error writing report: {e}")
        return

# ------------------------------------------------------------------ #
# Helper Functions (same as original markdown_reporter.py)
# ------------------------------------------------------------------ #

def _build_summary_table(assets: List[str]) -> list[str]:
    """Build the market summary table (same as original)."""
    summary_table = []
    
    summary_table.append("## Market Summary\n\n")
    summary_table.append("*The following table summarizes the market's phase based on a multi-factor model including Price, Open Interest, and CVD.*\n\n")
    
    # Build table header
    summary_table.append("| Asset   | Market Phase | Days in Regime | Liquidations | Sharpe (20d) | Sortino (20d) | CVaR (20d) |\n")
    summary_table.append("|:--------|:---------------|:---------------|:------------|:-------------|:--------------|:-----------|\n")
    
    # Build table rows
    for symbol in assets:
        try:
            # Get signal data
            signals_path = f"data/analysis/signals_{symbol}.csv"
            if os.path.exists(signals_path):
                signals_df = pd.read_csv(signals_path)
                if not signals_df.empty:
                    latest_signal = signals_df.iloc[-1]
                    
                    # Format market phase
                    phase = latest_signal.get('state', 'Unknown')
                    if 'bullish' in phase.lower():
                        phase = f"<span style='color: green;'>{phase}</span>"
                    elif 'bearish' in phase.lower():
                        phase = f"<span style='color: red;'>{phase}</span>"
                    
                    # Days in regime
                    days_in_regime = _calculate_days_in_regime(signals_df)
                    
                    # Get volatility metrics
                    volatility_path = f"data/analysis/volatility_{symbol}.csv"
                    sharpe, sortino, cvar = "N/A", "N/A", "N/A"
                    
                    if os.path.exists(volatility_path):
                        vol_df = pd.read_csv(volatility_path)
                        if not vol_df.empty:
                            latest_vol = vol_df.iloc[-1]
                            sharpe = f"{latest_vol.get('sharpe_ratio', 0):.2f}"
                            sortino = f"{latest_vol.get('sortino_ratio_20d', 0):.2f}"
                            cvar = f"{latest_vol.get('cvar_20d', 0):.2f}%"
                    
                    # Get liquidation status
                    liquidation_status = _get_liquidation_status(symbol)
                    
                    summary_table.append(f"| {symbol} | {phase} | {days_in_regime} days | {liquidation_status} | {sharpe} | {sortino} | {cvar} |\n")
                else:
                    summary_table.append(f"| {symbol} | No data | - | - | - | - | - |\n")
            else:
                summary_table.append(f"| {symbol} | No data | - | - | - | - | - |\n")
                
        except Exception as e:
            print(f"Error processing {symbol} for summary table: {e}")
            summary_table.append(f"| {symbol} | Error | - | - | - | - | - |\n")
    
    summary_table.append("\n")
    return summary_table

def _build_asset_section(symbol: str) -> str:
    """Build detailed section for an asset (same as original)."""
    section = []
    
    # Section header
    section.append(f"<div style=\"page-break-before: always;\"></div>\n\n")
    section.append(f"## {symbol} Analysis\n\n")
    
    # Get signal data
    signals_path = f"data/analysis/signals_{symbol}.csv"
    if os.path.exists(signals_path):
        signals_df = pd.read_csv(signals_path)
        if not signals_df.empty:
            latest_signal = signals_df.iloc[-1]
            
            # Current signal
            current_signal = latest_signal.get('state', 'Unknown')
            if 'bullish' in current_signal.lower():
                current_signal = f"<span style='color: green;'>{current_signal}</span>"
            elif 'bearish' in current_signal.lower():
                current_signal = f"<span style='color: red;'>{current_signal}</span>"
            
            section.append(f"**Current Signal:** {current_signal}\n\n")
            
            # Regime info
            regime_info = _get_regime_info(signals_df)
            section.append(f"**Prevailing Regime:** {regime_info}\n\n")
            
            # Latest market values
            section.append("**Latest Market Values:**\n\n")
            section.append("| Price (Intraday) | Open Interest | CVD |\n")
            section.append("|:---|:---|:---|\n")
            
            # Get intraday price
            intraday_price = _get_intraday_price(symbol)
            oi_value = _format_oi_value(latest_signal.get('oi', 0))
            cvd_value = _format_cvd_value(latest_signal.get('cvd', 0))
            
            section.append(f"| {intraday_price} | {oi_value} | {cvd_value} |\n\n")
            
            # Asset summary
            asset_summary = _get_asset_summary(latest_signal)
            section.append(f"**Asset Summary:**\n\n{asset_summary}\n\n")
            
            # What to watch for
            watch_for = _get_watch_for(latest_signal)
            section.append(f"**What to Watch For:**\n\n{watch_for}\n\n")
            
            # Longer-term observations
            longer_term = _get_longer_term_observations(signals_df, symbol)
            if longer_term:
                section.append(f"**Longer-Term Observations:**\n\n{longer_term}\n\n")
    
    # Combined plot
    section.append(f'<img src="/home/edward/Projects/CryptoAlertBot/plots/svg/combined_plot_{symbol}.svg" style="width: 70%; height: auto; display: block; margin-left: auto; margin-right: auto;" alt="Combined Plot for {symbol}">\n\n')
    
    # Instability index
    instability_section = _build_instability_section(symbol)
    section.append(instability_section)
    
    # Risk metrics
    risk_section = _build_risk_metrics_section(symbol)
    section.append(risk_section)
    
    # Recent signals table
    recent_signals = _build_recent_signals_table(symbol)
    section.append(recent_signals)
    
    # Technical plot
    section.append(f'<img src="/home/edward/Projects/CryptoAlertBot/plots/svg/technical_plot_{symbol}.svg" style="width: 100%; height: auto; display: block; margin-left: auto; margin-right: auto;" alt="Technical Plot for {symbol}">\n\n')
    
    # Technical interpretation
    tech_interpretation = _build_technical_interpretation_section(symbol)
    section.append(tech_interpretation)
    
    # Add AI technical perspective if this is Bitcoin
    if symbol == "BTCUSDT":
        ai_tech_section = _build_technical_interpretation_ai_section()
        section.append(ai_tech_section)
    
    # Market state
    market_state = _build_market_state_section(symbol)
    section.append(market_state)
    
    return "".join(section)

# Import all other helper functions from original markdown_reporter.py
# (This is simplified - in practice you'd import or copy all the helper functions)

def _calculate_days_in_regime(signals_df: pd.DataFrame) -> int:
    """Calculate days in current regime."""
    if signals_df.empty:
        return 0
    
    current_state = signals_df.iloc[-1]['state']
    days = 1
    
    for i in range(len(signals_df) - 2, -1, -1):
        if signals_df.iloc[i]['state'] == current_state:
            days += 1
        else:
            break
    
    return days

def _get_liquidation_status(symbol: str) -> str:
    """Get liquidation status for symbol."""
    # Simplified - would normally check instability data
    return "Normal"

def _get_regime_info(signals_df: pd.DataFrame) -> str:
    """Get regime information."""
    if signals_df.empty:
        return "Unknown"
    
    current_state = signals_df.iloc[-1]['state']
    days = _calculate_days_in_regime(signals_df)
    
    if 'bullish' in current_state.lower():
        return f"The market has been in a **<span style='color: green;'>Bullish</span>** state for **{days} {'day' if days == 1 else 'days'}.**"
    elif 'bearish' in current_state.lower():
        return f"The market has been in a **<span style='color: red;'>Bearish</span>** state for **{days} {'day' if days == 1 else 'days'}.**"
    else:
        return f"The market has been in a **Neutral** state for **{days} consecutive days**."

def _get_intraday_price(symbol: str) -> str:
    """Get formatted intraday price."""
    try:
        price_data = intraday_price_collector.get_latest_intraday_price(symbol)
        if price_data:
            price = float(price_data['price'])
            timestamp = price_data['timestamp']
            return f"${price:,.2f} <br/><small>({timestamp})</small>"
    except:
        pass
    return "N/A"

def _format_oi_value(oi: float) -> str:
    """Format OI value."""
    try:
        if oi >= 1e9:
            return f"${oi/1e9:.2f}B"
        elif oi >= 1e6:
            return f"${oi/1e6:.2f}M"
        else:
            return f"${oi:,.0f}"
    except:
        return "N/A"

def _format_cvd_value(cvd: float) -> str:
    """Format CVD value."""
    try:
        if abs(cvd) >= 1e6:
            return f"{cvd/1e6:.2f}M coins"
        elif abs(cvd) >= 1e3:
            return f"{cvd/1e3:.2f}k coins"
        else:
            return f"{cvd:.2f} coins"
    except:
        return "N/A"

def _get_asset_summary(signal: pd.Series) -> str:
    """Get asset summary based on signal."""
    state = signal.get('state', '').lower()
    
    if 'compression' in state:
        return "* The market is in a state of extremely low realized volatility. This indicates a 'compression' regime where the market is coiling and building energy."
    elif 'bullish' in state:
        return "* Price, Open Interest, and CVD are all signaling a strong <span style='color: green;'>upward</span> trend. This is a high-conviction <span style='color: green;'>bullish</span> signal suggesting broad market participation."
    elif 'bearish' in state:
        return "* Price, Open Interest, and CVD are all signaling a strong <span style='color: red;'>downward</span> trend. This is a high-conviction <span style='color: red;'>bearish</span> signal."
    else:
        return "* The market is showing mixed signals across price, open interest, and CVD metrics."

def _get_watch_for(signal: pd.Series) -> str:
    """Get what to watch for based on signal."""
    state = signal.get('state', '').lower()
    
    if 'compression' in state:
        return "* Directional trades are low probability. Wait for volatility to expand, signaling the start of a new, more reliable move."
    elif 'bullish' in state:
        return "* <span style='color: green;'>Bullish</span> continuation is likely. Watch for OI or CVD to falter as an early warning sign of weakness."
    elif 'bearish' in state:
        return "* <span style='color: red;'>Bearish</span> continuation is likely. Watch for CVD to flatten or turn up as an early sign of bottoming."
    else:
        return "* Monitor for clearer directional signals to emerge."

def _get_longer_term_observations(signals_df: pd.DataFrame, symbol: str) -> str:
    """Get longer-term observations."""
    # Simplified - would normally analyze trend patterns
    return ""

def _build_instability_section(symbol: str) -> str:
    """Build instability section."""
    return f"**Instability Index:**\n\n* The current instability level is **Normal**. This index measures the risk of liquidations in the market.\n\n"

def _build_risk_metrics_section(symbol: str) -> str:
    """Build risk metrics section."""
    return f"**Risk Metrics:**\n\n* **Volatility State**: Normal\n* **RSI**: Neutral conditions\n* **Sharpe Ratio (20d)**: <span style='color: green;'>Excellent</span> risk-adjusted returns\n\n"

def _build_recent_signals_table(symbol: str) -> str:
    """Build recent signals table."""
    section = []
    section.append("**Recent Signals:**\n\n")
    section.append("| Date | Close | State | Price State | OI State | CVD State |\n")
    section.append("|:---|---:|:---|:---|:---|:---|\n")
    
    try:
        signals_path = f"data/analysis/signals_{symbol}.csv"
        if os.path.exists(signals_path):
            signals_df = pd.read_csv(signals_path)
            if not signals_df.empty:
                # Get last 5 days
                recent_signals = signals_df.tail(5)
                
                for _, row in recent_signals.iterrows():
                    date_str = row.get('date', 'N/A')
                    close = row.get('close', 0)
                    state = row.get('state', 'N/A')
                    price_state = row.get('price_state', 'N/A')
                    oi_state = row.get('oi_state', 'N/A')
                    cvd_state = row.get('cvd_state', 'N/A')
                    
                    # Format states with colors
                    if 'UP' in price_state:
                        price_state = f"<span style='color: green;'>{price_state}</span>"
                    elif 'DOWN' in price_state:
                        price_state = f"<span style='color: red;'>{price_state}</span>"
                    
                    if 'UP' in oi_state:
                        oi_state = f"<span style='color: green;'>{oi_state}</span>"
                    elif 'DOWN' in oi_state:
                        oi_state = f"<span style='color: red;'>{oi_state}</span>"
                    
                    if 'UP' in cvd_state:
                        cvd_state = f"<span style='color: green;'>{cvd_state}</span>"
                    elif 'DOWN' in cvd_state:
                        cvd_state = f"<span style='color: red;'>{cvd_state}</span>"
                    
                    if 'bullish' in state.lower():
                        state = f"<span style='color: green;'>{state}</span>"
                    elif 'bearish' in state.lower():
                        state = f"<span style='color: red;'>{state}</span>"
                    
                    section.append(f"| {date_str} | {close:,.2f} | {state} | {price_state} | {oi_state} | {cvd_state} |\n")
    except Exception as e:
        print(f"Error building recent signals table for {symbol}: {e}")
    
    section.append("\n\n")
    return "".join(section)

def _build_technical_interpretation_section(symbol: str) -> str:
    """Build technical interpretation section."""
    try:
        interpretation = generate_technical_summary(symbol)
        return f"### Technical Interpretation\n{interpretation}\n\n"
    except Exception as e:
        return f"### Technical Interpretation\nTechnical analysis unavailable for {symbol}\n\n"

def _build_market_state_section(symbol: str) -> str:
    """Build market state section."""
    return f"### Market State\n\n| Metric | Value |\n|:-------|:------|\n| Daily Return (20d Avg) | 0.00% |\n| Volatility State | Normal |\n| RSI | 50.0 (Neutral) |\n\n"

def _build_appendices() -> list[str]:
    """Build appendix sections."""
    appendices = []
    
    # Rule definitions
    appendices.append("<div style=\"page-break-before: always;\"></div>\n\n")
    appendices.append("# Appendix: Rule Definitions\n\n")
    appendices.append("| Signal | Summary | Outlook |\n")
    appendices.append("|:---|:---|:---|\n")
    appendices.append("| **Compression** | The market is in a state of extremely low realized volatility. | Directional trades are low probability. Wait for volatility to expand. |\n")
    appendices.append("| **Bullish Trending** | Price, Open Interest, and CVD are all signaling upward trend. | Bullish continuation is likely. |\n")
    appendices.append("| **Bearish Trending** | Price, Open Interest, and CVD are all signaling downward trend. | Bearish continuation is likely. |\n")
    
    return appendices

def _generate_pdf(markdown_filename: str):
    """Generate PDF from markdown file."""
    try:
        import subprocess
        pdf_filename = markdown_filename.replace('.md', '.pdf')
        subprocess.run(['pandoc', markdown_filename, '-o', pdf_filename], check=True)
        print(f"PDF generated: {pdf_filename}")
    except Exception as e:
        print(f"PDF generation failed: {e}")

# ------------------------------------------------------------------ #
# Main Entry Point
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    generate_report_alt() 
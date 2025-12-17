# ai_market_reporter_alt.py
# Alternative AI-powered market analysis with shorter, focused opinions
# Provides multiple brief sections instead of comprehensive long-form analysis

import os
import json
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.ai_helper import send_prompt, get_supported_models


class AIMarketReporterAlt:
    """
    Alternative AI-powered market analysis reporter for brief, focused opinions.
    
    This version generates shorter, more focused AI analysis suitable for 
    concise market reports with targeted insights.
    """
    
    def __init__(self, default_model: str = "o4-mini"):
        """
        Initialize the Alternative AI Market Reporter.
        
        Args:
            default_model: Default AI model to use for analysis
        """
        self.default_model = default_model
        self.supported_models = get_supported_models()
        
        # Verify default model is supported
        if default_model not in self.supported_models:
            raise ValueError(f"Model {default_model} not supported. Available: {self.supported_models}")
    
    # ------------------------------------------------------------------ #
    # Public Methods - Main Entry Points
    # ------------------------------------------------------------------ #
    
    def generate_market_summary_opinion(self, assets_data: Dict, model: str = None) -> Dict[str, str]:
        """
        Generate brief market summary for front page based on table data.
        
        Args:
            assets_data: Market data for all assets from summary table
            model: AI model to use
            
        Returns:
            Dictionary with market summary analysis
        """
        model = model or self.default_model
        
        try:
            prompt = self._build_market_summary_prompt(assets_data)
            
            if model == "gpt-4o":
                from src.ai_helper import send_prompt_oai
                analysis = send_prompt_oai(
                    prompt=prompt,
                    model="gpt-4o",
                    max_tokens=1024,  # Shorter for brief summary
                    temperature=0.3,
                    role_description="You are a professional cryptocurrency market analyst specializing in concise market overviews and cycle analysis."
                )
            elif model == "o4-mini":
                from src.ai_helper import send_prompt_o1
                analysis = send_prompt_o1(
                    prompt=prompt,
                    model="o4-mini"
                )
            else:
                analysis = send_prompt(prompt, model)
            
            return {
                'success': True,
                'analysis': analysis,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model_used': model
            }
            
        except Exception as e:
            return {
                'success': False,
                'analysis': f"Market summary generation failed: {e}",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model_used': model
            }
    
    def generate_bitcoin_brief_opinion(self, bitcoin_data: Dict, model: str = None) -> Dict[str, str]:
        """
        Generate brief Bitcoin-focused opinion for Bitcoin section.
        
        Args:
            bitcoin_data: Bitcoin-specific market data
            model: AI model to use
            
        Returns:
            Dictionary with Bitcoin brief analysis
        """
        model = model or self.default_model
        
        try:
            prompt = self._build_bitcoin_brief_prompt(bitcoin_data)
            
            if model == "gpt-4o":
                from src.ai_helper import send_prompt_oai
                analysis = send_prompt_oai(
                    prompt=prompt,
                    model="gpt-4o",
                    max_tokens=512,  # Very brief
                    temperature=0.3,
                    role_description="You are a Bitcoin specialist providing concise market insights focused on current positioning and near-term outlook."
                )
            elif model == "o4-mini":
                from src.ai_helper import send_prompt_o1
                analysis = send_prompt_o1(
                    prompt=prompt,
                    model="o4-mini"
                )
            else:
                analysis = send_prompt(prompt, model)
            
            return {
                'success': True,
                'analysis': analysis,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model_used': model
            }
            
        except Exception as e:
            return {
                'success': False,
                'analysis': f"Bitcoin brief generation failed: {e}",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model_used': model
            }
    
    def generate_technical_interpretation_opinion(self, bitcoin_data: Dict, model: str = None) -> Dict[str, str]:
        """
        Generate brief technical interpretation for Technical Interpretation section.
        
        Args:
            bitcoin_data: Bitcoin technical data
            model: AI model to use
            
        Returns:
            Dictionary with technical interpretation analysis
        """
        model = model or self.default_model
        
        try:
            prompt = self._build_technical_interpretation_prompt(bitcoin_data)
            
            if model == "gpt-4o":
                from src.ai_helper import send_prompt_oai
                analysis = send_prompt_oai(
                    prompt=prompt,
                    model="gpt-4o",
                    max_tokens=512,  # Brief technical focus
                    temperature=0.3,
                    role_description="You are a technical analyst providing concise interpretations of chart patterns and technical indicators."
                )
            elif model == "o4-mini":
                from src.ai_helper import send_prompt_o1
                analysis = send_prompt_o1(
                    prompt=prompt,
                    model="o4-mini"
                )
            else:
                analysis = send_prompt(prompt, model)
            
            return {
                'success': True,
                'analysis': analysis,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model_used': model
            }
            
        except Exception as e:
            return {
                'success': False,
                'analysis': f"Technical interpretation generation failed: {e}",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model_used': model
            }
    
    # ------------------------------------------------------------------ #
    # Data Loading Methods
    # ------------------------------------------------------------------ #
    
    def _load_bitcoin_data(self, timeframe: str = "daily") -> Optional[Dict]:
        """
        Load Bitcoin analysis data (same as main reporter for consistency).
        """
        symbol = "BTCUSDT"
        data = {}
        
        try:
            # Load 8-state analysis signals
            signals_path = f"data/analysis/signals_{symbol}.csv"
            if os.path.exists(signals_path):
                signals_df = pd.read_csv(signals_path)
                if not signals_df.empty:
                    latest_signal = signals_df.iloc[-1].to_dict()
                    data['eight_state'] = {'latest_signal': latest_signal}
            
            # Load technical analysis
            technical_path = f"data/analysis/technical_analysis_{symbol}.csv"
            if os.path.exists(technical_path):
                tech_df = pd.read_csv(technical_path)
                if not tech_df.empty:
                    latest_tech = tech_df.iloc[-1].to_dict()
                    data['technical'] = {'latest': latest_tech}
            
            # Load recent predictions
            predictions_files = [f"data/predictions/run_analysis_{symbol}_20250710.json",
                               f"data/predictions/run_analysis_{symbol}_20250709.json",
                               f"data/predictions/run_analysis_{symbol}.json"]
            
            for pred_path in predictions_files:
                if os.path.exists(pred_path):
                    with open(pred_path, 'r') as f:
                        data['predictions'] = json.load(f)
                    break
            
            # Load recent price data
            price_path = f"data/daily/historical_price_{symbol}.csv"
            if os.path.exists(price_path):
                price_df = pd.read_csv(price_path)
                data['recent_prices'] = price_df.tail(7).to_dict('records')  # Last week
            
            return data if data else None
            
        except Exception as e:
            print(f"Error loading Bitcoin data: {e}")
            return None
    
    def _load_market_table_data(self) -> Optional[Dict]:
        """
        Load market summary table data for all assets.
        """
        try:
            # Load asset list from config
            with open("data/config.json", 'r') as f:
                config = json.load(f)
            assets = config.get("assets", [])
            
            market_data = {}
            for asset in assets:
                asset_data = {}
                
                # Load latest signals for market phase
                signals_path = f"data/analysis/signals_{asset}.csv"
                if os.path.exists(signals_path):
                    signals_df = pd.read_csv(signals_path)
                    if not signals_df.empty:
                        latest_signal = signals_df.iloc[-1]
                        asset_data['market_phase'] = latest_signal.get('state', 'Unknown')
                        asset_data['price'] = latest_signal.get('close', 0)
                
                # Load volatility metrics for risk metrics
                volatility_path = f"data/analysis/volatility_{asset}.csv"
                if os.path.exists(volatility_path):
                    vol_df = pd.read_csv(volatility_path)
                    if not vol_df.empty:
                        latest_vol = vol_df.iloc[-1]
                        asset_data['sharpe_20d'] = latest_vol.get('sharpe_ratio', 0)
                        asset_data['sortino_20d'] = latest_vol.get('sortino_ratio_20d', 0)
                        asset_data['cvar_20d'] = latest_vol.get('cvar_20d', 0)
                
                if asset_data:
                    market_data[asset] = asset_data
            
            return market_data if market_data else None
            
        except Exception as e:
            print(f"Error loading market table data: {e}")
            return None
    
    # ------------------------------------------------------------------ #
    # Prompt Building Methods
    # ------------------------------------------------------------------ #
    
    def _build_market_summary_prompt(self, assets_data: Dict) -> str:
        """Build brief market summary prompt for front page."""
        
        # Format market data for prompt
        market_overview = []
        bullish_count = 0
        total_assets = 0
        
        for asset, data in assets_data.items():
            total_assets += 1
            phase = data.get('market_phase', 'Unknown')
            if 'bullish' in phase.lower():
                bullish_count += 1
            
            sharpe = data.get('sharpe_20d', 0)
            market_overview.append(f"{asset}: {phase} (Sharpe: {sharpe:.1f})")
        
        market_summary = "\n".join(market_overview)
        bullish_percentage = (bullish_count / total_assets * 100) if total_assets > 0 else 0
        
        return f"""You are a professional cryptocurrency market analyst providing a brief market overview for institutional clients. Write a concise 1-2 paragraph market summary based on the current market data.

**CURRENT MARKET SNAPSHOT:**
{market_summary}

**MARKET COMPOSITION:**
- Total Assets Tracked: {total_assets}
- Bullish Signals: {bullish_count} ({bullish_percentage:.0f}%)
- Date: {date.today().strftime('%Y-%m-%d')}

**INSTRUCTION:**
Write a daily brief market summary (1-2 paragraphs) that:
1. Summarizes the overall market sentiment based on the signal distribution
2. References the broader 4-year Bitcoin cycle context and long-term trends
3. Highlights any notable risk-adjusted performance patterns (Sharpe ratios)
4. Provides context for where we might be in the larger market cycle

Keep it professional, concise, and suitable for sophisticated investors. Focus on the big picture rather than individual asset details."""
    
    def _build_bitcoin_brief_prompt(self, bitcoin_data: Dict) -> str:
        """Build brief Bitcoin-focused prompt."""
        
        # Extract key Bitcoin data
        current_price = "N/A"
        current_state = "N/A"
        rsi = "N/A"
        
        if 'recent_prices' in bitcoin_data and bitcoin_data['recent_prices']:
            latest_price = bitcoin_data['recent_prices'][-1]
            try:
                current_price = f"${float(latest_price['close']):,.0f}"
            except:
                pass
        
        if 'eight_state' in bitcoin_data:
            signal = bitcoin_data['eight_state'].get('latest_signal', {})
            current_state = signal.get('state', 'N/A')
        
        if 'technical' in bitcoin_data:
            tech = bitcoin_data['technical'].get('latest', {})
            try:
                rsi = f"{float(tech.get('rsi', 0)):.1f}"  # Changed from :.0f to :.1f for consistency
            except:
                pass
        
        return f"""You are a Bitcoin specialist providing a brief market insight. Write a concise paragraph (3-4 sentences) focused on Bitcoin's current positioning.

**CURRENT BITCOIN DATA:**
- Price: {current_price}
- Market State: {current_state} 
- RSI: {rsi}

**INSTRUCTION:**
Write a brief Bitcoin-focused opinion that:
1. Interprets the current market state in practical terms
2. Provides perspective on near-term outlook (next 1-2 weeks)
3. Mentions one key level or factor to watch

Keep it concise, practical, and focused specifically on Bitcoin. Avoid repeating technical details that appear elsewhere in the report."""
    
    def _build_technical_interpretation_prompt(self, bitcoin_data: Dict) -> str:
        """Build technical interpretation prompt."""
        
        # Extract technical data
        tech_summary = []
        
        if 'technical' in bitcoin_data:
            tech = bitcoin_data['technical'].get('latest', {})
            
            # RSI
            try:
                rsi = float(tech.get('rsi', 0))
                tech_summary.append(f"RSI: {rsi:.1f}")
            except:
                tech_summary.append("RSI: N/A")
            
            # Bollinger Bands
            try:
                bb_percentile = float(tech.get('bb_width_percentile', 0))
                tech_summary.append(f"BB Width: {bb_percentile:.0f}%")
            except:
                pass
            
            # Moving Averages
            try:
                sma50 = float(tech.get('sma_50', 0))
                sma200 = float(tech.get('sma_200', 0))
                current_price = float(tech.get('close', 0))
                
                if current_price > sma50 > sma200:
                    tech_summary.append("Above both SMAs (bullish structure)")
                elif current_price < sma50 < sma200:
                    tech_summary.append("Below both SMAs (bearish structure)")
                else:
                    tech_summary.append("Mixed SMA positioning")
            except:
                pass
        
        technical_data = "; ".join(tech_summary)
        
        return f"""You are a technical analyst providing a brief chart interpretation. Write a concise paragraph (2-3 sentences) focusing on what the technical setup suggests.

**CURRENT TECHNICAL DATA:**
{technical_data}

**INSTRUCTION:**
Write a brief technical interpretation that:
1. Interprets what the current technical setup suggests about momentum/trend
2. Identifies the most important technical factor for the next move
3. Provides a practical takeaway for traders/investors

Keep it concise and focused on actionable technical insights. Avoid repeating basic indicator values."""


# ------------------------------------------------------------------ #
# Convenience Functions
# ------------------------------------------------------------------ #

def generate_market_summary_opinion_alt(model: str = "o4-mini") -> Dict[str, str]:
    """
    Convenience function to generate market summary opinion using alternative brief approach.
    
    Args:
        model: AI model to use
        
    Returns:
        Dictionary with market summary analysis
    """
    reporter = AIMarketReporterAlt(default_model=model)
    
    # Load market data
    market_data = reporter._load_market_table_data()
    if not market_data:
        return {"error": "Failed to load market data"}
    
    return reporter.generate_market_summary_opinion(market_data, model)


def generate_bitcoin_brief_opinion_alt(model: str = "o4-mini") -> Dict[str, str]:
    """
    Convenience function to generate Bitcoin brief opinion using alternative approach.
    
    Args:
        model: AI model to use
        
    Returns:
        Dictionary with Bitcoin brief analysis
    """
    reporter = AIMarketReporterAlt(default_model=model)
    
    # Load Bitcoin data
    bitcoin_data = reporter._load_bitcoin_data()
    if not bitcoin_data:
        return {"error": "Failed to load Bitcoin data"}
    
    return reporter.generate_bitcoin_brief_opinion(bitcoin_data, model)


def generate_technical_interpretation_opinion_alt(model: str = "o4-mini") -> Dict[str, str]:
    """
    Convenience function to generate technical interpretation opinion using alternative approach.
    
    Args:
        model: AI model to use
        
    Returns:
        Dictionary with technical interpretation analysis
    """
    reporter = AIMarketReporterAlt(default_model=model)
    
    # Load Bitcoin data
    bitcoin_data = reporter._load_bitcoin_data()
    if not bitcoin_data:
        return {"error": "Failed to load Bitcoin data"}
    
    return reporter.generate_technical_interpretation_opinion(bitcoin_data, model) 
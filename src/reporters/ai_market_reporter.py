# ai_market_reporter.py
# AI-powered market analysis and opinion generation
# Integrates with existing data analysis and ai_helper module

import os
import json
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.ai_helper import send_prompt, get_supported_models


class AIMarketReporter:
    """
    AI-powered market analysis reporter for cryptocurrency data.
    
    This class integrates with various AI models to provide intelligent analysis
    of cryptocurrency market data, including technical analysis, market sentiment,
    and actionable investment insights.
    """
    
    def __init__(self, default_model: str = "o3"):
        """
        Initialize the AI Market Reporter.
        
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
    
    def generate_bitcoin_analysis(self, model: str = None, timeframe: str = "daily") -> Dict[str, str]:
        """
        Generate comprehensive AI analysis for Bitcoin across multiple timeframes.
        
        Args:
            model: AI model to use (defaults to class default)
            timeframe: Analysis timeframe ("daily", "weekly", "monthly")
            
        Returns:
            Dictionary containing different analysis sections
        """
        model = model or self.default_model
        
        # Load all relevant data for Bitcoin
        market_data = self._load_bitcoin_data(timeframe)
        
        if not market_data:
            return {"error": "Unable to load Bitcoin market data"}
        
        # Generate different analysis perspectives
        analysis = {
            "analyst_view": self._generate_analyst_opinion(market_data, model),
            "advisor_view": self._generate_advisor_opinion(market_data, model),
            "risk_assessment": self._generate_risk_assessment(market_data, model),
            "key_factors": self._generate_key_factors(market_data, model),
            "timeframe": timeframe,
            "generated_at": datetime.now().isoformat(),
            "model_used": model
        }
        
        return analysis
    
    def generate_market_summary(self, model: str = None) -> str:
        """
        Generate a high-level market summary across all tracked assets.
        
        Args:
            model: AI model to use
            
        Returns:
            AI-generated market summary text
        """
        model = model or self.default_model
        
        # Load multi-asset data
        assets_data = self._load_all_assets_data()
        
        if not assets_data:
            return "Unable to generate market summary - no data available"
        
        # Generate summary
        summary = self._generate_market_summary(assets_data, model)
        return summary
    
    # ------------------------------------------------------------------ #
    # Data Loading Methods
    # ------------------------------------------------------------------ #
    
    def _load_bitcoin_data(self, timeframe: str = "daily") -> Optional[Dict]:
        """
        Load all available Bitcoin analysis data.
        
        Args:
            timeframe: Data timeframe to load
            
        Returns:
            Dictionary containing all loaded data or None if failed
        """
        symbol = "BTCUSDT"
        data = {}
        
        try:
            # Load 8-state analysis signals (from CSV)
            signals_path = f"data/analysis/signals_{symbol}.csv"
            if os.path.exists(signals_path):
                signals_df = pd.read_csv(signals_path)
                if not signals_df.empty:
                    latest_signal = signals_df.iloc[-1].to_dict()
                    data['eight_state'] = {'latest_signal': latest_signal}
            
            # Load instability analysis
            instability_path = f"data/analysis/instability_{symbol}.csv"
            if os.path.exists(instability_path):
                instability_df = pd.read_csv(instability_path, names=['date', 'liquidation_value', 'status'])
                data['instability'] = instability_df.tail(30).to_dict('records')
            
            # Load volatility analysis
            volatility_path = f"data/analysis/volatility_{symbol}.csv"
            if os.path.exists(volatility_path):
                volatility_df = pd.read_csv(volatility_path)
                data['volatility'] = volatility_df.tail(30).to_dict('records')
            
            # Load technical analysis (from CSV)
            technical_path = f"data/analysis/technical_analysis_{symbol}.csv"
            if os.path.exists(technical_path):
                tech_df = pd.read_csv(technical_path)
                if not tech_df.empty:
                    latest_tech = tech_df.iloc[-1].to_dict()
                    data['technical'] = {'latest': latest_tech}
            
            # Load recent predictions
            # Try to find the most recent prediction file
            predictions_files = [f"data/predictions/run_analysis_{symbol}_20250710.json",
                               f"data/predictions/run_analysis_{symbol}_20250709.json",
                               f"data/predictions/run_analysis_{symbol}.json"]
            
            for pred_path in predictions_files:
                if os.path.exists(pred_path):
                    with open(pred_path, 'r') as f:
                        data['predictions'] = json.load(f)
                    break
            
            # Load recent price data for context (from historical prices)
            price_path = f"data/daily/historical_price_{symbol}.csv"
            if os.path.exists(price_path):
                price_df = pd.read_csv(price_path)
                data['recent_prices'] = price_df.tail(14).to_dict('records')  # Last 2 weeks
            
            return data if data else None
            
        except Exception as e:
            print(f"Error loading Bitcoin data: {e}")
            return None
    
    def _load_all_assets_data(self) -> Optional[Dict]:
        """
        Load summary data for all assets in config.
        
        Returns:
            Dictionary containing multi-asset data
        """
        try:
            # Load asset list from config
            with open("data/config.json", 'r') as f:
                config = json.load(f)
            assets = config.get("assets", [])
            
            assets_data = {}
            for asset in assets:
                # Load basic info for each asset
                asset_data = {}
                
                # Recent price data
                price_path = f"data/daily/historical_price_{asset}.csv"
                if os.path.exists(price_path):
                    price_df = pd.read_csv(price_path)
                    asset_data['recent_prices'] = price_df.tail(7).to_dict('records')
                
                # Latest predictions
                predictions_path = f"data/predictions/run_analysis_{asset}.json"
                if os.path.exists(predictions_path):
                    with open(predictions_path, 'r') as f:
                        asset_data['predictions'] = json.load(f)
                
                if asset_data:
                    assets_data[asset] = asset_data
            
            return assets_data if assets_data else None
            
        except Exception as e:
            print(f"Error loading multi-asset data: {e}")
            return None
    
    # ------------------------------------------------------------------ #
    # Prompt Generation Methods
    # ------------------------------------------------------------------ #
    
    def _generate_analyst_opinion(self, data: Dict, model: str) -> str:
        """Generate professional analyst perspective."""
        prompt = self._build_analyst_prompt(data)
        
        # Use custom AI function for market analysis with proper role
        if model == "gpt-4o":
            from src.ai_helper import send_prompt_oai
            return send_prompt_oai(
                prompt=prompt,
                model="gpt-4o",
                max_tokens=4096,
                temperature=0.3,
                role_description="You are a professional cryptocurrency market analyst with expertise in technical analysis, market structure, and digital asset investment strategies."
            )
        elif model == "o3":
            from src.ai_helper import send_prompt_o1
            return send_prompt_o1(
                prompt=prompt,
                model="o3"
            )
        else:
            return send_prompt(prompt, model)
    
    def _generate_advisor_opinion(self, data: Dict, model: str) -> str:
        """Generate actionable advisor perspective."""
        prompt = self._build_advisor_prompt(data)
        return send_prompt(prompt, model)
    
    def _generate_risk_assessment(self, data: Dict, model: str) -> str:
        """Generate risk-focused assessment."""
        prompt = self._build_risk_prompt(data)
        return send_prompt(prompt, model)
    
    def _generate_key_factors(self, data: Dict, model: str) -> str:
        """Generate key market factors analysis."""
        prompt = self._build_factors_prompt(data)
        return send_prompt(prompt, model)
    
    def _generate_market_summary(self, data: Dict, model: str) -> str:
        """Generate overall market summary."""
        prompt = self._build_market_summary_prompt(data)
        return send_prompt(prompt, model)
    
    # ------------------------------------------------------------------ #
    # Prompt Building Methods
    # ------------------------------------------------------------------ #
    
    def _build_analyst_prompt(self, data: Dict) -> str:
        """Build prompt for analyst perspective."""
        formatted_data = self._format_data_for_prompt(data)
        
        return f"""You are a professional cryptocurrency market analyst with 10+ years of experience in digital asset analysis. Your clients include institutional investors, hedge funds, and professional traders who require objective, data-driven market assessments.

**ANALYSIS FRAMEWORK:**
Provide a comprehensive technical analysis of Bitcoin based on the data below. Structure your response as follows:

1. **EXECUTIVE SUMMARY** (2-3 sentences)
   - Current market position and primary trend direction
   - Key risk/reward assessment

2. **TECHNICAL ANALYSIS**
   - Price action and trend analysis (daily/weekly perspective)
   - Key technical indicators interpretation (RSI, MACD, Moving Averages)
   - Support and resistance levels identification
   - Bollinger Bands positioning and volatility analysis

3. **MARKET STRUCTURE ANALYSIS**
   - 8-State model interpretation and current market regime
   - Open Interest and CVD (Cumulative Volume Delta) implications
   - Institutional flow assessment

4. **RISK ASSESSMENT**
   - Market instability metrics and liquidation risk
   - Volatility positioning relative to historical norms
   - Potential catalysts for trend continuation or reversal

5. **PROBABILITY-BASED OUTLOOK**
   - Short-term directional bias with confidence levels
   - Key levels to monitor for trend confirmation/invalidation
   - Scenario analysis (bull/bear/neutral cases)

**ANALYTICAL STANDARDS:**
- Use precise technical terminology
- Quantify observations where possible
- Maintain objectivity and avoid emotional language
- Acknowledge uncertainty and provide balanced perspective
- Focus on actionable insights

**CURRENT MARKET DATA:**

{formatted_data}

**INSTRUCTIONS:**
Analyze the above data systematically and provide your professional assessment. Be specific about price levels, percentages, and timeframes. Your analysis should be suitable for sophisticated institutional clients who understand advanced market concepts."""
    
    def _build_advisor_prompt(self, data: Dict) -> str:
        """Build prompt for advisor perspective."""
        formatted_data = self._format_data_for_prompt(data)
        
        return f"""You are an experienced cryptocurrency investment advisor with a proven track record of helping clients navigate volatile digital asset markets. Your approach combines technical analysis with prudent risk management to protect and grow client portfolios.

**ADVISORY FRAMEWORK:**
Based on the current market data, provide actionable investment guidance structured as follows:

1. **INVESTMENT THESIS** (2-3 sentences)
   - Clear directional bias with reasoning
   - Primary opportunity or risk to monitor

2. **POSITION SIZING & ALLOCATION**
   - Recommended portfolio allocation percentage for Bitcoin
   - Risk-adjusted position sizing based on current volatility
   - Considerations for different risk tolerance levels (conservative/moderate/aggressive)

3. **ENTRY & EXIT STRATEGY**
   - Optimal entry zones with specific price levels
   - Staged entry approach if appropriate
   - Target prices for profit-taking
   - Stop-loss recommendations and risk management

4. **TIME HORIZON GUIDANCE**
   - Short-term trading opportunities (1-7 days)
   - Medium-term investment outlook (1-4 weeks)
   - Long-term positioning considerations

5. **RISK MANAGEMENT**
   - Maximum acceptable drawdown
   - Position monitoring guidelines
   - Market condition changes that would trigger reassessment
   - Diversification recommendations

6. **ACTIONABLE RECOMMENDATIONS**
   - Specific actions to take today
   - Key price levels to watch for decisions
   - Rebalancing triggers and schedules

**ADVISORY PRINCIPLES:**
- Prioritize capital preservation
- Provide clear, specific guidance
- Account for different investor profiles
- Include practical implementation steps
- Address both upside potential and downside protection

**CURRENT MARKET DATA:**

{formatted_data}

**CLIENT CONTEXT:**
Assume your client is an informed investor who understands cryptocurrency markets but values professional guidance for portfolio decisions. They seek clear, actionable advice with specific price levels and percentages rather than general market commentary.

Provide your advisory recommendation with the confidence and specificity expected from a trusted financial advisor."""
    
    def _build_risk_prompt(self, data: Dict) -> str:
        """Build prompt for risk assessment."""
        # TODO: Implement detailed risk prompt construction
        return "Risk assessment prompt placeholder"
    
    def _build_factors_prompt(self, data: Dict) -> str:
        """Build prompt for key factors analysis."""
        # TODO: Implement detailed factors prompt construction
        return "Key factors prompt placeholder"
    
    def _build_market_summary_prompt(self, data: Dict) -> str:
        """Build prompt for market summary."""
        # TODO: Implement detailed market summary prompt construction
        return "Market summary prompt placeholder"
    
    # ------------------------------------------------------------------ #
    # Utility Methods
    # ------------------------------------------------------------------ #
    
    def _format_data_for_prompt(self, data: Dict) -> str:
        """Format loaded data into prompt-friendly text."""
        sections = []
        
        # === CURRENT MARKET POSITION ===
        if 'recent_prices' in data and data['recent_prices']:
            latest_price = data['recent_prices'][-1]
            sections.append(f"**CURRENT PRICE DATA:**")
            try:
                close_price = float(latest_price.get('close', 0))
                sections.append(f"Latest Close: ${close_price:,.2f}")
            except (ValueError, TypeError):
                sections.append(f"Latest Close: {latest_price.get('close', 'N/A')}")
            sections.append(f"Latest Date: {latest_price.get('date', 'N/A')}")
            
            # Price trend over last week
            if len(data['recent_prices']) >= 7:
                try:
                    current_price = float(latest_price['close'])
                    week_ago_price = float(data['recent_prices'][-7]['close'])
                    price_change = ((current_price - week_ago_price) / week_ago_price) * 100
                    sections.append(f"7-Day Change: {price_change:+.2f}%")
                except (ValueError, TypeError, KeyError):
                    sections.append(f"7-Day Change: Unable to calculate")
        
        # === 8-STATE ANALYSIS ===
        if 'eight_state' in data:
            sections.append(f"\n**8-STATE MARKET ANALYSIS:**")
            eight_state = data['eight_state']
            if 'latest_signal' in eight_state:
                signal = eight_state['latest_signal']
                sections.append(f"Current State: {signal.get('state', 'N/A')}")
                sections.append(f"Price State: {signal.get('price_state', 'N/A')}")
                sections.append(f"Open Interest State: {signal.get('oi_state', 'N/A')}")
                sections.append(f"CVD State: {signal.get('cvd_state', 'N/A')}")
        
        # === TECHNICAL INDICATORS ===
        if 'technical' in data and 'latest' in data['technical']:
            tech = data['technical']['latest']
            sections.append(f"\n**TECHNICAL INDICATORS:**")
            
            # RSI
            try:
                rsi = float(tech.get('rsi', 0))
                sections.append(f"RSI: {rsi:.1f}")
            except (ValueError, TypeError):
                sections.append(f"RSI: {tech.get('rsi', 'N/A')}")
            
            # MACD
            try:
                macd = float(tech.get('macd', 0))
                sections.append(f"MACD: {macd:.2f}")
            except (ValueError, TypeError):
                sections.append(f"MACD: {tech.get('macd', 'N/A')}")
            
            # Moving Averages
            try:
                sma50 = float(tech.get('sma_50', 0))
                sections.append(f"SMA 50: ${sma50:,.2f}")
            except (ValueError, TypeError):
                sections.append(f"SMA 50: {tech.get('sma_50', 'N/A')}")
                
            try:
                sma200 = float(tech.get('sma_200', 0))
                sections.append(f"SMA 200: ${sma200:,.2f}")
            except (ValueError, TypeError):
                sections.append(f"SMA 200: {tech.get('sma_200', 'N/A')}")
            
            # Bollinger Bands
            try:
                bb_upper = float(tech.get('bb_upper', 0))
                bb_lower = float(tech.get('bb_lower', 0))
                sections.append(f"Bollinger Bands: ${bb_lower:,.2f} - ${bb_upper:,.2f}")
            except (ValueError, TypeError):
                pass
                
            try:
                bb_percentile = float(tech.get('bb_width_percentile', 0))
                sections.append(f"BB Width Percentile: {bb_percentile:.0f}%")
            except (ValueError, TypeError):
                pass
        
        # === INSTABILITY ANALYSIS ===
        if 'instability' in data and data['instability']:
            sections.append(f"\n**MARKET INSTABILITY:**")
            recent_instability = data['instability'][-5:]  # Last 5 days
            high_instability_days = [day for day in recent_instability if day.get('status') == 'High']
            sections.append(f"High Instability Days (last 5): {len(high_instability_days)}")
            
            latest_instability = data['instability'][-1]
            try:
                liq_value = float(latest_instability.get('liquidation_value', 0))
                sections.append(f"Latest Liquidations: ${liq_value:,.0f}")
            except (ValueError, TypeError):
                sections.append(f"Latest Liquidations: {latest_instability.get('liquidation_value', 'N/A')}")
            sections.append(f"Latest Status: {latest_instability.get('status', 'N/A')}")
        
        # === VOLATILITY ANALYSIS ===
        if 'volatility' in data and data['volatility']:
            sections.append(f"\n**VOLATILITY METRICS:**")
            latest_vol = data['volatility'][-1]
            try:
                vol_value = float(latest_vol.get('volatility', 0))
                sections.append(f"Latest Volatility: {vol_value:.3f}")
            except (ValueError, TypeError):
                sections.append(f"Latest Volatility: {latest_vol.get('volatility', 'N/A')}")
                
            if 'volatility_percentile' in latest_vol:
                try:
                    vol_percentile = float(latest_vol['volatility_percentile'])
                    sections.append(f"Volatility Percentile: {vol_percentile:.1f}%")
                except (ValueError, TypeError):
                    sections.append(f"Volatility Percentile: {latest_vol['volatility_percentile']}")
        
        # === PREDICTIONS ===
        if 'predictions' in data:
            pred = data['predictions']
            sections.append(f"\n**PREDICTIVE ANALYSIS:**")
            
            if 'short_term' in pred:
                st = pred['short_term']
                sections.append(f"Short-term Streak: {st.get('current_streak_length', 'N/A')} days {st.get('current_direction', 'N/A')}")
                sections.append(f"Continuation Probability: {st.get('continuation_probability', 0):.1%}")
                sections.append(f"Expected Return: {st.get('expected_return', 0):.3%}")
            
            if 'all_time' in pred:
                at = pred['all_time']
                sections.append(f"All-time Analysis: {at.get('continuation_probability', 0):.1%} continuation probability")
        
        return "\n".join(sections)
    
    def save_analysis_to_file(self, analysis: Dict, filename: str = None) -> str:
        """
        Save AI analysis to file.
        
        Args:
            analysis: Analysis dictionary to save
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/analysis/ai_analysis_bitcoin_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return filename


# ------------------------------------------------------------------ #
# Convenience Functions
# ------------------------------------------------------------------ #

def generate_daily_bitcoin_analysis(model: str = "o3") -> Dict[str, str]:
    """
    Convenience function to generate daily Bitcoin analysis.
    
    Args:
        model: AI model to use
        
    Returns:
        Analysis dictionary
    """
    reporter = AIMarketReporter(default_model=model)
    return reporter.generate_bitcoin_analysis(timeframe="daily")


def generate_weekly_bitcoin_analysis(model: str = "o3") -> Dict[str, str]:
    """
    Convenience function to generate weekly Bitcoin analysis.
    
    Args:
        model: AI model to use
        
    Returns:
        Analysis dictionary
    """
    reporter = AIMarketReporter(default_model=model)
    return reporter.generate_bitcoin_analysis(timeframe="weekly")


def generate_ai_bitcoin_analysis(model: str = "o3") -> Dict[str, str]:
    """
    Generate complete AI-powered Bitcoin analysis with both analyst and advisor perspectives.
    
    Args:
        model: AI model to use (default: o3)
        
    Returns:
        Dictionary with analyst and advisor analysis
    """
    reporter = AIMarketReporter(default_model=model)
    data = reporter._load_bitcoin_data()
    
    if not data:
        return {"error": "Failed to load Bitcoin data"}
    
    result = {}
    
    try:
        # Generate analyst perspective
        analyst_text = reporter._generate_analyst_opinion(data, model)
        result['analyst'] = {
            'success': True,
            'analysis': analyst_text
        }
        
        # Generate advisor perspective  
        if model == "gpt-4o":
            from src.ai_helper import send_prompt_oai
            prompt = reporter._build_advisor_prompt(data)
            advisor_text = send_prompt_oai(
                prompt=prompt,
                model="gpt-4o",
                max_tokens=4096,
                temperature=0.3,
                role_description="You are an experienced cryptocurrency investment advisor specializing in risk management and portfolio optimization for digital assets."
            )
            result['advisor'] = {
                'success': True,
                'analysis': advisor_text
            }
        elif model == "o3":
            from src.ai_helper import send_prompt_o1
            prompt = reporter._build_advisor_prompt(data)
            advisor_text = send_prompt_o1(
                prompt=prompt,
                model="o3"
            )
            result['advisor'] = {
                'success': True,
                'analysis': advisor_text
            }
        else:
            advisor_text = reporter._generate_advisor_opinion(data, model)
            result['advisor'] = {
                'success': True,
                'analysis': advisor_text
            }
            
        result['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result['model_used'] = model
        
    except Exception as e:
        result['error'] = f"Analysis generation failed: {e}"
        result['analyst'] = {'success': False, 'analysis': 'Analyst analysis failed'}
        result['advisor'] = {'success': False, 'analysis': 'Advisor analysis failed'}
    
    return result


if __name__ == "__main__":
    # Test the AI reporter
    reporter = AIMarketReporter()
    
    print("Generating Bitcoin analysis...")
    analysis = reporter.generate_bitcoin_analysis()
    
    print("\nAnalysis generated:")
    for key, value in analysis.items():
        print(f"{key}: {value[:100]}..." if len(str(value)) > 100 else f"{key}: {value}") 
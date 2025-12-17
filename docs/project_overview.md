# CryptoAlertBot - Project Overview

## Table of Contents
- [Introduction](#introduction)
- [Architecture](#architecture)
- [Core Features](#core-features)
- [Data Sources](#data-sources)
- [Analysis Modules](#analysis-modules)
- [Visualization & Plotting](#visualization--plotting)
- [AI Integration](#ai-integration)
- [GUI Interface](#gui-interface)
- [Data Management](#data-management)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Output Files](#output-files)
- [Development](#development)

## Introduction

CryptoAlertBot is a comprehensive cryptocurrency analysis platform that combines traditional technical analysis with modern AI-powered insights. The application provides institutional-grade market analysis, signal generation, and automated reporting for multiple cryptocurrency assets.

### Key Capabilities
- **Multi-Asset Analysis**: Supports 7 major cryptocurrencies (BTC, ETH, SOL, BNB, XRP, ADA, TRX)
- **Advanced Technical Analysis**: Traditional indicators plus specialized tools like UT Bot alerts
- **AI-Powered Insights**: GPT-4o integration for professional market analysis
- **Comprehensive Visualization**: Multiple chart types and specialized plotting functions
- **Automated Reporting**: Markdown reports with embedded analysis and charts
- **Real-time Data Collection**: API integration for live market data

## Architecture

```
CryptoAlertBot/
├── main.py                 # Main GUI application
├── src/                    # Core modules
│   ├── analyzers/          # Analysis engines
│   ├── collectors/         # Data collection modules
│   ├── plotters/           # Visualization modules
│   ├── reporters/          # Report generation
│   ├── archivers/          # Data archival system
│   ├── backtesters/        # Strategy backtesting
│   └── ai_helper.py        # AI integration utilities
├── data/                   # Data storage
│   ├── daily/              # Daily market data
│   ├── weekly/             # Weekly aggregated data
│   ├── analysis/           # Analysis results
│   └── predictions/        # Predictive analysis
├── plots/                  # Generated charts
├── reports/                # Generated reports
└── docs/                   # Documentation
```

### Design Principles
- **Modular Architecture**: Each component is self-contained and reusable
- **Data-Driven**: All analysis based on quantitative market data
- **Extensible**: Easy to add new assets, indicators, or analysis methods
- **Professional Grade**: Institutional-quality analysis and reporting

## Core Features

### 1. Market Regime Analysis
- **8-State Market Analysis**: Comprehensive market state classification
- **Price State Detection**: UP/DOWN/NEUTRAL trend identification
- **Open Interest Analysis**: Derivatives market sentiment
- **CVD Analysis**: Cumulative Volume Delta for institutional flow

### 2. Technical Analysis Suite
- **Traditional Indicators**: RSI, MACD, Moving Averages, Bollinger Bands
- **Advanced Tools**: UT Bot alerts with Heikin-Ashi variants
- **Custom Indicators**: BB on MACD for specialized analysis
- **Multi-Timeframe**: Daily and weekly analysis capabilities

### 3. Risk Assessment
- **Volatility Analysis**: Historical and implied volatility metrics
- **Instability Detection**: Liquidation-based market stress indicators
- **Predictive Modeling**: Statistical analysis for trend continuation

### 4. AI-Powered Analysis
- **Dual Persona System**: Technical Analyst and Investment Advisor perspectives
- **Contextual Analysis**: Integration of multiple data sources for comprehensive insights
- **Professional Reporting**: Institutional-grade analysis format

## Data Sources

### Primary Data Feeds
- **Price Data**: OHLCV data from cryptocurrency exchanges
- **Open Interest**: Derivatives market data
- **CVD (Cumulative Volume Delta)**: Institutional flow indicators
- **Liquidations**: Forced position closures data
- **Volume Profiles**: Intraday trading activity

### Data Collection Modules
- `cvd_collector.py`: Cumulative Volume Delta data
- `oi_collector.py`: Open Interest from exchanges
- `price_collector.py`: Real-time price feeds
- `liquidation_collector.py`: Liquidation events
- `historical_price_collector.py`: Historical OHLCV data
- `intraday_price_collector.py`: High-frequency price data

### Supported Assets
- BTCUSDT (Bitcoin)
- ETHUSDT (Ethereum)
- SOLUSDT (Solana)
- BNBUSDT (Binance Coin)
- XRPUSDT (Ripple)
- ADAUSDT (Cardano)
- TRXUSDT (Tron)

## Analysis Modules

### Technical Analysis (`technical_analyzer.py`)
- **Indicators**: RSI, MACD, SMAs (50, 200), Bollinger Bands
- **UT Bot Integration**: Advanced trend-following signals
- **Heikin-Ashi Analysis**: Smoothed price action analysis
- **Multi-timeframe**: Daily and weekly calculations

### Market State Analysis (`eight_state_analyzer.py`)
- **State Classification**: 8 distinct market regimes
- **Component Analysis**: Price, OI, and CVD state detection
- **Signal Generation**: Entry/exit signals based on state transitions

### Risk Analysis
- **Volatility Analysis** (`price_volatility_analyzer.py`): Historical volatility metrics
- **Instability Analysis** (`instability_analyzer.py`): Liquidation-based risk assessment
- **Predictive Analysis** (`run_predictor.py`): Statistical trend analysis

### Advanced Analytics
- **Run Analysis** (`run_analyzer.py`): Streak and momentum analysis
- **Pattern Recognition**: Technical pattern identification
- **Statistical Modeling**: Probability-based forecasting

## Visualization & Plotting

### Chart Types
- **Technical Charts**: Price with indicators overlay
- **Heikin-Ashi Charts**: Smoothed candlestick visualization
- **UT Bot Charts**: Specialized trend-following plots
- **BB on MACD**: Bollinger Bands applied to MACD indicator
- **Combined Charts**: Multi-panel technical analysis

### Plotting Modules
- `technical_plotter.py`: Main technical analysis charts
- `heikin_ashi_plotter.py`: Heikin-Ashi visualization
- `cvd_plotter.py`: CVD flow analysis charts
- `oi_plotter.py`: Open Interest visualization
- `liquidation_plotter.py`: Liquidation heatmaps
- `combined_plotter.py`: Multi-asset comparison charts

### Chart Features
- **Multi-Panel Layout**: Price, indicators, and volume in separate panels
- **Signal Highlighting**: Entry/exit points clearly marked
- **Customizable Timeframes**: Daily and weekly views
- **Professional Styling**: Clean, institutional-grade appearance

## AI Integration

### AI Market Reporter (`ai_market_reporter.py`)
- **Dual Persona Analysis**: Technical Analyst and Investment Advisor perspectives
- **Data Integration**: Combines all analysis modules for comprehensive insights
- **Professional Format**: Institutional-grade report structure
- **Model Support**: GPT-4o integration with fallback options

### Analysis Components
- **Executive Summary**: High-level market assessment
- **Technical Analysis**: Detailed indicator interpretation
- **Market Structure**: Regime and flow analysis
- **Risk Assessment**: Volatility and instability evaluation
- **Probability Outlook**: Statistical forecasting

### AI Helper (`ai_helper.py`)
- **Model Management**: Support for multiple AI models
- **Prompt Engineering**: Optimized prompts for financial analysis
- **Error Handling**: Robust API interaction management
- **Token Optimization**: Efficient prompt structure

## GUI Interface

### Main Application (`main.py`)
The GUI provides intuitive access to all platform features through a tabbed interface:

### Core Functions
- **Data Collection**: Update all data sources with single click
- **Analysis Generation**: Run comprehensive analysis suite
- **Plot Generation**: Create all chart types
- **Report Generation**: Generate markdown reports with AI analysis
- **Archive Management**: Historical data preservation

### Interface Components
- **Asset Tabs**: Individual tabs for each tracked cryptocurrency
- **Data Source Tables**: Real-time status of data feeds
- **Control Buttons**: Easy access to all major functions
- **Status Indicators**: Visual feedback on operation status

### User Experience
- **One-Click Operations**: Complex analysis with simple interface
- **Real-time Feedback**: Console output for operation status
- **File Management**: Automatic organization of outputs
- **Error Handling**: Graceful handling of missing data or API issues

## Data Management

### Storage Structure
```
data/
├── daily/              # Daily market data files
├── weekly/             # Weekly aggregated data
├── analysis/           # Analysis results (CSV/JSON)
├── predictions/        # Predictive analysis outputs
├── intraday/          # High-frequency data
└── config.json        # Asset configuration
```

### File Formats
- **CSV**: Structured data for analysis (prices, indicators, signals)
- **JSON**: Configuration and complex analysis results
- **PNG**: Generated charts and visualizations
- **MD**: Markdown reports with embedded analysis

### Archive System
- **Automated Archival**: Historical data preservation
- **Date-based Organization**: Chronological data management
- **Compression**: Efficient storage of historical data
- **Metadata Tracking**: Data source and update timestamps

## Getting Started

### Prerequisites
```bash
# Python 3.8+
pip install -r requirements.txt
```

### Dependencies
- `pandas`: Data manipulation and analysis
- `matplotlib/mplfinance`: Chart generation
- `requests`: API data collection
- `openai`: AI analysis integration
- `tkinter`: GUI framework (built-in)

### Environment Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure API keys in `.env` file
4. Run the application: `python main.py`

### Initial Configuration
- Set up API keys for data sources
- Configure asset list in `data/config.json`
- Verify data collection permissions
- Test AI integration

## Configuration

### Asset Configuration (`data/config.json`)
```json
{
    "assets": [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "TRXUSDT"
    ]
}
```

### Environment Variables (`.env`)
```
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
# Additional API keys as needed
```

### Analysis Parameters
- **UT Bot**: Key Value (1.0), ATR Period (10)
- **Technical Indicators**: Standard periods (14, 50, 200)
- **Bollinger Bands**: 2 standard deviations
- **Analysis Timeframes**: Daily and Weekly

## Output Files

### Generated Reports
- **Location**: `reports/`
- **Format**: Markdown with embedded charts
- **Content**: Comprehensive market analysis with AI insights
- **Frequency**: On-demand generation

### Analysis Data
- **Location**: `data/analysis/`
- **Files**: `technical_analysis_{symbol}.csv`, `signals_{symbol}.csv`
- **Content**: Calculated indicators and signals
- **Update**: Real-time with data collection

### Visualizations
- **Location**: `plots/`
- **Types**: Technical charts, Heikin-Ashi, UT Bot, BB on MACD
- **Format**: PNG images
- **Resolution**: High-quality for professional use

### AI Analysis
- **Location**: `data/analysis/`
- **Files**: `ai_analysis_bitcoin_YYYYMMDD_HHMMSS.json`
- **Content**: Structured AI analysis with metadata
- **Perspectives**: Technical Analyst and Investment Advisor

## Development

### Adding New Assets
1. Update `data/config.json` with new symbol
2. Ensure data collection APIs support the asset
3. Test data collection and analysis pipeline
4. Verify chart generation and reporting

### Extending Analysis
1. Create new analyzer module in `src/analyzers/`
2. Implement analysis logic with CSV output
3. Add plotting support in `src/plotters/`
4. Integrate with main application workflow

### Custom Indicators
1. Add calculation logic to `technical_analyzer.py`
2. Update plotting functions for visualization
3. Include in AI analysis data formatting
4. Test across all supported assets

### Contributing
- Follow modular architecture patterns
- Maintain CSV output format consistency
- Include comprehensive error handling
- Document new features and parameters

---

*Last Updated: July 2025*
*Version: 2.0*

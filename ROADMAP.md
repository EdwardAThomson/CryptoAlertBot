# Roadmap — CryptoAlertBot

_Status: active · updated 2026-05-30_

A Python crypto market-research platform — ingests multi-asset futures data,
runs quantitative + technical analysis, generates charts, and produces
markdown/PDF reports with optional AI commentary. See `docs/project_overview.md`.

## Shipped

- [x] Multi-asset data collection (7 futures pairs: price, CVD, open interest, liquidations, intraday)
- [x] Market regime analysis (8-state price/OI/CVD model)
- [x] Technical analysis (RSI, MACD, SMAs, Bollinger Bands, UT Bot, BB-on-MACD, daily/weekly)
- [x] Risk metrics (Sharpe, Sortino, Omega, CVaR, drawdowns, instability index, run-length)
- [x] Plotting (price / CVD / OI / liquidations / combined / technical / Heikin-Ashi → PNG/SVG)
- [x] Report generation (multi-asset + Bitcoin-only, markdown + PDF)
- [x] AI commentary (dual-persona Technical Analyst + Investment Advisor via GPT-4o)
- [x] Tkinter GUI (tabbed, per-asset coverage tables, action buttons)
- [x] Archiving (timestamped data snapshots)
- [x] Configuration via `data/config.json` + `.env`

## Next

- [ ] Google Trends integration (data collection + metadata UI)
- [ ] Plotter asset-aware refactor (CVD/OI/combined currently hardcoded)
- [ ] Signal generation (`update_signals()` stub)
- [ ] Expand detailed AI analysis beyond Bitcoin to all tracked assets
- [ ] Upgrade to the latest AI models

## Backlog

- [ ] Strategy backtesting GUI integration (`src/backtesters/` exists, not wired up)
- [ ] Custom-indicator extensibility
- [ ] Real-time data enhancements
- [ ] Historical AI-analysis performance tracking
- [ ] Multi-model consensus analysis

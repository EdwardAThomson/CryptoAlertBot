import tkinter as tk
from tkinter import ttk
from datetime import date
import json
import src.collectors.cvd_collector as cvd_collector
import src.collectors.oi_collector as oi_collector
import src.collectors.price_collector as price_collector
import src.collectors.liquidation_collector as liquidation_collector
import src.collectors.historical_price_collector as historical_price_collector
import src.collectors.intraday_price_collector as intraday_price_collector
from src.plotters import cvd_plotter
from src.plotters import price_plotter
from src.plotters import oi_plotter
from src.plotters import combined_plotter
from src.plotters import liquidation_plotter
from src.plotters import technical_plotter
from src.plotters import heikin_ashi_plotter
from src.analyzers import eight_state_analyzer
from src.analyzers import instability_analyzer
from src.analyzers import price_volatility_analyzer
from src.analyzers import technical_analyzer
from src.archivers import archiver
from src.reporters import markdown_reporter
import os
from src.analyzers import run_predictor
from src.analyzers import run_analyzer
from datetime import datetime

# CryptoAlertBot
# Main application
# This file handles the GUI and calls to data collectors and plotters


class DataSourceTable(ttk.Frame):
    """Reusable table widget for grouping data sources by timeframe."""

    COLUMNS = ("Label", "Start Date", "End Date", "Filename")

    def __init__(self, master: tk.Widget, title: str, sources: list[str], **kwargs):
        super().__init__(master, **kwargs)

        # Section title
        ttk.Label(self, text=title, font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 2))

        # Treeview acts like a simple table
        self.tree = ttk.Treeview(self, columns=self.COLUMNS, show="headings", height=max(len(sources), 1))
        self._configure_columns()
        self._populate_rows(sources)
        self.tree.pack(fill="x", expand=True)

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #
    def set_dates(self, label: str, start: date | str, end: date | str):
        """Update the start/end date cells for a given data source label."""
        item_id = self._find_item_by_label(label)
        if not item_id:
            return  # label not present – could raise or log instead.
        filename = self.tree.set(item_id, "Filename")
        self.tree.item(item_id, values=(label, start, end, filename))

    def set_filename(self, label: str, filename: str):
        item_id = self._find_item_by_label(label)
        if not item_id:
            return
        start = self.tree.set(item_id, "Start Date")
        end = self.tree.set(item_id, "End Date")
        self.tree.item(item_id, values=(label, start, end, filename))

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _configure_columns(self):
        for col in self.COLUMNS:
            self.tree.heading(col, text=col)
            # Widths are placeholders – adjust or make dynamic later
            width = 140 if col == "Label" else 110
            self.tree.column(col, width=width, anchor="center")

    def _populate_rows(self, sources: list[str]):
        """Insert initial blank rows for each data source."""
        for label in sources:
            self.tree.insert("", "end", values=(label, "--", "--", "--"))

    def _find_item_by_label(self, label: str):
        for iid in self.tree.get_children():
            if self.tree.set(iid, "Label") == label:
                return iid
        return None


class App(tk.Tk):
    """Main application window."""

    DAILY_SOURCES = [
        "Price",
        "CVD",
        "Open Interest",
        "Liquidations",
        "Historical Price",
    ]

    MONTHLY_SOURCES = [
        "Google Trends (Bitcoin)",
        # "Price (Yahoo Finance)",
    ]

    def __init__(self):
        super().__init__()
        self.title("Data Source Dashboard")
        self.geometry("1000x800")
        self.configure(padx=10, pady=10)

        # --- Tabbed Interface ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # --- Create a tab for each asset in config.json ---
        self.asset_tabs = {}
        assets = self._load_assets()
        for asset in assets:
            self._create_asset_tab(asset)

        # ------------------------------------------------------------------ #
        # Action Buttons
        # ------------------------------------------------------------------ #
        # Main container frame for all button sections
        action_frame = ttk.Frame(self)
        action_frame.pack(pady=(10, 0), fill="x", expand=False)

        # --- Data Collection Frame ---
        data_frame = ttk.Labelframe(action_frame, text="Data Collection", padding=5)
        data_frame.grid(row=0, column=0, padx=5, sticky="ns")
        ttk.Button(data_frame, text="Update All Market Data", command=self.update_data).pack(fill="x", pady=2)
        ttk.Button(data_frame, text="Update Historical Prices", command=self.update_historical_prices).pack(fill="x", pady=2)
        
        # --- Analysis Frame ---
        analysis_frame = ttk.Labelframe(action_frame, text="Run Analyses", padding=5)
        analysis_frame.grid(row=0, column=1, padx=5, sticky="ns")
        ttk.Button(analysis_frame, text="Run 8-State Analysis", command=self.run_eight_state_analysis).pack(fill="x", pady=2)
        ttk.Button(analysis_frame, text="Run Instability Analysis", command=self.run_instability_analysis).pack(fill="x", pady=2)
        ttk.Button(analysis_frame, text="Run Volatility Analysis", command=self.run_volatility_analysis).pack(fill="x", pady=2)
        ttk.Button(analysis_frame, text="Run Daily Technical Analysis", command=self.run_technical_analysis).pack(fill="x", pady=2)
        ttk.Button(analysis_frame, text="Run Weekly Technical Analysis", command=self.run_weekly_technical_analysis).pack(fill="x", pady=2)

        # --- Master Actions / Outputs Frame ---
        output_frame = ttk.Labelframe(action_frame, text="Generate Outputs & Master Controls", padding=5)
        output_frame.grid(row=0, column=2, padx=5, sticky="ns")
        ttk.Button(output_frame, text="Update All Analyses", command=self.update_analysis).pack(fill="x", pady=2)
        ttk.Button(output_frame, text="Update All Plots", command=self.update_plots).pack(fill="x", pady=2)
        ttk.Button(output_frame, text="Plot Weekly Technicals", command=self.plot_weekly_technicals).pack(fill="x", pady=2)
        ttk.Button(output_frame, text="Plot Heikin Ashi", command=self.plot_heikin_ashi).pack(fill="x", pady=2)
        ttk.Button(output_frame, text="Generate AI Analysis", command=self.generate_ai_analysis).pack(fill="x", pady=2)
        ttk.Button(output_frame, text="Update Everything & Archive", command=self.update_all).pack(fill="x", pady=2)
        
        # --- Report Generation Frame ---
        report_frame = ttk.Labelframe(action_frame, text="Generate Reports", padding=5)
        report_frame.grid(row=0, column=3, padx=5, sticky="ns")
        ttk.Button(report_frame, text="Full Market Report (with AI)", command=self.generate_full_report_with_ai).pack(fill="x", pady=2)
        ttk.Button(report_frame, text="Full Market Report (no AI)", command=self.generate_full_report_no_ai).pack(fill="x", pady=2)
        ttk.Button(report_frame, text="Bitcoin Only (with AI)", command=self.generate_bitcoin_report_with_ai).pack(fill="x", pady=2)
        ttk.Button(report_frame, text="Bitcoin Only (no AI)", command=self.generate_bitcoin_report_no_ai).pack(fill="x", pady=2)
        ttk.Button(report_frame, text="Brief AI Report", command=self.generate_report_alt).pack(fill="x", pady=2)
        
        # Configure the grid columns to have equal weight
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)
        action_frame.grid_columnconfigure(2, weight=1)
        action_frame.grid_columnconfigure(3, weight=1)

        # --- Status Display ---
        status_frame = ttk.Frame(self)
        status_frame.pack(pady=(10, 0), fill="x")
        self.archive_status_label = ttk.Label(status_frame, text="Last Archive: --", font=("Helvetica", 10, "italic"))
        self.archive_status_label.pack()

        # Load initial metadata on startup
        self.update_metadata()
        self.update_archive_display()

    # ------------------------------------------------------------------ #
    # UI Setup Helpers
    # ------------------------------------------------------------------ #
    def _load_assets(self):
        """Loads the list of assets from the config file."""
        try:
            with open("data/config.json", 'r') as f:
                config = json.load(f)
            return config.get("assets", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing config file: {e}")
            return []

    def _create_asset_tab(self, asset_symbol: str):
        """Creates a new tab for a given asset symbol."""
        tab_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_frame, text=asset_symbol)

        daily_table = DataSourceTable(tab_frame, "Daily Data", self.DAILY_SOURCES)
        daily_table.pack(fill="x", expand=True, pady=4)

        monthly_table = DataSourceTable(tab_frame, "Monthly Data", self.MONTHLY_SOURCES)
        monthly_table.pack(fill="x", expand=True, pady=4)

        # Frame for asset-specific buttons
        asset_button_frame = ttk.Frame(tab_frame)
        asset_button_frame.pack(pady=(10, 0), fill="x")

        ttk.Button(
            asset_button_frame,
            text=f"Update Analysis for {asset_symbol}",
            command=lambda: self.update_analysis(symbol=asset_symbol)
        ).pack()

        self.asset_tabs[asset_symbol] = {
            "daily": daily_table,
            "monthly": monthly_table,
        }

    # ------------------------------------------------------------------ #
    # Individual Analysis Runners
    # ------------------------------------------------------------------ #
    def run_eight_state_analysis(self):
        """Runs only the 8-state analysis for all assets."""
        print("\n--- Running 8-State Analysis for all assets ---")
        assets_to_run = self._load_assets()
        column_map = {"price": "close", "oi": "sumOpenInterestValue", "cvd": "CVD"}
        for asset_symbol in assets_to_run:
            print(f"  - Generating 8-state signals for {asset_symbol}...")
            price_data_path = historical_price_collector.get_historical_price_data_filepath(asset_symbol)
            oi_data_path = oi_collector.get_oi_data_filepath(asset_symbol)
            cvd_data_path = cvd_collector.get_cvd_data_filepath(asset_symbol)
            if all(os.path.exists(p) for p in [price_data_path, oi_data_path, cvd_data_path]):
                eight_state_analyzer.generate_signals(
                    price_path=price_data_path,
                    oi_path=oi_data_path,
                    cvd_path=cvd_data_path,
                    symbol=asset_symbol,
                    column_map=column_map
                )
            else:
                print(f"    - Signal generation for {asset_symbol} failed: One or more required data files are missing.")
        print("--- 8-State Analysis complete ---\n")

    def run_instability_analysis(self):
        """Runs only the instability analysis for all assets."""
        print("\n--- Running Instability Analysis for all assets ---")
        assets_to_run = self._load_assets()
        for asset_symbol in assets_to_run:
            print(f"  - Generating instability analysis for {asset_symbol}...")
            liquidation_path = liquidation_collector.get_liquidation_data_filepath(asset_symbol)
            if os.path.exists(liquidation_path):
                instability_analyzer.generate_instability_analysis(
                    liquidation_path=liquidation_path, symbol=asset_symbol
                )
            else:
                print(f"    - Instability analysis for {asset_symbol} failed: Liquidation data file not found.")
        print("--- Instability Analysis complete ---\n")

    def run_volatility_analysis(self):
        """Runs only the volatility analysis for all assets."""
        print("\n--- Running Volatility Analysis for all assets ---")
        assets_to_run = self._load_assets()
        for asset_symbol in assets_to_run:
            print(f"  - Generating volatility analysis for {asset_symbol}...")
            historical_price_path = historical_price_collector.get_historical_price_data_filepath(asset_symbol)
            if os.path.exists(historical_price_path):
                price_volatility_analyzer.generate_volatility_analysis(
                    price_path=historical_price_path, symbol=asset_symbol
                )
            else:
                print(f"    - Volatility analysis for {asset_symbol} failed: Historical price data file not found.")
        print("--- Volatility Analysis complete ---\n")

    def run_technical_analysis(self):
        """Runs only the technical analysis for all assets."""
        print("\n--- Running Technical Analysis for all assets ---")
        assets_to_run = self._load_assets()
        for asset_symbol in assets_to_run:
            print(f"  - Generating technical analysis for {asset_symbol}...")
            technical_analyzer.generate_technical_analysis(asset_symbol)
        print("--- Technical Analysis complete ---\n")

    def run_weekly_technical_analysis(self):
        """Runs only the technical analysis on weekly data for all assets."""
        print("\n--- Running Weekly Technical Analysis for all assets ---")
        assets_to_run = self._load_assets()
        for asset_symbol in assets_to_run:
            print(f"  - Generating weekly technical analysis for {asset_symbol}...")
            technical_analyzer.generate_technical_analysis(asset_symbol, timeframe='weekly')
        print("--- Weekly Technical Analysis complete ---\n")

    def plot_weekly_technicals(self):
        """Generates only the weekly technical plots for all assets."""
        print("\n--- Plotting Weekly Technicals for all assets ---")
        assets = self._load_assets()
        for symbol in assets:
            technical_plotter.generate_technical_plot(symbol=symbol, timeframe='weekly', last_n_periods=104) # 2 years of weekly data
            technical_plotter.generate_ut_bot_plot(symbol=symbol, timeframe='weekly', last_n_periods=104) # UT Bot weekly plots
            technical_plotter.generate_bb_macd_plot(symbol=symbol, timeframe='weekly', last_n_periods=104) # BB on MACD weekly plots
        print("--- Weekly plotting complete ---\n")

    def plot_heikin_ashi(self):
        """Generates Heikin Ashi plots for all assets, daily and weekly."""
        print("\n--- Plotting Heikin Ashi candles for all assets ---")
        assets = self._load_assets()
        for symbol in assets:
            heikin_ashi_plotter.generate_heikin_ashi_plot(symbol=symbol, timeframe='daily')
            heikin_ashi_plotter.generate_heikin_ashi_plot(symbol=symbol, timeframe='weekly', last_n_periods=104)
        print("--- Heikin Ashi plotting complete ---\n")

    def generate_ai_analysis(self):
        """Generates AI analysis for Bitcoin and saves it to file."""
        print("\n--- Generating AI Analysis ---")
        try:
            from src.reporters.ai_market_reporter import generate_ai_bitcoin_analysis, AIMarketReporter
            analysis = generate_ai_bitcoin_analysis()
            
            if analysis['analyst']['success'] and analysis['advisor']['success']:
                print("AI analysis generated successfully!")
                print(f"Analyst analysis: {len(analysis['analyst']['analysis'])} characters")
                print(f"Advisor analysis: {len(analysis['advisor']['analysis'])} characters")
                
                # Save analysis to file
                reporter = AIMarketReporter()
                saved_path = reporter.save_analysis_to_file(analysis)
                print(f"Analysis saved to: {saved_path}")
                
            else:
                print("AI analysis completed with some errors - check logs")
                
        except Exception as e:
            print(f"AI analysis failed: {e}")
        print("--- AI Analysis complete ---\n")

    def generate_report_alt(self):
        """Generates market report using the alternative brief AI approach."""
        print("\n--- Generating Market Report (Brief AI) ---")
        try:
            from src.reporters.markdown_reporter_alt import generate_report_alt
            generate_report_alt()
            print("Alternative report generated successfully!")
        except Exception as e:
            print(f"Alternative report generation failed: {e}")
        print("--- Alternative Report complete ---\n")

    def generate_full_report_with_ai(self):
        """Generates full market report with AI analysis included."""
        print("\n--- Generating Full Market Report (with AI) ---")
        try:
            # Set environment to enable AI
            os.environ['DISABLE_AI_REPORTING'] = 'false'
            markdown_reporter.generate_report()
            print("Full market report with AI generated successfully!")
        except Exception as e:
            print(f"Full market report generation failed: {e}")
        print("--- Full Market Report (with AI) complete ---\n")

    def generate_full_report_no_ai(self):
        """Generates full market report without AI analysis."""
        print("\n--- Generating Full Market Report (no AI) ---")
        try:
            # Set environment to disable AI
            os.environ['DISABLE_AI_REPORTING'] = 'true'
            markdown_reporter.generate_report()
            print("Full market report without AI generated successfully!")
        except Exception as e:
            print(f"Full market report generation failed: {e}")
        finally:
            # Reset environment
            os.environ['DISABLE_AI_REPORTING'] = 'false'
        print("--- Full Market Report (no AI) complete ---\n")

    def generate_bitcoin_report_with_ai(self):
        """Generates Bitcoin-only report with AI analysis."""
        print("\n--- Generating Bitcoin Report (with AI) ---")
        try:
            # Set environment to enable AI
            os.environ['DISABLE_AI_REPORTING'] = 'false'
            self._generate_bitcoin_only_report()
            print("Bitcoin report with AI generated successfully!")
        except Exception as e:
            print(f"Bitcoin report generation failed: {e}")
        print("--- Bitcoin Report (with AI) complete ---\n")

    def generate_bitcoin_report_no_ai(self):
        """Generates Bitcoin-only report without AI analysis."""
        print("\n--- Generating Bitcoin Report (no AI) ---")
        try:
            # Set environment to disable AI
            os.environ['DISABLE_AI_REPORTING'] = 'true'
            self._generate_bitcoin_only_report()
            print("Bitcoin report without AI generated successfully!")
        except Exception as e:
            print(f"Bitcoin report generation failed: {e}")
        finally:
            # Reset environment
            os.environ['DISABLE_AI_REPORTING'] = 'false'
        print("--- Bitcoin Report (no AI) complete ---\n")

    def _generate_bitcoin_only_report(self):
        """Helper method to generate Bitcoin-only report."""
        from src.reporters.markdown_reporter import generate_bitcoin_only_report
        generate_bitcoin_only_report()

    # ------------------------------------------------------------------ #
    # Data Update Callbacks
    # ------------------------------------------------------------------ #
    def _should_update_run_distributions(self) -> bool:
        """Checks if the run distributions have been updated in the last 7 days."""
        last_updated_file = "data/analysis/run_distributions_last_updated.json"
        if not os.path.exists(last_updated_file):
            return True  # File doesn't exist, so we should update

        try:
            with open(last_updated_file, 'r') as f:
                data = json.load(f)
            last_updated_str = data.get("last_updated")
            if not last_updated_str:
                return True # Key missing
            
            last_updated_date = datetime.strptime(last_updated_str, "%Y-%m-%d").date()
            
            # Check if it's been 7 or more days
            if (date.today() - last_updated_date).days >= 7:
                return True

        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            print(f"Could not read or parse last updated timestamp for run distributions: {e}")
            return True # Error reading, so update just in case
            
        return False

    def _update_run_distributions_timestamp(self):
        """Updates the timestamp file after a successful distributions update."""
        last_updated_file = "data/analysis/run_distributions_last_updated.json"
        try:
            os.makedirs("data/analysis", exist_ok=True)
            with open(last_updated_file, 'w') as f:
                json.dump({"last_updated": date.today().strftime("%Y-%m-%d")}, f)
        except IOError as e:
            print(f"Error updating run distributions timestamp: {e}")

    def update_metadata(self):
        """Fetch latest metadata for all sources from metadata.csv and refresh tables."""
        print("Updating metadata display from metadata.csv...")
        
        assets = self._load_assets()
        for asset in assets:
            print(f"  - Updating metadata for {asset}")
            
            # Get the correct table from the corresponding tab
            try:
                daily_table = self.asset_tabs[asset]["daily"]
                monthly_table = self.asset_tabs[asset]["monthly"]
            except KeyError:
                print(f"Warning: Could not find UI tables for asset '{asset}'. Skipping.")
                continue

            # --- Update Daily metadata ---
            # CVD
            cvd_start, cvd_end, cvd_filename = cvd_collector.get_source_metadata_from_csv(f"CVD_{asset}")
            daily_table.set_dates("CVD", cvd_start, cvd_end)
            daily_table.set_filename("CVD", cvd_filename)

            # Open Interest
            oi_start, oi_end, oi_filename = oi_collector.get_source_metadata_from_csv(f"Open Interest_{asset}")
            daily_table.set_dates("Open Interest", oi_start, oi_end)
            daily_table.set_filename("Open Interest", oi_filename)

            # Price
            price_start, price_end, price_filename = price_collector.get_source_metadata_from_csv(f"Price_{asset}")
            daily_table.set_dates("Price", price_start, price_end)
            daily_table.set_filename("Price", price_filename)

            # Liquidations
            liq_start, liq_end, liq_filename = liquidation_collector.get_source_metadata_from_csv(f"Liquidations_{asset}")
            daily_table.set_dates("Liquidations", liq_start, liq_end)
            daily_table.set_filename("Liquidations", liq_filename)
            
            # Historical Price
            hp_start, hp_end, hp_filename = historical_price_collector.get_source_metadata_from_csv(f"Historical Price_{asset}")
            daily_table.set_dates("Historical Price", hp_start, hp_end)
            daily_table.set_filename("Historical Price", hp_filename)
            
            # --- Update Monthly metadata ---
            # TODO: update Google Trends metadata for this asset
            
        print("Metadata display updated.")

    def update_data(self):
        """Fetch latest data for all sources and refresh tables."""
        print("Update Data clicked – (partially) in progress...")

        # --- Update Daily Data ---
        price_collector.update_all_price_data()
        cvd_collector.update_all_cvd_data()
        oi_collector.update_all_oi_data()
        liquidation_collector.update_all_liquidation_data()
        historical_price_collector.update_all_historical_data()
        intraday_price_collector.update_all_intraday_price_data()

        # --- Update Monthly Data ---
        # TODO: Add call for Google Trends

        # update metadata
        self.update_metadata()

    def update_historical_prices(self):
        """Fetch latest historical prices and refresh tables."""
        print("Update Historical Prices clicked...")
        historical_price_collector.update_all_historical_data()
        self.update_metadata()

    def update_plots(self):
        """Generate / refresh plots for all configured assets based on existing data."""
        print("Update Plots clicked - generating plots for all assets...")

        # --- Load asset list from config ---
        try:
            with open("data/config.json", 'r') as f:
                config = json.load(f)
            assets = config.get("assets", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading or parsing config file: {e}")
            return

        for symbol in assets:
            print(f"\n--- Generating plots for {symbol} ---")
            
            # --- Generate Price Plot ---
            price_data_path = price_collector.get_price_data_filepath(symbol)
            if os.path.exists(price_data_path):
                price_plotter.generate_price_plot(data_path=price_data_path, symbol=symbol)
            else:
                print(f"Plotting failed: Price data file not found at {price_data_path}")

            # TODO: Refactor other plotters (CVD, OI, Combined) to be asset-aware
            # The code below will still use the old hardcoded paths until refactored.

            # --- Generate CVD Plot ---
            cvd_data_path = cvd_collector.get_cvd_data_filepath(symbol)
            if os.path.exists(cvd_data_path):
                cvd_plotter.generate_cvd_plot(data_path=cvd_data_path, symbol=symbol)
            else:
                print(f"Plotting failed: CVD data file not found at {cvd_data_path}")
            
            # --- Generate OI Plot ---
            oi_data_path = oi_collector.get_oi_data_filepath(symbol)
            if os.path.exists(oi_data_path):
                oi_plotter.generate_oi_plot(data_path=oi_data_path, symbol=symbol)
            else:
                print(f"Plotting failed: Open Interest data file not found at {oi_data_path}")

            # --- Generate Liquidation Plot ---
            liq_data_path = liquidation_collector.get_liquidation_data_filepath(symbol)
            if os.path.exists(liq_data_path):
                liquidation_plotter.generate_liquidation_plot(data_path=liq_data_path, symbol=symbol)
            else:
                print(f"Plotting failed: Liquidation data file not found at {liq_data_path}")

            # --- Generate Combined Plot ---
            price_path = price_collector.get_price_data_filepath(symbol)
            cvd_path = cvd_collector.get_cvd_data_filepath(symbol)
            oi_path = oi_collector.get_oi_data_filepath(symbol)

            if all(os.path.exists(p) for p in [price_path, cvd_path, oi_path]):
                combined_plotter.generate_combined_plot(
                    price_path=price_path,
                    cvd_path=cvd_path,
                    oi_path=oi_path,
                    symbol=symbol
                )
            else:
                print(f"Combined plotting for {symbol} failed: One or more data files are missing.")

            # --- Generate Technical Analysis Plot ---
            technical_plotter.generate_technical_plot(symbol=symbol, timeframe='daily')
            technical_plotter.generate_technical_plot(symbol=symbol, timeframe='weekly', last_n_periods=104) # 2 years of weekly data

            # --- Generate UT Bot Alerts Plot ---
            technical_plotter.generate_ut_bot_plot(symbol=symbol, timeframe='daily')
            technical_plotter.generate_ut_bot_plot(symbol=symbol, timeframe='weekly', last_n_periods=104)

            # --- Generate BB on MACD Plot ---
            technical_plotter.generate_bb_macd_plot(symbol=symbol, timeframe='daily')
            technical_plotter.generate_bb_macd_plot(symbol=symbol, timeframe='weekly', last_n_periods=104)

            # --- Generate Heikin Ashi Plot ---
            heikin_ashi_plotter.generate_heikin_ashi_plot(symbol=symbol, timeframe='daily')
            heikin_ashi_plotter.generate_heikin_ashi_plot(symbol=symbol, timeframe='weekly', last_n_periods=104)

    def update_analysis(self, symbol: str | None = None):
        """
        Generate / refresh analysis signals.
        If a symbol is provided, runs only for that asset.
        Otherwise, runs for all assets in the config.
        """
        if symbol:
            print(f"Update Analysis for {symbol} clicked...")
            assets_to_run = [symbol]
        else:
            print("Update Analysis clicked - generating signals for all assets...")
            assets_to_run = self._load_assets()

        if not assets_to_run:
            print("No assets found to analyze.")
            return

        # --- Weekly Run Analysis Distribution Update ---
        if self._should_update_run_distributions():
            print("\nUpdating run analysis probability distributions (weekly task)...")
            run_analyzer.update_all_distributions()
            self._update_run_distributions_timestamp()
            print("Run analysis distributions updated for all assets.")

        # Define the mapping from our standard data names to the actual column names in the CSVs
        column_map = {
            "price": "close",
            "oi": "sumOpenInterestValue",
            "cvd": "CVD"
        }

        for asset_symbol in assets_to_run:
            print(f"--- Generating analysis for {asset_symbol} ---")

            # --- Run 8-State Analysis ---
            price_data_path = historical_price_collector.get_historical_price_data_filepath(asset_symbol)
            oi_data_path = oi_collector.get_oi_data_filepath(asset_symbol)
            cvd_data_path = cvd_collector.get_cvd_data_filepath(asset_symbol)

            # Check if all necessary data files exist before running the analyzer
            if all(os.path.exists(p) for p in [price_data_path, oi_data_path, cvd_data_path]):
                eight_state_analyzer.generate_signals(
                    price_path=price_data_path,
                    oi_path=oi_data_path,
                    cvd_path=cvd_data_path,
                    symbol=asset_symbol,
                    column_map=column_map
                )
            else:
                print(f"Signal generation for {asset_symbol} failed: One or more required data files are missing.")
                if not os.path.exists(price_data_path): print(f"  - Missing: {price_data_path}")
                if not os.path.exists(oi_data_path): print(f"  - Missing: {oi_data_path}")
                if not os.path.exists(cvd_data_path): print(f"  - Missing: {cvd_data_path}")

            # --- Run Instability Analysis ---
            liquidation_path = liquidation_collector.get_liquidation_data_filepath(asset_symbol)
            if os.path.exists(liquidation_path):
                instability_analyzer.generate_instability_analysis(
                    liquidation_path=liquidation_path,
                    symbol=asset_symbol
                )
            else:
                print(f"Instability analysis for {asset_symbol} failed: Liquidation data file not found.")
                print(f"  - Missing: {liquidation_path}")

            # --- Run Volatility Analysis ---
            historical_price_path = historical_price_collector.get_historical_price_data_filepath(asset_symbol)
            if os.path.exists(historical_price_path):
                price_volatility_analyzer.generate_volatility_analysis(
                    price_path=historical_price_path,
                    symbol=asset_symbol
                )
            else:
                print(f"Volatility analysis for {asset_symbol} failed: Historical price data file not found.")
                print(f"  - Missing: {historical_price_path}")

            # --- Run Technical Analysis ---
            technical_analyzer.generate_technical_analysis(asset_symbol, timeframe='daily')
            technical_analyzer.generate_technical_analysis(asset_symbol, timeframe='weekly')

            # --- Run Daily Run Analysis ---
            run_predictor.generate_daily_prediction_file(asset_symbol)

    def update_archive_display(self):
        """Refreshes the GUI label showing the last archive date."""
        print("Updating archive status display...")
        last_archive_date = archiver.get_last_archive_date()
        if last_archive_date:
            display_text = f"Last Archive Date: {last_archive_date}"
        else:
            display_text = "Last Archive Date: Never"
        self.archive_status_label.config(text=display_text)
        print("Archive status display updated.")

    def update_signals(self):
        """Generate / refresh signals based on existing data."""
        # TODO: Implement signal generation logic
        print("Update Signals clicked – coming soon...")

    def update_all(self):
        """Convenience method – update data then plots."""
        self.update_data()
        self.update_plots()
        self.update_analysis()
        archiver.update_archive()
        self.update_archive_display()


if __name__ == "__main__":
    app = App()
    app.mainloop()


import os
import sys

# --- Add project root to sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
# ---------------------------------------

from main import App

def regenerate():
    """
    Instantiates the main App and calls the update_analysis method
    to regenerate all analysis files based on the latest data.
    """
    print("--- Starting signal regeneration process ---")
    
    # We don't need the GUI, but the App class holds the update logic.
    # We can instantiate it and call the method directly.
    app_logic = App()
    
    # We need to destroy the window immediately as we are not running the mainloop
    app_logic.destroy()
    
    app_logic.update_analysis()
    
    print("\n--- Signal regeneration complete ---")

if __name__ == "__main__":
    regenerate() 
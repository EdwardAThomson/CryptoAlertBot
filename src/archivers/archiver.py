import os
import shutil
from datetime import datetime, timedelta

# --- Constants ---
ARCHIVE_ROOT_DIR = "archive"
METADATA_FILE = os.path.join(ARCHIVE_ROOT_DIR, "last_archive_date.txt")
DIRECTORIES_TO_ARCHIVE = ["data", "plots"]
ARCHIVE_INTERVAL_DAYS = 7

# --- Main Public Function ---
def update_archive():
    """
    Checks if an archive is due and creates one if necessary.
    This is the main entry point to be called from the application.
    """
    print("Checking if data archive is due...")
    if _is_archive_due():
        print("Archive is due. Starting archival process...")
        _create_new_archive()
    else:
        last_date = get_last_archive_date()
        print(f"Archive not due. Last archive was on {last_date}. Next due in {ARCHIVE_INTERVAL_DAYS} days.")

# --- Helper Functions (Internal) ---

def get_last_archive_date() -> str | None:
    """Reads the last archive date from the metadata file."""
    if not os.path.exists(METADATA_FILE):
        return None
    try:
        with open(METADATA_FILE, 'r') as f:
            return f.read().strip()
    except Exception:
        return None

def _is_archive_due() -> bool:
    """
    Determines if a new archive should be created based on the last archive date.
    """
    last_archive_date_str = get_last_archive_date()
    
    if last_archive_date_str is None:
        print("No previous archive metadata found. An archive is required.")
        return True
        
    try:
        last_archive_date = datetime.strptime(last_archive_date_str, '%Y-%m-%d')
        days_since_last_archive = (datetime.now() - last_archive_date).days
        
        if days_since_last_archive >= ARCHIVE_INTERVAL_DAYS:
            return True
        else:
            return False
            
    except ValueError:
        print(f"Warning: Could not parse date from {METADATA_FILE}. Assuming archive is due to be safe.")
        return True

def _create_new_archive():
    """
    Performs the actual file operations for creating the archive.
    """
    today_str = datetime.now().strftime('%Y%m%d')
    new_archive_path = os.path.join(ARCHIVE_ROOT_DIR, today_str)

    try:
        # Create the main dated archive folder
        os.makedirs(new_archive_path, exist_ok=True)
        print(f"Created new archive directory: {new_archive_path}")

        all_copied_successfully = True
        for dir_name in DIRECTORIES_TO_ARCHIVE:
            source_path = dir_name
            destination_path = os.path.join(new_archive_path, dir_name)
            
            if not os.path.exists(source_path):
                print(f"Warning: Source directory '{source_path}' not found. Skipping.")
                continue

            print(f"  - Copying '{source_path}' to '{destination_path}'...")
            try:
                shutil.copytree(source_path, destination_path)
            except FileExistsError:
                # If the dir already exists for some reason, remove and retry
                print(f"    - Destination '{destination_path}' exists. Replacing.")
                shutil.rmtree(destination_path)
                shutil.copytree(source_path, destination_path)

        _update_archive_metadata()
        print("\nArchive created successfully.")

    except Exception as e:
        print(f"\nERROR: An unexpected error occurred during archiving: {e}")
        print("Archive may be incomplete. Metadata file was not updated.")

def _update_archive_metadata():
    """
    Writes the current date to the metadata file.
    """
    try:
        os.makedirs(ARCHIVE_ROOT_DIR, exist_ok=True)
        today_str = datetime.now().strftime('%Y-%m-%d')
        with open(METADATA_FILE, 'w') as f:
            f.write(today_str)
        print(f"Updated archive metadata file with new date: {today_str}")
    except IOError as e:
        print(f"ERROR: Could not write to metadata file {METADATA_FILE}: {e}")

# --- Example Usage (for direct testing) ---
# if __name__ == '__main__':
#     print("--- Running Archiver Directly for Testing ---")
    
#     # Create dummy directories and files for a robust test
#     print("\n1. Setting up dummy 'data' and 'plots' directories...")
#     os.makedirs("data/daily", exist_ok=True)
#     os.makedirs("data/analysis", exist_ok=True)
#     os.makedirs("plots", exist_ok=True)
#     with open("data/daily/dummy_price.csv", "w") as f:
#         f.write("date,price\n2023-01-01,100\n")
#     with open("data/analysis/dummy_signals.csv", "w") as f:
#         f.write("date,signal\n2023-01-01,Buy\n")
#     with open("plots/dummy_plot.png", "wb") as f:
#         # A simple 1x1 black pixel PNG
#         f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90\wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82')

#     print("Dummy files created.")

#     # To test the "due date" logic, you can manually create an old metadata file
#     # print("\n(Optional) Simulating an old archive date...")
#     # os.makedirs(ARCHIVE_ROOT_DIR, exist_ok=True)
#     # with open(METADATA_FILE, 'w') as f:
#     #     f.write("2023-01-01")

#     print("\n2. Calling the main update_archive() function...")
#     update_archive()
    
#     print("\n--- Test Complete ---") 
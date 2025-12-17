#!/usr/bin/env python3
"""
Quick script to generate the full report without AI calls.
This is useful for testing formatting and logic changes.
"""

import os
import sys

# Set the environment variable to disable AI
os.environ['DISABLE_AI_REPORTING'] = 'true'

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.reporters.markdown_reporter import generate_report

if __name__ == '__main__':
    print("Generating report without AI calls...")
    generate_report()
    print("Report generated successfully!") 
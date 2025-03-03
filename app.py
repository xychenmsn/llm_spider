#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - URL Parser Management Application

A PySide6 application for managing URL parsers.
"""

import sys
import signal
import logging
from PySide6 import QtWidgets, QtCore

from ui.parser_list import ParserListWindow

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def signal_handler(signum, frame):
    """Handle termination signals to ensure clean shutdown."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    QtWidgets.QApplication.quit()

def main():
    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    
    # Set up signal handlers for graceful termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create a timer to process Python signals
    timer = QtCore.QTimer()
    timer.start(500)  # Check for signals every 500ms
    timer.timeout.connect(lambda: None)  # Needed to process Python signals
    
    # Create and show the main window
    window = ParserListWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
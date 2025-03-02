#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - URL Parser Management Application

A PySide6 application for managing URL parsers.
"""

import sys
from PySide6 import QtWidgets

from ui.parser_list import ParserListWindow


def main():
    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    
    # Create and show the main window
    window = ParserListWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - URL Parser List Window

The main window for managing URL parsers.
"""

import re
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, Slot

from db.db_client import db_client
from db.models import URLParser
from parser_designer import ParserDesignerWindow
from ui.action_table import ActionTableWidget
from ui.parser_table_model import URLParserTableModel


class ParserListWindow(QtWidgets.QMainWindow):
    """Main application window for managing URL parsers."""
    
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("LLM Spider - URL Parser Management")
        self.setGeometry(100, 100, 1000, 600)
        
        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Top bar with URL input, Parse button, and New Parser button
        top_bar = QtWidgets.QHBoxLayout()
        
        # URL input
        self.url_input = QtWidgets.QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to parse...")
        top_bar.addWidget(self.url_input, 3)
        
        # Parse button
        parse_button = QtWidgets.QPushButton("Parse")
        parse_button.clicked.connect(self.parse_url)
        top_bar.addWidget(parse_button, 1)
        
        # New Parser button
        new_parser_button = QtWidgets.QPushButton("New Parser")
        new_parser_button.clicked.connect(self.create_parser)
        top_bar.addWidget(new_parser_button, 1)
        
        layout.addLayout(top_bar)
        
        # Create the table model
        self.model = URLParserTableModel()
        
        # Create a configuration dictionary for the action table
        table_config = {
            # Action buttons configuration
            'buttons': [
                {"name": "edit", "label": "Edit", "width": 80},
                {"name": "delete", "label": "Delete", "width": 80}
            ],
            
            # ID column name
            'id_column_name': "ID",
            
            # Column width percentages
            'column_widths': {
                "ID": 5,           # Very narrow for ID column
                "Name": 25,        # 25% of the remaining space
                "URL Pattern": 45, # 45% of the remaining space
                "Parser": 25       # 25% of the remaining space
            },
            
            # Disable horizontal scrolling
            'allow_horizontal_scroll': False
        }
        
        # Create the action table widget
        self.table_widget = ActionTableWidget(
            parent=self,
            model=self.model,
            config=table_config
        )
        
        # Connect the action_triggered signal to our handler
        self.table_widget.action_triggered.connect(self.handle_action)
        
        # Add table widget to the main layout
        layout.addWidget(self.table_widget)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def handle_action(self, row_id, action_name):
        """Handle action button clicks from the table."""
        if action_name == "edit":
            self.edit_parser(row_id)
        elif action_name == "delete":
            self.delete_parser(row_id)
    
    def parse_url(self):
        """Parse the URL entered in the input field."""
        url = self.url_input.text()
        if not url:
            self.statusBar().showMessage("Please enter a URL to parse")
            return
            
        # Find a matching parser for the URL
        for parser in self.model.parsers:
            if re.search(parser.url_pattern, url):
                self.statusBar().showMessage(f"Found matching parser: {parser.name}")
                
                # Open the parser designer for this parser
                designer = ParserDesignerWindow(self, parser.id, url=url)
                designer.parser_saved.connect(self.model.refresh_data)
                designer.show()
                return
        
        # No matching parser found
        self.statusBar().showMessage(f"No matching parser found for URL: {url}")
        
        # Ask if user wants to create a new parser
        reply = QtWidgets.QMessageBox.question(
            self, "Create New Parser?",
            "No matching parser found. Would you like to create a new one?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            designer = ParserDesignerWindow(self, url=url)
            designer.parser_saved.connect(self.model.refresh_data)
            designer.show()
    
    def create_parser(self):
        """Open dialog to create a new parser."""
        url = self.url_input.text().strip()
        designer = ParserDesignerWindow(self, url=url)
        designer.parser_saved.connect(self.model.refresh_data)
        designer.show()
    
    def edit_parser(self, parser_id):
        """Open dialog to edit an existing parser."""
        designer = ParserDesignerWindow(self, parser_id)
        designer.parser_saved.connect(self.model.refresh_data)
        designer.show()
    
    def delete_parser(self, parser_id):
        """Delete a parser after confirmation."""
        confirm = QtWidgets.QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this parser?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                db_client.delete(URLParser, parser_id)
                self.table_widget.refresh()
                self.statusBar().showMessage(f"Deleted parser ID: {parser_id}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to delete parser: {str(e)}"
                ) 
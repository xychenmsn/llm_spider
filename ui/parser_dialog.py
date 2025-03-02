#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - URL Parser Dialog

A dialog for creating or editing URL parsers.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, Slot
import json

from db.db_client import db_client
from db.models import URLParser


class ParserDialog(QtWidgets.QDialog):
    """Dialog for creating or editing a URL parser."""
    
    def __init__(self, parent=None, parser_id=None):
        super().__init__(parent)
        self.parser_id = parser_id
        self.parser = None
        
        if parser_id:
            self.setWindowTitle("Edit URL Parser")
            self.parser = db_client.get_by_id(URLParser, parser_id)
        else:
            self.setWindowTitle("New URL Parser")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setMinimumWidth(500)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Form layout for inputs
        form_layout = QtWidgets.QFormLayout()
        
        # Name field
        self.name_input = QtWidgets.QLineEdit()
        form_layout.addRow("Name:", self.name_input)
        
        # URL Pattern field
        self.pattern_input = QtWidgets.QLineEdit()
        form_layout.addRow("URL Pattern:", self.pattern_input)
        
        # Parser field
        self.parser_input = QtWidgets.QLineEdit()
        form_layout.addRow("Parser:", self.parser_input)
        
        # Meta Data field
        self.meta_input = QtWidgets.QTextEdit()
        self.meta_input.setMaximumHeight(100)
        form_layout.addRow("Meta Data (JSON):", self.meta_input)
        
        # Chat Data field
        self.chat_input = QtWidgets.QTextEdit()
        self.chat_input.setMaximumHeight(100)
        form_layout.addRow("Chat Data (JSON):", self.chat_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Fill fields if editing
        if self.parser:
            self.name_input.setText(self.parser.name)
            self.pattern_input.setText(self.parser.url_pattern)
            self.parser_input.setText(self.parser.parser)
            
            if self.parser.meta_data:
                self.meta_input.setText(json.dumps(self.parser.meta_data, indent=2))
                
            if self.parser.chat_data:
                self.chat_input.setText(json.dumps(self.parser.chat_data, indent=2))
    
    def get_parser_data(self):
        """Get the parser data from the form fields."""
        
        data = {
            'name': self.name_input.text(),
            'url_pattern': self.pattern_input.text(),
            'parser': self.parser_input.text()
        }
        
        # Parse JSON fields
        meta_text = self.meta_input.toPlainText().strip()
        if meta_text:
            try:
                data['meta_data'] = json.loads(meta_text)
            except json.JSONDecodeError:
                QtWidgets.QMessageBox.warning(
                    self, "Invalid JSON", "Meta Data contains invalid JSON."
                )
                return None
        
        chat_text = self.chat_input.toPlainText().strip()
        if chat_text:
            try:
                data['chat_data'] = json.loads(chat_text)
            except json.JSONDecodeError:
                QtWidgets.QMessageBox.warning(
                    self, "Invalid JSON", "Chat Data contains invalid JSON."
                )
                return None
        
        return data 
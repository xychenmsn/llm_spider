#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - URL Parser Table Model

A table model for displaying URL parsers in a table view.
"""

from PySide6 import QtCore
from PySide6.QtCore import Qt

from db.db_client import db_client
from db.models import URLParser


class URLParserTableModel(QtCore.QAbstractTableModel):
    """Model for displaying URL parsers in a table view."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parsers = []
        self.headers = ["ID", "Name", "URL Pattern", "Parser", "Actions"]
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh data from the database."""
        self.beginResetModel()
        self.parsers = db_client.get_all(URLParser)
        self.endResetModel()
    
    def rowCount(self, parent=None):
        return len(self.parsers)
    
    def columnCount(self, parent=None):
        return len(self.headers)
    
    def data(self, index, role):
        if not index.isValid():
            return None
            
        if role == Qt.DisplayRole:
            parser = self.parsers[index.row()]
            col = index.column()
            
            if col == 0:
                return str(parser.id)
            elif col == 1:
                return parser.name
            elif col == 2:
                return parser.url_pattern
            elif col == 3:
                return parser.parser
            elif col == 4:
                return None  # Actions column handled by delegate
                
        return None
    
    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None 
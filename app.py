#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - URL Parser Management Application

A PySide6 application for managing URL parsers.
"""

import sys
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, Slot

from db.db_client import db_client
from db.models import URLParser
from parser_designer import ParserDesignerWindow

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


class ButtonDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate for rendering action buttons in the table."""
    
    edit_clicked = Signal(int)
    delete_clicked = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def paint(self, painter, option, index):
        if index.column() == 4:  # Actions column
            # Create a widget to hold the buttons
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(10)
            
            # Edit button
            edit_button = QtWidgets.QPushButton("Edit")
            layout.addWidget(edit_button)
            
            # Delete button
            delete_button = QtWidgets.QPushButton("Delete")
            layout.addWidget(delete_button)
            
            # Calculate the size and position
            widget.setGeometry(option.rect)
            
            # Use a pixmap to render the widget
            pixmap = QtGui.QPixmap(option.rect.size())
            pixmap.fill(Qt.transparent)
            widget.render(pixmap)
            
            # Draw the pixmap
            painter.drawPixmap(option.rect, pixmap)
        else:
            super().paint(painter, option, index)
    
    def editorEvent(self, event, model, option, index):
        if index.column() == 4 and event.type() == QtCore.QEvent.MouseButtonRelease:
            # Calculate button positions
            rect = option.rect
            button_width = rect.width() // 2 - 10
            
            # Check if edit button was clicked
            edit_rect = QtCore.QRect(rect.left() + 4, rect.top() + 4, button_width, rect.height() - 8)
            if edit_rect.contains(event.position().toPoint()):
                self.edit_clicked.emit(model.data(model.index(index.row(), 0), Qt.DisplayRole))
                return True
                
            # Check if delete button was clicked
            delete_rect = QtCore.QRect(rect.right() - button_width - 4, rect.top() + 4, button_width, rect.height() - 8)
            if delete_rect.contains(event.position().toPoint()):
                self.delete_clicked.emit(model.data(model.index(index.row(), 0), Qt.DisplayRole))
                return True
                
        return super().editorEvent(event, model, option, index)
    
    def sizeHint(self, option, index):
        if index.column() == 4:
            return QtCore.QSize(200, 40)
        return super().sizeHint(option, index)


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
                import json
                self.meta_input.setText(json.dumps(self.parser.meta_data, indent=2))
                
            if self.parser.chat_data:
                import json
                self.chat_input.setText(json.dumps(self.parser.chat_data, indent=2))
    
    def get_parser_data(self):
        """Get the parser data from the form fields."""
        import json
        
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


class MainWindow(QtWidgets.QMainWindow):
    """Main application window."""
    
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
        
        # Create a scroll area for the table view
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget for the table
        table_container = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_container)
        
        # Table view for URL parsers
        self.table_view = QtWidgets.QTableView()
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(False)
        
        # Set up the model and delegate
        self.model = URLParserTableModel()
        self.table_view.setModel(self.model)
        
        self.button_delegate = ButtonDelegate()
        self.button_delegate.edit_clicked.connect(self.edit_parser)
        self.button_delegate.delete_clicked.connect(self.delete_parser)
        self.table_view.setItemDelegateForColumn(4, self.button_delegate)
        
        # Set column widths
        self.table_view.setColumnWidth(0, 50)   # ID
        self.table_view.setColumnWidth(1, 200)  # Name
        self.table_view.setColumnWidth(2, 300)  # URL Pattern
        self.table_view.setColumnWidth(3, 200)  # Parser
        
        # Add table to the container layout
        table_layout.addWidget(self.table_view)
        
        # Set the container as the scroll area widget
        scroll_area.setWidget(table_container)
        
        # Add scroll area to the main layout
        layout.addWidget(scroll_area)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def parse_url(self):
        """Parse the URL entered in the input field."""
        url = self.url_input.text()
        if not url:
            self.statusBar().showMessage("Please enter a URL to parse")
            return
            
        # Find a matching parser for the URL
        import re
        for parser in self.model.parsers:
            if re.search(parser.url_pattern, url):
                self.statusBar().showMessage(f"Found matching parser: {parser.name}")
                
                # Open the parser designer for this parser
                designer = ParserDesignerWindow(self, parser.id)
                designer.exec()
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
            designer = ParserDesignerWindow(self)
            designer.exec()
    
    def create_parser(self):
        """Open dialog to create a new parser."""
        designer = ParserDesignerWindow(self)
        if designer.exec():
            # Refresh the model to show the new parser
            self.model.refresh_data()
    
    def edit_parser(self, parser_id):
        """Open dialog to edit an existing parser."""
        designer = ParserDesignerWindow(self, parser_id)
        if designer.exec():
            # Refresh the model to show the updated parser
            self.model.refresh_data()
    
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
                self.model.refresh_data()
                self.statusBar().showMessage(f"Deleted parser ID: {parser_id}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to delete parser: {str(e)}"
                )


def main():
    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
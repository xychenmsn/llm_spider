#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Spider - Action Table Component

A reusable table component that supports action buttons in the last column.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, Signal, Slot


class ActionButtonDelegate(QtWidgets.QStyledItemDelegate):
    """
    A delegate for rendering action buttons in a table cell.
    
    This delegate renders configurable action buttons in the last column of a table
    and emits signals when buttons are clicked.
    """
    
    button_clicked = Signal(int, str)  # row_id, button_name
    
    def __init__(self, parent=None, buttons=None, id_column=0):
        """
        Initialize the action button delegate.
        
        Args:
            parent: Parent widget
            buttons: List of button configs, each as {"name": "name", "label": "Label", "width": 80}
            id_column: Column index that contains the row ID
        """
        super().__init__(parent)
        self.buttons = buttons or []
        self.id_column = id_column
        
        # Calculate total width needed for all buttons
        self.total_width = sum(button.get("width", 80) for button in self.buttons)
        self.total_width += (len(self.buttons) - 1) * 10  # Add spacing
    
    def paint(self, painter, option, index):
        """Paint the delegate."""
        if index.column() == index.model().columnCount() - 1:  # Last column
            # Create a widget to hold the buttons
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(10)
            
            # Add buttons based on configuration
            for button_config in self.buttons:
                button = QtWidgets.QPushButton(button_config.get("label", button_config.get("name", "")))
                if "width" in button_config:
                    button.setFixedWidth(button_config["width"])
                layout.addWidget(button)
            
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
        """Handle editor events (mouse clicks)."""
        if (index.column() == index.model().columnCount() - 1 and 
                event.type() == QtCore.QEvent.MouseButtonRelease):
            
            # Get the row ID from the ID column
            row_id = model.data(model.index(index.row(), self.id_column), Qt.DisplayRole)
            
            # Calculate button positions
            rect = option.rect
            x_pos = rect.left() + 4
            
            # Check which button was clicked
            for button_config in self.buttons:
                button_width = button_config.get("width", 80)
                button_rect = QtCore.QRect(x_pos, rect.top() + 4, button_width, rect.height() - 8)
                
                if button_rect.contains(event.position().toPoint()):
                    self.button_clicked.emit(int(row_id), button_config["name"])
                    return True
                
                # Move to next button position
                x_pos += button_width + 10
            
        return super().editorEvent(event, model, option, index)
    
    def sizeHint(self, option, index):
        """Provide size hint for the cell."""
        if index.column() == index.model().columnCount() - 1:
            return QtCore.QSize(self.total_width + 20, 40)  # Add padding
        return super().sizeHint(option, index)


class ActionTableView(QtWidgets.QTableView):
    """
    A table view that supports action buttons in the last column.
    
    This is a customized QTableView that automatically sets up action buttons
    in the last column based on configuration.
    """
    
    action_triggered = Signal(int, str)  # row_id, action_name
    
    def __init__(self, parent=None, config=None):
        """
        Initialize the action table view.
        
        Args:
            parent: Parent widget
            config: Configuration dictionary with the following options:
                - buttons: List of button configs, each as {"name": "name", "label": "Label", "width": 80}
                - id_column_name: Name of the column containing row IDs (default: "ID")
                - column_widths: Dict mapping column names to percentages (e.g., {"ID": 10, "Name": 30})
                - allow_horizontal_scroll: Whether to allow horizontal scrolling (default: False)
        """
        super().__init__(parent)
        
        # Set default configuration
        self.config = {
            'buttons': [],
            'id_column_name': "ID",
            'column_widths': {},
            'allow_horizontal_scroll': False
        }
        
        # Update with provided configuration
        if config:
            self.config.update(config)
        
        # Set up table view properties
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().setVisible(False)
        
        # Disable horizontal scrolling if configured
        if not self.config['allow_horizontal_scroll']:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # We'll set up the button delegate in setModel
        self.button_delegate = None
    
    def setModel(self, model):
        """Set the model for the view and configure the button delegate."""
        super().setModel(model)
        
        # Set the delegate for the last column
        if model and model.columnCount() > 0:
            last_column = model.columnCount() - 1
            
            # Find the ID column index based on the column name
            id_column = 0  # Default to first column
            for i in range(last_column + 1):
                header_text = model.headerData(i, Qt.Horizontal, Qt.DisplayRole)
                if header_text == self.config['id_column_name']:
                    id_column = i
                    break
            
            # Create the button delegate
            self.button_delegate = ActionButtonDelegate(
                parent=self,
                buttons=self.config['buttons'],
                id_column=id_column
            )
            self.button_delegate.button_clicked.connect(self.action_triggered)
            self.setItemDelegateForColumn(last_column, self.button_delegate)
            
            # Set fixed width for the action column
            total_width = sum(button.get("width", 80) for button in self.config['buttons'])
            total_width += (len(self.config['buttons']) - 1) * 10  # Add spacing
            action_column_width = total_width + 20  # Add padding
            self.setColumnWidth(last_column, action_column_width)
            
            # Apply column width percentages if provided
            if self.config['column_widths'] and len(self.config['column_widths']) > 0:
                # First set all columns to stretch mode
                self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
                
                # Then apply custom stretch factors based on percentages
                for i in range(last_column):
                    self.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.Interactive)
                
                # Set the last column to fixed size
                self.horizontalHeader().setSectionResizeMode(last_column, QtWidgets.QHeaderView.Fixed)
            else:
                # Default behavior: make all columns stretch equally
                self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
                # Set the last column to fixed size
                self.horizontalHeader().setSectionResizeMode(last_column, QtWidgets.QHeaderView.Fixed)
    
    def showEvent(self, event):
        """Handle the show event to apply percentage-based column widths."""
        super().showEvent(event)
        self._apply_column_widths()
    
    def resizeEvent(self, event):
        """Handle resize events to maintain percentage-based column widths."""
        super().resizeEvent(event)
        self._apply_column_widths()
    
    def _apply_column_widths(self):
        """Apply percentage-based column widths."""
        if not self.model() or not self.config['column_widths']:
            return
            
        last_column = self.model().columnCount() - 1
        
        # Get the total width available for columns (excluding the action column)
        action_column_width = self.columnWidth(last_column)
        
        # Calculate total available width more accurately
        # Subtract scrollbar width if vertical scrollbar is visible
        scrollbar_width = 0
        if self.verticalScrollBar().isVisible():
            scrollbar_width = self.verticalScrollBar().width()
        
        # Calculate available width for content columns
        total_available_width = self.width() - action_column_width - scrollbar_width
        
        # Get column names from the model's header data
        column_names = {}
        for i in range(last_column):
            header_text = self.model().headerData(i, Qt.Horizontal, Qt.DisplayRole)
            if header_text:
                column_names[i] = header_text
        
        # Apply percentage-based widths
        total_percentage = sum(self.config['column_widths'].values())
        
        for col_name, percentage in self.config['column_widths'].items():
            # Find the column index for this name
            col_index = None
            for i, name in column_names.items():
                if name == col_name:
                    col_index = i
                    break
            
            # If column name not found, try to use it as an index
            if col_index is None and isinstance(col_name, str) and col_name.isdigit():
                col_index = int(col_name)
            
            if col_index is not None and col_index < last_column:
                # Calculate width based on percentage of available space
                width = int(total_available_width * (percentage / total_percentage))
                self.setColumnWidth(col_index, width)


class ActionTableWidget(QtWidgets.QWidget):
    """
    A complete table widget with action buttons.
    
    This widget combines a table view with action buttons and provides
    a simple interface for setting up and using the table.
    """
    
    action_triggered = Signal(int, str)  # row_id, action_name
    
    def __init__(self, parent=None, model=None, config=None):
        """
        Initialize the action table widget.
        
        Args:
            parent: Parent widget
            model: The table model to use
            config: Configuration dictionary with the following options:
                - buttons: List of button configs, each as {"name": "name", "label": "Label", "width": 80}
                - id_column_name: Name of the column containing row IDs (default: "ID")
                - column_widths: Dict mapping column names to percentages (e.g., {"ID": 10, "Name": 30})
                - allow_horizontal_scroll: Whether to allow horizontal scrolling (default: False)
        """
        super().__init__(parent)
        
        # Store configuration
        self.model = model
        self.config = config or {}
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Set horizontal scroll policy based on configuration
        if self.config.get('allow_horizontal_scroll', False):
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create table container
        table_container = QtWidgets.QWidget()
        table_layout = QtWidgets.QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to prevent horizontal scrollbar
        
        # Create table view
        self.table_view = ActionTableView(
            parent=self,
            config=self.config
        )
        self.table_view.action_triggered.connect(self.action_triggered)
        
        # Set the model if provided
        if self.model:
            self.table_view.setModel(self.model)
        
        # Add table to container
        table_layout.addWidget(self.table_view)
        
        # Set container as scroll area widget
        scroll_area.setWidget(table_container)
        
        # Add scroll area to main layout
        layout.addWidget(scroll_area)
    
    def setModel(self, model):
        """Set the model for the table view."""
        self.model = model
        self.table_view.setModel(model)
    
    def model(self):
        """Get the current model."""
        return self.table_view.model()
    
    def refresh(self):
        """Refresh the table data if the model supports it."""
        if hasattr(self.model, 'refresh_data'):
            self.model.refresh_data()
    
    def setColumnWidth(self, column, width):
        """Set the width of a column."""
        self.table_view.setColumnWidth(column, width)
        
    def setConfig(self, config):
        """Update the configuration."""
        if not hasattr(self, 'config'):
            self.config = {}
        
        self.config.update(config)
        
        # Update table view configuration
        if hasattr(self, 'table_view'):
            self.table_view.config.update(config)
            
            # Apply horizontal scroll policy
            if 'allow_horizontal_scroll' in config:
                if config['allow_horizontal_scroll']:
                    self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                else:
                    self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # Trigger a resize to apply any new column widths
            if 'column_widths' in config and self.table_view.isVisible():
                self.table_view.resizeEvent(QtGui.QResizeEvent(
                    self.table_view.size(), self.table_view.size()
                )) 
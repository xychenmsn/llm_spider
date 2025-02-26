#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple PySide6 application with Material theme.
This demonstrates the basic setup for our Claude-style chat application.
"""

import sys
from PySide6 import QtWidgets, QtCore
from qt_material import apply_stylesheet

class SimpleWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("Material Theme Demo")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Add a title label
        title = QtWidgets.QLabel("Claude-Style Chat App")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(24)
        title.setFont(font)
        layout.addWidget(title)
        
        # Add a text area
        text_area = QtWidgets.QTextEdit()
        text_area.setPlaceholderText("This is where messages will appear...")
        layout.addWidget(text_area)
        
        # Add an input field and button in a horizontal layout
        input_layout = QtWidgets.QHBoxLayout()
        
        self.input_field = QtWidgets.QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        input_layout.addWidget(self.input_field)
        
        send_button = QtWidgets.QPushButton("Send")
        send_button.clicked.connect(self.on_send)
        input_layout.addWidget(send_button)
        
        layout.addLayout(input_layout)
        
        # Add a status bar
        self.statusBar().showMessage("Ready")
    
    def on_send(self):
        message = self.input_field.text()
        if message:
            self.statusBar().showMessage(f"Message sent: {message}")
            self.input_field.clear()


def main():
    # Create the application
    app = QtWidgets.QApplication(sys.argv)
    
    # Apply material theme
    apply_stylesheet(app, theme='dark_teal.xml')
    
    # Create and show the main window
    window = SimpleWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
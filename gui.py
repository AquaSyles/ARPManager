from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt

import sys
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.windowSizeWidth = 700
        self.windowSizeHeight = 500
        self.setWindowTitle('Title')
        self.setGeometry(0, 0, self.windowSizeWidth, self.windowSizeHeight)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a vertical layout
        self.layout = QVBoxLayout()        

        # Add widgets to the layout
        self.knownConsole = QTextEdit(self)
        self.unknownConsole = QTextEdit(self)

        self.layout.addWidget(self.knownConsole)        
        self.layout.addWidget(self.unknownConsole)        

        # Set the layout to the central widget
        central_widget.setLayout(self.layout)


app = QApplication(sys.argv)
window = MainWindow()

window.show()

sys.exit(app.exec())
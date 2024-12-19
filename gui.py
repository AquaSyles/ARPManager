from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel
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

        # Here I define the centralWidget to be a new widget
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        # Layouts
        outsideLayout = QVBoxLayout()
        # Layouts to add to the outside layout/main layout
        consoleContainerLayout = QVBoxLayout()        

        consoleColumnContainerLayout = QHBoxLayout()
        consoleColumnKnownLayout = QHBoxLayout()
        consoleColumnUnknownLayout = QHBoxLayout()

        consoleRowLayout = QHBoxLayout()
        consoleCommandLayout = QVBoxLayout()


        buttonLayout = QHBoxLayout() 

        # Define widgets to addd to layout here
        self.columnKnownNameLabel = QLabel('Name', self)
        self.columnKnownNameLabel.setStyleSheet('background-color: grey; color: black;')
        self.columnKnownIpLabel = QLabel('IP', self)
        self.columnKnownIpLabel.setStyleSheet('background-color: white; color: black;')
        self.columnKnownMacLabel = QLabel('MAC', self)
        self.columnKnownMacLabel.setStyleSheet('background-color: grey; color: black;')

        self.columnUnknownIpLabel = QLabel('IP', self)
        self.columnUnknownIpLabel.setStyleSheet('background-color: grey; color: black;')
        self.columnUnknownMacLabel = QLabel('MAC', self)
        self.columnUnknownMacLabel.setStyleSheet('background-color: white; color: black;')

        self.knownConsole = QTextEdit(self)
        self.unknownConsole = QTextEdit(self)
        self.updateButton = QPushButton(text='Update')

        # Add widgets to layouts here
        consoleColumnKnownLayout.addWidget(self.columnKnownNameLabel)
        consoleColumnKnownLayout.addWidget(self.columnKnownIpLabel)
        consoleColumnKnownLayout.addWidget(self.columnKnownMacLabel)

        consoleColumnUnknownLayout.addWidget(self.columnUnknownIpLabel)
        consoleColumnUnknownLayout.addWidget(self.columnUnknownMacLabel)

        consoleRowLayout.addWidget(self.knownConsole)        
        consoleRowLayout.addWidget(self.unknownConsole)   
        buttonLayout.addWidget(self.updateButton)

        # Set centralWidget to use outsideLayout which is the main layout
        centralWidget.setLayout(outsideLayout)
        # Add layouts to the main layout which is vertical
        outsideLayout.addLayout(consoleContainerLayout)
        outsideLayout.addLayout(buttonLayout)
        # Add layouts to the consoleContainerLayout
        consoleColumnContainerLayout.addLayout(consoleColumnKnownLayout)
        consoleColumnContainerLayout.addLayout(consoleColumnUnknownLayout)
        consoleContainerLayout.addLayout(consoleColumnContainerLayout)

        consoleContainerLayout.addLayout(consoleRowLayout)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        width = event.size().width()
        height = event.size().height()

        self.updateButton.setFixedSize(int(width/5), int(height/9))

        print(f"Window size: {width}x{height}")

app = QApplication(sys.argv)
window = MainWindow()

window.show()

sys.exit(app.exec())
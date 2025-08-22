from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtCore import QRegularExpression
from PyQt5 import Qt
import sys

class IPInputDialog(QDialog):
    def __init__(self, default_ip="192.168.40.2"):
        super().__init__()
        self.setWindowTitle("Enter USRP IP Address")
        self.ip_address = default_ip

        self.label = QLabel("Enter IP address of USRP (e.g. 192.168.1.10):")
        self.input = QLineEdit()
        self.input.setText(default_ip)

        # Regular expression for validating IPv4 addresses
        ip_regex = QRegularExpression(
            r'^((25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})\.){3}(25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})$'
        )
        ip_validator = QRegularExpressionValidator(ip_regex)
        self.input.setValidator(ip_validator)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.validate_and_accept)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

    def validate_and_accept(self):
        if self.input.hasAcceptableInput():
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid IP", "Please enter a valid IPv4 address.")

    def get_ip(self):
        return self.input.text().strip()
    
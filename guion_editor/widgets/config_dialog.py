# guion_editor/widgets/config_dialog.py

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt

class ConfigDialog(QDialog):
    def __init__(self, current_trim=0, current_font_size=12):
        super().__init__()
        self.setWindowTitle("Configuración")
        self.setFixedSize(300, 200)
        self.init_ui(current_trim, current_font_size)

    def init_ui(self, current_trim: int, current_font_size: int) -> None:
        layout = QVBoxLayout()

        # Configuración de TRIM
        trim_layout = QHBoxLayout()
        trim_label = QLabel("Trim (ms):")
        self.trim_spinbox = QSpinBox()
        self.trim_spinbox.setRange(0, 10000)
        self.trim_spinbox.setValue(current_trim)
        trim_layout.addWidget(trim_label)
        trim_layout.addWidget(self.trim_spinbox)
        layout.addLayout(trim_layout)

        # Configuración del tamaño de la fuente
        font_layout = QHBoxLayout()
        font_label = QLabel("Tamaño de Fuente:")
        self.font_spinbox = QSpinBox()
        self.font_spinbox.setRange(8, 48)
        self.font_spinbox.setValue(current_font_size)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_spinbox)
        layout.addLayout(font_layout)

        # Botones Aceptar y Cancelar
        buttons_layout = QHBoxLayout()
        self.accept_button = QPushButton("Aceptar")
        self.accept_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.accept_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def get_values(self) -> tuple:
        return self.trim_spinbox.value(), self.font_spinbox.value()

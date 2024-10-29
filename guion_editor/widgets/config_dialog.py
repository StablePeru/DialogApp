# guion_editor/widgets/config_dialog.py

import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QHBoxLayout
)


class ConfigDialog(QDialog):
    """
    Ventana de configuración para ajustar el valor de TRIM y el tamaño de la fuente.
    """
    def __init__(self, current_trim=0, current_font_size=12):
        super().__init__()
        self.setup_logging()
        self.setWindowTitle("Configuración")
        self.setFixedSize(300, 200)
        self.init_ui(current_trim, current_font_size)
        self.logger.debug("ConfigDialog inicializado correctamente.")

    def setup_logging(self) -> None:
        """
        Configura el sistema de logging para la clase.
        """
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)

    def init_ui(self, current_trim: int, current_font_size: int) -> None:
        """
        Inicializa la interfaz de usuario del diálogo.

        Args:
            current_trim (int): Valor actual de TRIM en milisegundos.
            current_font_size (int): Tamaño de fuente actual.
        """
        layout = QVBoxLayout()

        # Configuración de TRIM
        trim_layout = QHBoxLayout()
        trim_label = QLabel("Trim (ms):")
        trim_label.setObjectName("trim_label")
        self.trim_spinbox = QSpinBox()
        self.trim_spinbox.setObjectName("trim_spinbox")
        self.trim_spinbox.setRange(0, 10000)  # Rango de 0 a 10,000 ms
        self.trim_spinbox.setValue(current_trim)
        trim_layout.addWidget(trim_label)
        trim_layout.addWidget(self.trim_spinbox)
        layout.addLayout(trim_layout)

        # Configuración del tamaño de la fuente
        font_layout = QHBoxLayout()
        font_label = QLabel("Tamaño de Fuente:")
        font_label.setObjectName("font_label")
        self.font_spinbox = QSpinBox()
        self.font_spinbox.setObjectName("font_spinbox")
        self.font_spinbox.setRange(8, 48)  # Rango de 8 a 48 puntos
        self.font_spinbox.setValue(current_font_size)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_spinbox)
        layout.addLayout(font_layout)

        # Botones Aceptar y Cancelar
        buttons_layout = QHBoxLayout()
        self.accept_button = QPushButton("Aceptar")
        self.accept_button.setObjectName("accept_button")
        self.accept_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.accept_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def get_values(self) -> tuple:
        """
        Obtiene los valores seleccionados por el usuario.

        Returns:
            tuple: (trim, font_size)
        """
        trim_value = self.trim_spinbox.value()
        font_size = self.font_spinbox.value()
        self.logger.debug(f"Valores obtenidos - Trim: {trim_value} ms, Tamaño de Fuente: {font_size} pt")
        return trim_value, font_size

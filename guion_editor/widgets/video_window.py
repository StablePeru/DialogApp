# guion_editor/widgets/video_window.py

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

import logging

class VideoWindow(QMainWindow):
    """
    Ventana independiente para alojar el VideoPlayerWidget.
    """
    closeDetached = pyqtSignal()  # Señal para notificar que la ventana se ha cerrado

    def __init__(self, video_widget):
        super().__init__()
        self.setWindowTitle("Reproductor de Video Independiente")
        self.setGeometry(150, 150, 800, 600)
        self.setup_logging()
        self.init_ui(video_widget)
        self.logger.debug("VideoWindow inicializado correctamente.")

    def setup_logging(self):
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def init_ui(self, video_widget):
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Guardar la referencia del video_widget para reintegrarlo
        self.video_widget = video_widget
        self.video_widget.setParent(self)  # Asignar el nuevo padre

        # Añadir el VideoPlayerWidget pasado como argumento
        layout.addWidget(self.video_widget)

        # Botón para volver a adjuntar
        self.attachButton = QPushButton("Adjuntar de Nuevo")
        self.attachButton.setFont(QFont("Arial", 12))
        self.attachButton.clicked.connect(self.attach_back)
        layout.addWidget(self.attachButton)

        self.setCentralWidget(central_widget)
        self.logger.debug("VideoWidget añadido al layout de VideoWindow.")

    def attach_back(self):
        """
        Emitir una señal para adjuntar de nuevo el VideoPlayerWidget a la ventana principal.
        """
        self.closeDetached.emit()
        self.close()

    def closeEvent(self, event):
        """
        Emitir una señal cuando la ventana se cierra para asegurar que el widget sea adjuntado de nuevo.
        """
        self.closeDetached.emit()
        super().closeEvent(event)

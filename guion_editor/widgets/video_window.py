# guion_editor/widgets/video_window.py

import logging
import os
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton


class VideoWindow(QMainWindow):
    """
    Ventana independiente para alojar el VideoPlayerWidget.
    """
    close_detached = pyqtSignal()  # Señal para notificar que la ventana se ha cerrado

    def __init__(self, video_widget: QWidget):
        super().__init__()
        self.setup_logging()
        self.setWindowTitle("Reproductor de Video Independiente")
        self.setGeometry(150, 150, 800, 600)
        self.init_ui(video_widget)
        self.load_stylesheet()
        self.logger.debug("VideoWindow inicializado correctamente.")

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

    def init_ui(self, video_widget: QWidget) -> None:
        """
        Inicializa la interfaz de usuario de la ventana.

        Args:
            video_widget (QWidget): Instancia de VideoPlayerWidget a alojar.
        """
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Guardar la referencia del video_widget para reintegrarlo
        self.video_widget = video_widget
        self.video_widget.setParent(self)  # Asignar el nuevo padre

        # Asignar objectName para permitir estilos CSS
        self.video_widget.setObjectName("video_widget")

        # Añadir el VideoPlayerWidget pasado como argumento
        layout.addWidget(self.video_widget)

        # Botón para volver a adjuntar
        self.attach_button = QPushButton("Adjuntar de Nuevo")
        self.attach_button.setObjectName("attach_button")
        self.attach_button.setFont(QFont("Arial", 12))
        self.attach_button.clicked.connect(self.attach_back)
        layout.addWidget(self.attach_button)

        self.setCentralWidget(central_widget)
        self.logger.debug("VideoWidget añadido al layout de VideoWindow.")

    def load_stylesheet(self) -> None:
        """
        Carga el archivo de estilos CSS.
        """
        try:
            # Asumiendo que main.css está en una carpeta llamada 'styles' al mismo nivel que este archivo
            current_dir = os.path.dirname(os.path.abspath(__file__))
            css_path = os.path.join(current_dir, '..', 'styles', 'main.css')

            with open(css_path, 'r') as f:
                self.setStyleSheet(f.read())
            self.logger.debug(f"Stylesheet cargado desde: {css_path}")
        except Exception as e:
            self.logger.error(f"Error al cargar el stylesheet: {e}")

    def attach_back(self) -> None:
        """
        Emitir una señal para adjuntar de nuevo el VideoPlayerWidget a la ventana principal.
        """
        self.close_detached.emit()
        self.close()

    def closeEvent(self, event) -> None:
        """
        Emitir una señal cuando la ventana se cierra para asegurar que el widget sea adjuntado de nuevo.

        Args:
            event (QCloseEvent): Evento de cierre de la ventana.
        """
        self.close_detached.emit()
        super().closeEvent(event)

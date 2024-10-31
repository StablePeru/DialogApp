# simple_pyqt5_test.py
# -*- coding: utf-8 -*-

import sys
import logging
import faulthandler
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QPushButton, QVBoxLayout,
    QWidget, QDialog, QKeySequenceEdit, QMessageBox, QLabel
)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt, QSettings

# Habilitar faulthandler para capturar stack traces en fallos
faulthandler.enable()

# Configuración del logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("simple_pyqt5_debug.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class ShortcutConfigDialog(QDialog):
    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.new_shortcut = None  # Inicializar la variable
        self.setWindowTitle("Configurar Shortcut")
        self.setMinimumSize(300, 150)
        logger.debug("Inicializando ShortcutConfigDialog.")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Instrucción para el usuario
        instruction_label = QLabel("Presione las teclas para asignar el nuevo shortcut:")
        layout.addWidget(instruction_label)

        # Widget para editar la secuencia de teclas
        self.shortcut_edit = QKeySequenceEdit()
        self.shortcut_edit.setKeySequence(self.action.shortcut())  # Mostrar el shortcut actual
        self.shortcut_edit.keySequenceChanged.connect(self.on_key_sequence_changed)
        layout.addWidget(self.shortcut_edit)

        # Botón para asignar el shortcut
        self.assign_button = QPushButton("Asignar")
        self.assign_button.setEnabled(False)  # Deshabilitado hasta que se ingrese un shortcut válido
        self.assign_button.clicked.connect(self.assign_shortcut)
        layout.addWidget(self.assign_button)

        self.setLayout(layout)

    def on_key_sequence_changed(self, key_seq):
        logger.debug(f"Secuencia de teclas cambiada: {key_seq.toString(QKeySequence.NativeText)}")
        if key_seq.isEmpty():
            self.assign_button.setEnabled(False)
        else:
            self.assign_button.setEnabled(True)

    def assign_shortcut(self):
        logger.debug("Intentando asignar un nuevo shortcut.")
        key_seq = self.shortcut_edit.keySequence()
        if key_seq.isEmpty():
            QMessageBox.warning(self, "Advertencia", "Ingrese un shortcut válido.")
            logger.warning("No se ingresó un shortcut válido antes de intentar asignar.")
            return

        # Validar si el shortcut ya está en uso por otra acción
        main_window = self.parent()
        if main_window:
            for action in main_window.actions():
                if action != self.action and action.shortcut() == key_seq:
                    QMessageBox.warning(
                        self,
                        "Advertencia",
                        f"El shortcut '{key_seq.toString()}' ya está en uso por la acción '{action.text().replace('&', '')}'."
                    )
                    logger.warning(f"El shortcut '{key_seq.toString()}' ya está en uso por la acción '{action.text()}'.")
                    return

        try:
            self.action.setShortcut(key_seq)
            # Guardar el shortcut en QSettings
            settings = QSettings('MiEmpresa', 'MiAplicacion')
            settings.setValue(f'shortcuts/{self.action.objectName()}', key_seq.toString(QKeySequence.NativeText))
            QMessageBox.information(
                self,
                "Éxito",
                f"Shortcut asignado a '{self.action.text().replace('&', '')}'."
            )
            logger.info(f"Shortcut '{key_seq.toString()}' asignado a la acción '{self.action.text()}'.")
            self.close()
        except Exception as e:
            logger.error(f"Error al asignar shortcut: {e}")
            QMessageBox.warning(self, "Error", f"Error al asignar shortcut: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.debug("Inicializando MainWindow.")
        self.setWindowTitle("Ejemplo Simplificado de Shortcuts con PyQt5")
        self.setGeometry(100, 100, 400, 200)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Crear una acción
        self.abrir_video_action = QAction("&Abrir Video", self)
        self.abrir_video_action.setObjectName('abrir_video_action')  # Asignar un objectName único
        self.abrir_video_action.setShortcut(QKeySequence("Ctrl+O"))
        self.abrir_video_action.triggered.connect(self.abrir_video)
        self.addAction(self.abrir_video_action)  # Asegurarse de que la acción está añadida al QMainWindow

        # Crear un botón para abrir el diálogo de configuración de shortcuts
        config_button = QPushButton("Configurar Shortcut de 'Abrir Video'")
        config_button.clicked.connect(self.open_shortcut_dialog)
        layout.addWidget(config_button)

        # Crear otra acción para demostrar múltiples shortcuts (opcional)
        # Por ejemplo, una acción para "Guardar Video"
        self.guardar_video_action = QAction("&Guardar Video", self)
        self.guardar_video_action.setObjectName('guardar_video_action')
        self.guardar_video_action.setShortcut(QKeySequence("Ctrl+S"))
        self.guardar_video_action.triggered.connect(self.guardar_video)
        self.addAction(self.guardar_video_action)

        # Crear un botón para configurar el shortcut de "Guardar Video"
        guardar_config_button = QPushButton("Configurar Shortcut de 'Guardar Video'")
        guardar_config_button.clicked.connect(self.open_guardar_shortcut_dialog)
        layout.addWidget(guardar_config_button)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Cargar los shortcuts guardados
        self.load_shortcuts()

    def abrir_video(self):
        logger.debug("Acción 'Abrir Video' activada.")
        QMessageBox.information(self, "Abrir Video", "Acción 'Abrir Video' ejecutada.")

    def guardar_video(self):
        logger.debug("Acción 'Guardar Video' activada.")
        QMessageBox.information(self, "Guardar Video", "Acción 'Guardar Video' ejecutada.")

    def open_shortcut_dialog(self):
        logger.debug("Abriendo ShortcutConfigDialog para 'Abrir Video'.")
        try:
            dialog = ShortcutConfigDialog(self.abrir_video_action, self)
            dialog.setModal(True)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error al abrir ShortcutConfigDialog: {e}")
            QMessageBox.critical(self, "Error", f"Error al abrir el diálogo de shortcuts: {str(e)}")

    def open_guardar_shortcut_dialog(self):
        logger.debug("Abriendo ShortcutConfigDialog para 'Guardar Video'.")
        try:
            dialog = ShortcutConfigDialog(self.guardar_video_action, self)
            dialog.setModal(True)
            dialog.exec_()
        except Exception as e:
            logger.error(f"Error al abrir ShortcutConfigDialog: {e}")
            QMessageBox.critical(self, "Error", f"Error al abrir el diálogo de shortcuts: {str(e)}")

    def load_shortcuts(self):
        logger.debug("Cargando shortcuts desde QSettings.")
        try:
            settings = QSettings('MiEmpresa', 'MiAplicacion')
            # Cargar shortcut para 'Abrir Video'
            shortcut_abrir = settings.value(f'shortcuts/{self.abrir_video_action.objectName()}', "Ctrl+O")
            self.abrir_video_action.setShortcut(QKeySequence(shortcut_abrir))
            logger.info(f"Shortcut cargado para 'Abrir Video': {shortcut_abrir}")

            # Cargar shortcut para 'Guardar Video'
            shortcut_guardar = settings.value(f'shortcuts/{self.guardar_video_action.objectName()}', "Ctrl+S")
            self.guardar_video_action.setShortcut(QKeySequence(shortcut_guardar))
            logger.info(f"Shortcut cargado para 'Guardar Video': {shortcut_guardar}")
        except Exception as e:
            logger.error(f"Error al cargar shortcuts: {e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

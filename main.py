# main.py

import sys
import logging
import traceback

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QSplitter, QAction,
    QFileDialog, QMessageBox, QDialog, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence

from guion_editor.widgets.video_player_widget import VideoPlayerWidget
from guion_editor.widgets.table_window import TableWindow
from guion_editor.widgets.video_window import VideoWindow
from guion_editor.widgets.config_dialog import ConfigDialog
from guion_editor.widgets.shortcut_config_dialog import ShortcutConfigDialog
from guion_editor.utils.shortcut_manager import ShortcutManager

# Configuración del logger
logging.basicConfig(
    level=logging.DEBUG,  # Asegúrate de que el nivel esté en DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app_debug.log", encoding='utf-8')  # Opcional: Guardar logs en un archivo
    ]
)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Guion con Video")
        self.setGeometry(100, 100, 1600, 900)

        # Inicializar valores de configuración
        self.trim_value = 0
        self.font_size = 12

        # Crear el widget central y el layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Crear el splitter y agregar widgets
        self.splitter = QSplitter(Qt.Horizontal)
        self.videoPlayerWidget = VideoPlayerWidget()
        self.splitter.addWidget(self.videoPlayerWidget)
        self.tableWindow = TableWindow(self.videoPlayerWidget)
        self.splitter.addWidget(self.tableWindow)
        layout.addWidget(self.splitter)

        # Diccionario para almacenar las acciones
        self.actions = {}

        # Crear la barra de menú **sin** el menú de shortcuts
        self.create_menu_bar(exclude_shortcuts=True)
        logger.debug("Barra de menú creada sin el menú de shortcuts.")

        # Inicializar ShortcutManager **después** de crear la barra de menú
        self.shortcut_manager = ShortcutManager(self)
        logger.debug("ShortcutManager inicializado y asignado a 'self.shortcut_manager'.")

        # Crear el menú de shortcuts **después** de inicializar ShortcutManager
        self.create_shortcuts_menu(self.menuBar())

        # Conectar señales
        self.videoPlayerWidget.detach_requested.connect(self.detach_video)
        self.tableWindow.in_out_signal.connect(self.handle_set_position)

        # Variable para la ventana independiente
        self.videoWindow = None

        logger.debug("MainWindow inicializado correctamente.")

    def create_menu_bar(self, exclude_shortcuts=False):
        menuBar = self.menuBar()
        self.create_file_menu(menuBar)
        self.create_edit_menu(menuBar)
        self.create_config_menu(menuBar)
        if not exclude_shortcuts:
            self.create_shortcuts_menu(menuBar)

    def create_file_menu(self, menuBar):
        fileMenu = menuBar.addMenu("&Archivo")

        actions = [
            ("&Abrir Video", self.open_video, "Ctrl+O"),
            ("&Abrir Guion", self.tableWindow.open_file_dialog, "Ctrl+G"),
            ("&Exportar Guion a Excel", self.tableWindow.export_to_excel, "Ctrl+E"),
            ("&Importar Guion desde Excel", self.tableWindow.import_from_excel, "Ctrl+I"),
            ("&Guardar Guion como JSON", self.tableWindow.save_to_json, "Ctrl+S"),
            ("&Cargar Guion desde JSON", self.tableWindow.load_from_json, "Ctrl+D"),
        ]

        for name, slot, shortcut in actions:
            action = self.create_action(name, slot, shortcut)
            fileMenu.addAction(action)
            self.actions[name] = action  # Añadir al diccionario de acciones
            logger.debug(f"Acción añadida al menú Archivo: '{name}' con shortcut '{shortcut}'.")

    def create_edit_menu(self, menuBar):
        editMenu = menuBar.addMenu("&Editar")

        actions = [
            ("&Agregar Línea", self.tableWindow.add_new_row, "Ctrl+N"),
            ("&Eliminar Fila", self.tableWindow.remove_row, "Ctrl+Del"),
            ("Mover &Arriba", self.tableWindow.move_row_up, "Alt+Up"),
            ("Mover &Abajo", self.tableWindow.move_row_down, "Alt+Down"),
            ("&Ajustar Diálogos", self.tableWindow.adjust_dialogs, None),
            ("&Separar Intervención", self.tableWindow.split_intervention, "Alt+I"),
            ("&Juntar Intervenciones", self.tableWindow.merge_interventions, "Alt+J"),
        ]

        for name, slot, shortcut in actions:
            action = self.create_action(name, slot, shortcut)
            editMenu.addAction(action)
            self.actions[name] = action  # Añadir al diccionario de acciones
            logger.debug(f"Acción añadida al menú Editar: '{name}' con shortcut '{shortcut}'.")

    def create_config_menu(self, menuBar):
        configMenu = menuBar.addMenu("&Configuración")

        openConfigAction = self.create_action("&Configuración", self.open_config_dialog)
        configMenu.addAction(openConfigAction)
        self.actions["&Configuración"] = openConfigAction  # Añadir al diccionario de acciones
        logger.debug("Acción añadida al menú Configuración: '&Configuración'.")

    def create_shortcuts_menu(self, menuBar):
        shortcutsMenu = menuBar.addMenu("&Shortcuts")

        # Submenú para configurar shortcuts
        configure_shortcuts_action = self.create_action("&Configurar Shortcuts", self.open_shortcut_config_dialog)
        shortcutsMenu.addAction(configure_shortcuts_action)
        self.actions["&Configurar Shortcuts"] = configure_shortcuts_action  # Añadir al diccionario de acciones
        logger.debug("Acción añadida al menú Shortcuts: '&Configurar Shortcuts'.")

        # Submenú para cargar configuraciones existentes
        load_config_menu = shortcutsMenu.addMenu("Cargar Configuración")
        for config_name in self.shortcut_manager.get_available_configs():
            # Usar una función lambda con argumentos por defecto para evitar problemas de cierre
            action = self.create_action(
                config_name,
                lambda checked, name=config_name: self.shortcut_manager.apply_shortcuts(name)
            )
            load_config_menu.addAction(action)
            self.actions[config_name] = action  # Añadir al diccionario de acciones
            logger.debug(f"Acción añadida al submenú Cargar Configuración: '{config_name}'.")

        # Opción para eliminar configuraciones
        delete_config_action = self.create_action("Eliminar Configuración", self.delete_configuration)
        shortcutsMenu.addAction(delete_config_action)
        self.actions["Eliminar Configuración"] = delete_config_action  # Añadir al diccionario de acciones
        logger.debug("Acción añadida al menú Shortcuts: 'Eliminar Configuración'.")

    def create_action(self, name, slot, shortcut=None):
        action = QAction(name, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        logger.debug(f"Acción creada: '{name}' con shortcut '{shortcut}'.")
        return action

    def open_config_dialog(self):
        config_dialog = ConfigDialog(
            current_trim=self.trim_value,
            current_font_size=self.font_size
        )
        if config_dialog.exec_() == QDialog.Accepted:
            self.trim_value, self.font_size = config_dialog.get_values()
            logger.debug(
                f"Configuración actualizada: Trim={self.trim_value} ms, "
                f"Tamaño de Fuente={self.font_size} pt"
            )
            self.apply_font_size()

    def apply_font_size(self):
        """
        Aplica el tamaño de fuente configurado a los elementos relevantes.
        """
        # Ajustar el tamaño de la fuente en la tabla del guion
        font = self.tableWindow.tableWidget.font()
        font.setPointSize(self.font_size)
        self.tableWindow.tableWidget.setFont(font)

        # Ajustar la fuente de los encabezados si es necesario
        header = self.tableWindow.tableWidget.horizontalHeader()
        header_font = header.font()
        header_font.setPointSize(self.font_size)
        header.setFont(header_font)

        # Ajustar la fuente de los diálogos
        self.tableWindow.apply_font_size_to_dialogs(self.font_size)

        # Actualizar fuentes en VideoPlayerWidget
        self.videoPlayerWidget.update_fonts(self.font_size)

    def open_shortcut_config_dialog(self):
        dialog = ShortcutConfigDialog(self.shortcut_manager)
        dialog.exec_()
        # Aplicar los shortcuts después de configurar
        self.shortcut_manager.apply_shortcuts(self.shortcut_manager.current_config)

    def delete_configuration(self):
        configs = self.shortcut_manager.get_available_configs()
        if "default" in configs:
            configs.remove("default")  # No permitir eliminar 'default'
        if not configs:
            QMessageBox.information(self, "Información", "No hay configuraciones para eliminar.")
            return
        config, ok = QInputDialog.getItem(
            self,
            "Eliminar Configuración",
            "Seleccione una configuración para eliminar:",
            configs,
            0,
            False
        )
        if ok and config:
            confirm = QMessageBox.question(
                self,
                "Confirmar",
                f"¿Está seguro de que desea eliminar la configuración '{config}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                if self.shortcut_manager.delete_configuration(config):
                    QMessageBox.information(
                        self,
                        "Éxito",
                        f"Configuración '{config}' eliminada exitosamente."
                    )
                    self.create_shortcuts_menu(menuBar=self.menuBar())  # Actualizar el menú
                    logger.debug(f"Configuración '{config}' eliminada y menú actualizado.")

    def open_video(self):
        videoPath, _ = QFileDialog.getOpenFileName(
            self, "Abrir Video", "", "Video Files (*.mp4 *.avi *.mkv)"
        )
        if videoPath:
            self.videoPlayerWidget.load_video(videoPath)
            logger.debug(f"Video cargado desde: {videoPath}")

    def detach_video(self, video_widget):
        logger.debug("Intentando detachar el VideoPlayerWidget.")
        if self.videoWindow is not None:
            logger.debug("VideoWindow ya está abierto.")
            return

        try:
            detached_widget = self.splitter.widget(0)
            if detached_widget:
                detached_widget.setParent(None)
                self.videoWindow = VideoWindow(detached_widget)
                self.videoWindow.close_detached.connect(self.attach_video)
                self.videoWindow.show()
                logger.debug("VideoWindow creado y mostrado.")

                # Ajustar el splitter para solo mostrar el TableWindow
                self.splitter.setSizes([0, 100])
        except Exception as e:
            logger.error(f"Error al detachar el video: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Error al detachar el video: {str(e)}"
            )

    def attach_video(self):
        logger.debug("Intentando adjuntar el VideoPlayerWidget de nuevo.")
        if self.videoWindow is None:
            logger.debug("VideoWindow no está abierto.")
            return

        try:
            video_widget = self.videoWindow.video_widget
            self.splitter.insertWidget(0, video_widget)
            self.videoWindow = None
            logger.debug("VideoPlayerWidget insertado de nuevo en el splitter.")

            # Ajustar el splitter para mostrar ambos widgets de manera equilibrada
            self.splitter.setSizes([50, 50])
        except Exception as e:
            logger.error(f"Error al adjuntar el video: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Error al adjuntar el video: {str(e)}"
            )

    def handle_set_position(self, action, position_ms):
        try:
            logger.debug(
                f"handle_set_position called with action={action}, "
                f"position_ms={position_ms}"
            )
            # Aplicar el trim al establecer la posición
            adjusted_position = max(position_ms - self.trim_value, 0)
            logger.debug(
                f"Adjusted position after trim: {adjusted_position} ms"
            )
            self.videoPlayerWidget.set_position_public(adjusted_position)
            logger.debug(
                f"Posición del video establecida a {adjusted_position} ms "
                f"(Trim aplicado: {self.trim_value} ms) por acción {action}"
            )
        except Exception as e:
            logger.error(f"Error al establecer la posición del video: {e}")
            QMessageBox.warning(
                self,
                "Error",
                f"Error al establecer la posición del video: {str(e)}"
            )

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Permitir que Ctrl+C termine la aplicación
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.error(f"Excepción no manejada: {error_message}")
    QMessageBox.critical(None, "Error Inesperado", "Ocurrió un error inesperado. Consulte los logs para más detalles.")


def main():
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

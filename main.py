# main.py

import sys
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

        # Crear la barra de menú sin el menú de shortcuts
        self.create_menu_bar(exclude_shortcuts=True)

        # Inicializar ShortcutManager después de crear la barra de menú
        self.shortcut_manager = ShortcutManager(self)

        # Crear el menú de shortcuts después de inicializar ShortcutManager
        self.create_shortcuts_menu(self.menuBar())

        # Conectar señales
        self.videoPlayerWidget.detach_requested.connect(self.detach_video)
        self.tableWindow.in_out_signal.connect(self.handle_set_position)

        # Variable para la ventana independiente
        self.videoWindow = None

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
            self.actions[name] = action

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
            self.actions[name] = action

    def create_config_menu(self, menuBar):
        configMenu = menuBar.addMenu("&Configuración")

        openConfigAction = self.create_action("&Configuración", self.open_config_dialog)
        configMenu.addAction(openConfigAction)
        self.actions["&Configuración"] = openConfigAction

    def create_shortcuts_menu(self, menuBar):
        shortcutsMenu = menuBar.addMenu("&Shortcuts")

        # Submenú para configurar shortcuts
        configure_shortcuts_action = self.create_action("&Configurar Shortcuts", self.open_shortcut_config_dialog)
        shortcutsMenu.addAction(configure_shortcuts_action)
        self.actions["&Configurar Shortcuts"] = configure_shortcuts_action

        # Submenú para cargar configuraciones existentes
        load_config_menu = shortcutsMenu.addMenu("Cargar Configuración")
        for config_name in self.shortcut_manager.get_available_configs():
            action = self.create_action(
                config_name,
                lambda checked, name=config_name: self.shortcut_manager.apply_shortcuts(name)
            )
            load_config_menu.addAction(action)
            self.actions[config_name] = action

        # Opción para eliminar configuraciones
        delete_config_action = self.create_action("Eliminar Configuración", self.delete_configuration)
        shortcutsMenu.addAction(delete_config_action)
        self.actions["Eliminar Configuración"] = delete_config_action

    def create_action(self, name, slot, shortcut=None):
        action = QAction(name, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        return action

    def open_config_dialog(self):
        config_dialog = ConfigDialog(
            current_trim=self.trim_value,
            current_font_size=self.font_size
        )
        if config_dialog.exec_() == QDialog.Accepted:
            self.trim_value, self.font_size = config_dialog.get_values()
            self.apply_font_size()

    def apply_font_size(self):
        # Ajustar el tamaño de la fuente en la tabla del guion
        font = self.tableWindow.tableWidget.font()
        font.setPointSize(self.font_size)
        self.tableWindow.tableWidget.setFont(font)

        # Ajustar la fuente de los encabezados
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
        self.shortcut_manager.apply_shortcuts(self.shortcut_manager.current_config)

    def delete_configuration(self):
        configs = self.shortcut_manager.get_available_configs()
        if "default" in configs:
            configs.remove("default")
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
                    self.create_shortcuts_menu(menuBar=self.menuBar())

    def open_video(self):
        videoPath, _ = QFileDialog.getOpenFileName(
            self, "Abrir Video", "", "Video Files (*.mp4 *.avi *.mkv)"
        )
        if videoPath:
            self.videoPlayerWidget.load_video(videoPath)

    def detach_video(self, video_widget):
        if self.videoWindow is not None:
            return

        try:
            detached_widget = self.splitter.widget(0)
            if detached_widget:
                detached_widget.setParent(None)
                self.videoWindow = VideoWindow(detached_widget)
                self.videoWindow.close_detached.connect(self.attach_video)
                self.videoWindow.show()

                # Ajustar el splitter para solo mostrar el TableWindow
                self.splitter.setSizes([0, 100])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Error al detachar el video: {str(e)}"
            )

    def attach_video(self):
        if self.videoWindow is None:
            return

        try:
            video_widget = self.videoWindow.video_widget
            self.splitter.insertWidget(0, video_widget)
            self.videoWindow = None

            # Ajustar el splitter para mostrar ambos widgets de manera equilibrada
            self.splitter.setSizes([50, 50])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Error al adjuntar el video: {str(e)}"
            )

    def handle_set_position(self, action, position_ms):
        try:
            adjusted_position = max(position_ms - self.trim_value, 0)
            self.videoPlayerWidget.set_position_public(adjusted_position)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Error al establecer la posición del video: {str(e)}"
            )

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    QMessageBox.critical(None, "Error Inesperado", "Ocurrió un error inesperado. Consulte los logs para más detalles.")

def main():
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

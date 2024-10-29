# main.py

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QSplitter, QAction, QFileDialog, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence

from guion_editor.widgets.video_player_widget import VideoPlayerWidget
from guion_editor.widgets.table_window import TableWindow
from guion_editor.widgets.video_window import VideoWindow
from guion_editor.widgets.config_dialog import ConfigDialog  # Importar el ConfigDialog

import logging


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Guion con Video")
        self.setGeometry(100, 100, 1600, 900)  # Ajustar el tamaño de la ventana

        # Inicializar valores de configuración
        self.trim_value = 0  # Valor de TRIM en milisegundos
        self.font_size = 12  # Tamaño de fuente predeterminado

        # Crear el widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Crear un QSplitter para dividir la ventana en dos partes
        self.splitter = QSplitter(Qt.Horizontal)

        # Crear y agregar el reproductor de video
        self.videoPlayerWidget = VideoPlayerWidget()
        self.splitter.addWidget(self.videoPlayerWidget)

        # Crear y agregar la ventana de gestión del guion
        self.tableWindow = TableWindow(self.videoPlayerWidget)
        self.splitter.addWidget(self.tableWindow)

        # Agregar el splitter al layout principal
        layout.addWidget(self.splitter)

        # Crear la barra de menú
        self.create_menu_bar()

        # Conectar la señal de detach del VideoPlayerWidget
        self.videoPlayerWidget.detachRequested.connect(self.detach_video)

        # Variable para almacenar la ventana independiente
        self.videoWindow = None

        # Conectar la señal para establecer la posición del video
        self.tableWindow.inOutSignal.connect(self.handle_set_position)  # Conectar la señal correcta

        self.logger().debug("MainWindow inicializado correctamente.")

    def create_menu_bar(self):
        menuBar = self.menuBar()

        # Menú Archivo
        fileMenu = menuBar.addMenu("&Archivo")

        # Acción Abrir Video
        openVideoAction = QAction("&Abrir Video", self)
        openVideoAction.triggered.connect(self.open_video)
        fileMenu.addAction(openVideoAction)

        # Acción Abrir Guion
        openGuionAction = QAction("&Abrir Guion", self)
        openGuionAction.triggered.connect(self.tableWindow.open_file_dialog)
        fileMenu.addAction(openGuionAction)

        # Acción Exportar a Excel (desde la tabla)
        exportExcelAction = QAction("&Exportar Guion a Excel", self)
        exportExcelAction.triggered.connect(self.tableWindow.export_to_excel)
        fileMenu.addAction(exportExcelAction)

        # Acción Importar desde Excel (a la tabla)
        importExcelAction = QAction("&Importar Guion desde Excel", self)
        importExcelAction.triggered.connect(self.tableWindow.import_from_excel)
        fileMenu.addAction(importExcelAction)

        # Acción Guardar como JSON (desde la tabla)
        saveJsonAction = QAction("&Guardar Guion como JSON", self)
        saveJsonAction.triggered.connect(self.tableWindow.save_to_json)
        fileMenu.addAction(saveJsonAction)

        # Acción Cargar desde JSON (a la tabla)
        loadJsonAction = QAction("&Cargar Guion desde JSON", self)
        loadJsonAction.triggered.connect(self.tableWindow.load_from_json)
        fileMenu.addAction(loadJsonAction)

        # Menú Editar
        editMenu = menuBar.addMenu("&Editar")

        # Acción Agregar Línea (a la tabla)
        addRowAction = QAction("&Agregar Línea", self)
        addRowAction.triggered.connect(self.tableWindow.add_new_row)
        addRowAction.setShortcut(QKeySequence("Ctrl+N"))
        editMenu.addAction(addRowAction)

        # Acción Eliminar Fila (de la tabla)
        deleteRowAction = QAction("&Eliminar Fila", self)
        deleteRowAction.triggered.connect(self.tableWindow.remove_row)
        deleteRowAction.setShortcut(QKeySequence("Ctrl+Del"))
        editMenu.addAction(deleteRowAction)

        # Acción Mover Arriba (de la tabla)
        moveUpAction = QAction("Mover &Arriba", self)
        moveUpAction.triggered.connect(self.tableWindow.move_row_up)
        moveUpAction.setShortcut(QKeySequence("Alt+Up"))
        editMenu.addAction(moveUpAction)

        # Acción Mover Abajo (de la tabla)
        moveDownAction = QAction("Mover &Abajo", self)
        moveDownAction.triggered.connect(self.tableWindow.move_row_down)
        moveDownAction.setShortcut(QKeySequence("Alt+Down"))
        editMenu.addAction(moveDownAction)

        # Acción Ajustar Diálogos (de la tabla)
        adjustDialogsAction = QAction("&Ajustar Diálogos", self)
        adjustDialogsAction.triggered.connect(self.tableWindow.adjust_dialogs)
        editMenu.addAction(adjustDialogsAction)

        # Acción Separar Intervención (de la tabla)
        splitInterventionAction = QAction("&Separar Intervención", self)
        splitInterventionAction.triggered.connect(self.tableWindow.split_intervention)
        splitInterventionAction.setShortcut(QKeySequence("Alt+I"))
        editMenu.addAction(splitInterventionAction)

        # Acción Juntar Intervenciones (de la tabla)
        mergeInterventionAction = QAction("&Juntar Intervenciones", self)
        mergeInterventionAction.triggered.connect(self.tableWindow.merge_interventions)
        mergeInterventionAction.setShortcut(QKeySequence("Alt+J"))
        editMenu.addAction(mergeInterventionAction)

        # Menú Configuración
        configMenu = menuBar.addMenu("&Configuración")

        # Acción Abrir Configuración
        openConfigAction = QAction("&Configuración", self)
        openConfigAction.triggered.connect(self.open_config_dialog)
        configMenu.addAction(openConfigAction)

    def open_config_dialog(self):
        config_dialog = ConfigDialog(current_trim=self.trim_value, current_font_size=self.font_size)
        if config_dialog.exec_() == QDialog.Accepted:
            self.trim_value, self.font_size = config_dialog.get_values()
            self.logger().debug(f"Configuración actualizada: Trim={self.trim_value} ms, Tamaño de Fuente={self.font_size} pt")
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

    def open_video(self):
        videoPath, _ = QFileDialog.getOpenFileName(self, "Abrir Video", "", "Video Files (*.mp4 *.avi)")
        if videoPath:
            self.videoPlayerWidget.load_video(videoPath)

    def detach_video(self, video_widget):
        self.logger().debug("Intentando detachar el VideoPlayerWidget.")
        if self.videoWindow is None:
            try:
                # Remover el widget manualmente (ya que takeWidget no funciona)
                detached_widget = self.splitter.widget(0)
                if detached_widget:
                    detached_widget.setParent(None)
                    self.videoWindow = VideoWindow(detached_widget)
                    self.videoWindow.closeDetached.connect(self.attach_video)
                    self.videoWindow.show()
                    self.logger().debug("VideoWindow creado y mostrado.")

                    # Ajustar el splitter para solo mostrar el TableWindow
                    self.splitter.setSizes([0, 100])
            except Exception as e:
                self.logger().error(f"Error al detachar el video: {e}")
                QMessageBox.warning(self, "Error", f"Error al detachar el video: {str(e)}")
        else:
            self.logger().debug("VideoWindow ya está abierto.")

    def attach_video(self):
        self.logger().debug("Intentando adjuntar el VideoPlayerWidget de nuevo.")
        if self.videoWindow is not None:
            try:
                video_widget = self.videoWindow.video_widget
                self.splitter.insertWidget(0, video_widget)
                self.videoWindow = None
                self.logger().debug("VideoPlayerWidget insertado de nuevo en el splitter.")

                # Ajustar el splitter para mostrar ambos widgets de manera equilibrada
                self.splitter.setSizes([50, 50])
            except Exception as e:
                self.logger().error(f"Error al adjuntar el video: {e}")
                QMessageBox.warning(self, "Error", f"Error al adjuntar el video: {str(e)}")

    def handle_set_position(self, action, position_ms):
        try:
            self.logger().debug(f"handle_set_position called with action={action}, position_ms={position_ms}")
            # Aplicar el trim al establecer la posición
            adjusted_position = max(position_ms - self.trim_value, 0)
            self.logger().debug(f"Adjusted position after trim: {adjusted_position} ms")
            self.videoPlayerWidget.set_position_public(adjusted_position)
            self.logger().debug(f"Posición del video establecida a {adjusted_position} ms (Trim aplicado: {self.trim_value} ms) por acción {action}")
        except Exception as e:
            self.logger().error(f"Error al establecer la posición del video: {e}")
            QMessageBox.warning(self, "Error", f"Error al establecer la posición del video: {str(e)}")

    def logger(self):
        return logging.getLogger(__name__)


def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

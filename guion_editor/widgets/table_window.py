# guion_editor/widgets/table_window.py

import json
import os
from PyQt5.QtCore import pyqtSignal, QObject, QEvent, Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QWidget, QTableWidgetItem, QTextEdit, QFileDialog, QAbstractItemView,
    QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton, QShortcut, QCompleter,
    QUndoStack, QUndoCommand
)
import pandas as pd

from guion_editor.delegates.custom_delegates import TimeCodeDelegate, CharacterDelegate
from guion_editor.utils.dialog_utils import leer_guion, ajustar_dialogo
from guion_editor.widgets.custom_table_widget import CustomTableWidget


class TableWindow(QWidget):
    in_out_signal = pyqtSignal(str, int)
    character_name_changed = pyqtSignal()

    # Definir constantes para los índices de las columnas
    COL_ID = 0
    COL_SCENE = 1
    COL_IN = 2
    COL_OUT = 3
    COL_CHARACTER = 4
    COL_DIALOGUE = 5

    # Mapeo de columnas de la tabla a columnas del DataFrame
    TABLE_TO_DF_COL_MAP = {
        COL_ID: 'ID',
        COL_SCENE: 'SCENE',
        COL_IN: 'IN',
        COL_OUT: 'OUT',
        COL_CHARACTER: 'PERSONAJE',
        COL_DIALOGUE: 'DIÁLOGO'
    }

    class KeyPressFilter(QObject):
        def __init__(self, table_window):
            super().__init__()
            self.table_window = table_window

        def eventFilter(self, obj, event):
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_F6 and not event.isAutoRepeat():
                    self.table_window.video_player_widget.start_out_timer()
                    return True
            elif event.type() == QEvent.KeyRelease:
                if event.key() == Qt.Key_F6 and not event.isAutoRepeat():
                    self.table_window.video_player_widget.stop_out_timer()
                    return True
            return False

    def __init__(self, video_player_widget, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Editor de Guion")
        self.setGeometry(100, 100, 800, 600)
        self.video_player_widget = video_player_widget
        self.video_player_widget.in_out_signal.connect(self.update_in_out)
        self.video_player_widget.out_released.connect(self.select_next_row_and_set_in)
        self.key_filter = self.KeyPressFilter(self)
        self.installEventFilter(self.key_filter)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.dataframe = pd.DataFrame(columns=self.TABLE_TO_DF_COL_MAP.values())  # Inicializar con columnas
        self.unsaved_changes = False  # Bandera para cambios sin guardar
        self.undo_stack = QUndoStack(self)  # Pila para deshacer/rehacer
        self.has_scene_numbers = False  # Bandera para verificar si hay números de escena en los datos importados
        self.setup_ui()

        # Atajos para deshacer y rehacer
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)

        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)

        # Atajo para copiar IN/OUT a la siguiente intervención
        copy_in_out_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        copy_in_out_shortcut.activated.connect(self.copy_in_out_to_next)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.setup_buttons(layout)
        self.setup_table_widget(layout)
        self.load_stylesheet()

    def setup_buttons(self, layout):
        buttons_layout = QHBoxLayout()
        buttons = [
            ("Agregar Línea", self.add_new_row),
            ("Eliminar Fila", self.remove_row),
            ("Mover Arriba", self.move_row_up),
            ("Mover Abajo", self.move_row_down),
            ("Ajustar Diálogos", self.adjust_dialogs),
            ("Separar Intervención", self.split_intervention),
            ("Juntar Intervenciones", self.merge_interventions)
        ]
        for text, method in buttons:
            button = QPushButton(text)
            button.clicked.connect(method)
            buttons_layout.addWidget(button)
        layout.addLayout(buttons_layout)

    def setup_table_widget(self, layout):
        self.table_widget = CustomTableWidget()
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)  # Permitir selección única
        self.table_widget.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        layout.addWidget(self.table_widget)

        # Definir las columnas: "ID", "SCENE", "IN", "OUT", "PERSONAJE", "DIÁLOGO"
        self.columns = ["ID", "SCENE", "IN", "OUT", "PERSONAJE", "DIÁLOGO"]
        self.table_widget.setColumnCount(len(self.columns))
        self.table_widget.setHorizontalHeaderLabels(self.columns)
        # Ocultar la columna ID
        self.table_widget.setColumnHidden(self.columns.index("ID"), True)

        # Configurar los delegados para las columnas existentes
        self.table_widget.setItemDelegateForColumn(self.COL_IN, TimeCodeDelegate(self.table_widget))
        self.table_widget.setItemDelegateForColumn(self.COL_OUT, TimeCodeDelegate(self.table_widget))
        self.table_widget.setItemDelegateForColumn(self.COL_CHARACTER, CharacterDelegate(get_names_callback=self.get_character_names, parent=self.table_widget))
        # "DIÁLOGO" debería usar un delegado diferente, como QPlainTextEdit, pero aquí se usa QTextEdit directamente

        # Configurar la selección de filas completas
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.table_widget.cellCtrlClicked.connect(self.handle_ctrl_click)
        self.table_widget.cellAltClicked.connect(self.handle_alt_click)
        self.table_widget.itemChanged.connect(self.on_item_changed)

    def load_stylesheet(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            css_path = os.path.join(current_dir, '..', 'styles', 'table_styles.css')
            with open(css_path, 'r') as f:
                self.table_widget.setStyleSheet(f.read())
        except Exception as e:
            QMessageBox.warning(self, "Error de Estilos", f"Error al cargar el stylesheet: {str(e)}")

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Abrir guion", "", "Documentos de Word (*.docx)"
        )
        if file_name:
            self.load_data(file_name)
            # Agregar a archivos recientes
            if self.main_window:
                self.main_window.add_to_recent_files(file_name)

    def load_data(self, file_name):
        try:
            guion_data = leer_guion(file_name)
            # Verificar si 'SCENE' está presente en los datos importados
            if 'SCENE' not in guion_data[0]:
                self.has_scene_numbers = False
                for entry in guion_data:
                    entry['SCENE'] = '1'  # Asignar '1' a todas las escenas si no están presentes
                print("Importación sin números de escena. Asignando '1' a todas las escenas.")
            else:
                # Verificar si 'SCENE' tiene múltiples valores
                scene_values = [entry['SCENE'] for entry in guion_data]
                unique_scenes = set(scene_values)
                if len(unique_scenes) > 1 or (len(unique_scenes) == 1 and unique_scenes.pop() != '1'):
                    self.has_scene_numbers = True
                    print("Importación con números de escena. Preservando escenas existentes.")
                else:
                    self.has_scene_numbers = False
                    for entry in guion_data:
                        entry['SCENE'] = '1'  # Asignar '1' a todas las escenas si todos son '1'
                    print("Importación sin números de escena (todos '1'). Asignando '1' a todas las escenas.")
            self.dataframe = pd.DataFrame(guion_data)
            required_columns = [col for col in self.TABLE_TO_DF_COL_MAP.values() if col != 'ID']

            if not all(col in self.dataframe.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
            # Asignar IDs únicos
            self.dataframe.insert(0, 'ID', range(len(self.dataframe)))
            self.populate_table()
            self.unsaved_changes = False  # Datos cargados, no hay cambios sin guardar
        except Exception as e:
            self.handle_exception(e, "Error al cargar los datos")

    def populate_table(self):
        try:
            if self.dataframe.empty:
                QMessageBox.information(self, "Información", "El archivo está vacío.")
                return

            self.table_widget.blockSignals(True)  # Bloquear señales para evitar disparar itemChanged
            self.table_widget.clear()
            self.table_widget.setRowCount(self.dataframe.shape[0])
            self.table_widget.setColumnCount(len(self.columns))
            self.table_widget.setHorizontalHeaderLabels(self.columns)
            # Ocultar la columna ID
            self.table_widget.setColumnHidden(self.columns.index("ID"), True)

            for i in range(self.dataframe.shape[0]):
                # Asignar los valores de cada columna
                for col_index, col_name in enumerate(self.columns):
                    if col_name == "DIÁLOGO":
                        dialogo_text = str(self.dataframe.at[i, col_name])
                        dialogo_item = self.create_text_edit(dialogo_text, i, self.COL_DIALOGUE)
                        self.table_widget.setCellWidget(i, self.COL_DIALOGUE, dialogo_item)
                    else:
                        text = str(self.dataframe.at[i, col_name])
                        item = self.create_table_item(text, col_index)
                        self.table_widget.setItem(i, col_index, item)

                self.adjust_row_height(i)

            self.table_widget.resizeColumnsToContents()
            self.table_widget.horizontalHeader().setStretchLastSection(True)
            self.table_widget.blockSignals(False)  # Desbloquear señales
        except Exception as e:
            self.handle_exception(e, "Error al llenar la tabla")

    def create_text_edit(self, text, row, column):
        text_edit = QTextEdit(text)
        text_edit.setStyleSheet("font-size: 16px;")
        text_edit.setFont(QFont("Arial", 12))
        text_edit.textChanged.connect(self.generate_text_changed_callback(row, column))
        return text_edit

    def create_table_item(self, text, column):
        item = QTableWidgetItem(text)
        item.setFont(QFont("Arial", 12))
        return item

    def generate_text_changed_callback(self, row, column):
        def callback():
            self.on_text_changed(row, column)
        return callback

    def adjust_dialogs(self):
        try:
            for i in range(self.dataframe.shape[0]):
                text_widget = self.table_widget.cellWidget(i, self.COL_DIALOGUE)
                if text_widget:
                    dialogo_actual = text_widget.toPlainText()
                    dialogo_ajustado = ajustar_dialogo(dialogo_actual)
                    text_widget.blockSignals(True)
                    text_widget.setText(dialogo_ajustado)
                    text_widget.blockSignals(False)
                    old_text = self.dataframe.at[i, 'DIÁLOGO']
                    if dialogo_actual != dialogo_ajustado:
                        command = EditCommand(self, i, self.COL_DIALOGUE, old_text, dialogo_ajustado)
                        self.undo_stack.push(command)
                        self.unsaved_changes = True
                    self.adjust_row_height(i)
            QMessageBox.information(self, "Éxito", "Diálogos ajustados correctamente.")
        except Exception as e:
            self.handle_exception(e, "Error al ajustar diálogos")

    def adjust_all_row_heights(self):
        for row in range(self.table_widget.rowCount()):
            self.adjust_row_height(row)

    def adjust_row_height(self, row):
        try:
            text_widget = self.table_widget.cellWidget(row, self.COL_DIALOGUE)
            if text_widget:
                document = text_widget.document()
                text_height = document.size().height()
                margins = text_widget.contentsMargins()
                total_height = text_height + margins.top() + margins.bottom() + 10
                self.table_widget.setRowHeight(row, int(total_height))
        except Exception as e:
            self.handle_exception(e, f"Error al ajustar la altura de la fila {row}")

    def on_text_changed(self, row, column):
        try:
            df_col = self.get_dataframe_column_name(column)
            if not df_col:
                return

            text_widget = self.table_widget.cellWidget(row, column)
            new_text = text_widget.toPlainText()
            old_text = self.dataframe.at[row, df_col]
            if new_text != old_text:
                command = EditCommand(self, row, column, old_text, new_text)
                self.undo_stack.push(command)
                self.unsaved_changes = True
        except Exception as e:
            self.handle_exception(e, "Error al actualizar texto en la tabla")

    def on_item_changed(self, item):
        try:
            row = item.row()
            column = item.column()
            df_col = self.get_dataframe_column_name(column)
            if not df_col:
                return

            new_text = item.text()
            old_text = self.dataframe.at[row, df_col]
            if new_text != old_text:
                command = EditCommand(self, row, column, old_text, new_text)
                self.undo_stack.push(command)
                self.unsaved_changes = True
                if column == self.COL_SCENE:
                    self.has_scene_numbers = True  # Actualizar bandera
                    print("El usuario ha editado los números de escena. has_scene_numbers = True")
        except Exception as e:
            self.handle_exception(e, "Error al actualizar celda en la tabla")

    def add_new_row(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                selected_row = self.table_widget.rowCount()
            else:
                selected_row += 1

            # Crear comando para agregar fila
            command = AddRowCommand(self, selected_row)
            self.undo_stack.push(command)
            self.unsaved_changes = True
        except Exception as e:
            self.handle_exception(e, "Error al agregar una nueva fila")

    def remove_row(self):
        try:
            selected_rows = self.table_widget.selectionModel().selectedRows()
            if selected_rows:
                rows = sorted([index.row() for index in selected_rows], reverse=False)
                confirm = QMessageBox.question(
                    self, "Confirmar Eliminación",
                    f"¿Estás seguro de que deseas eliminar las filas seleccionadas?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm == QMessageBox.Yes:
                    command = RemoveRowsCommand(self, rows)
                    self.undo_stack.push(command)
                    self.unsaved_changes = True
            else:
                QMessageBox.warning(self, "Eliminar Filas", "Por favor, selecciona al menos una fila para eliminar.")
        except Exception as e:
            self.handle_exception(e, "Error al eliminar las filas")

    def move_row_up(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row > 0:
                command = MoveRowCommand(self, selected_row, selected_row - 1)
                self.undo_stack.push(command)
                self.table_widget.selectRow(selected_row - 1)
                self.unsaved_changes = True
        except Exception as e:
            self.handle_exception(e, "Error al mover la fila hacia arriba")

    def move_row_down(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row < self.table_widget.rowCount() - 1:
                command = MoveRowCommand(self, selected_row, selected_row + 1)
                self.undo_stack.push(command)
                self.table_widget.selectRow(selected_row + 1)
                self.unsaved_changes = True
        except Exception as e:
            self.handle_exception(e, "Error al mover la fila hacia abajo")

    def handle_ctrl_click(self, row):
        try:
            in_time_code = self.dataframe.at[row, 'IN']
            milliseconds = self.convert_time_code_to_milliseconds(in_time_code)
            self.in_out_signal.emit("IN", milliseconds)
        except Exception as e:
            self.handle_exception(e, "Error al desplazar el video")

    def handle_alt_click(self, row):
        try:
            out_time_code = self.dataframe.at[row, 'OUT']
            milliseconds = self.convert_time_code_to_milliseconds(out_time_code)
            self.in_out_signal.emit("OUT", milliseconds)
        except Exception as e:
            self.handle_exception(e, "Error al desplazar el video")

    def convert_time_code_to_milliseconds(self, time_code):
        try:
            parts = time_code.split(':')
            if len(parts) != 4:
                raise ValueError("Formato de time code inválido.")
            hours, minutes, seconds, frames = map(int, parts)
            milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000 + int((frames / 25) * 1000)
            return milliseconds
        except Exception as e:
            self.handle_exception(e, "Error al convertir time code a milisegundos")
            raise

    def convert_milliseconds_to_time_code(self, ms):
        try:
            total_seconds = ms // 1000
            frames = int((ms % 1000) / (1000 / 25))
            seconds = total_seconds % 60
            minutes = (total_seconds // 60) % 60
            hours = total_seconds // 3600
            return f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}"
        except Exception as e:
            return "00:00:00:00"

    def export_to_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", "", "Archivos Excel (*.xlsx)")
            if path:
                self.save_to_excel(path)
                QMessageBox.information(self, "Éxito", "Datos exportados correctamente a Excel.")
                self.unsaved_changes = False  # Cambios guardados
            else:
                # El usuario canceló la exportación
                QMessageBox.information(self, "Exportación cancelada", "La exportación ha sido cancelada.")
        except Exception as e:
            self.handle_exception(e, "Error al exportar a Excel")

    def save_to_excel(self, path):
        try:
            # Actualizar el DataFrame con los diálogos actuales
            for row in range(self.table_widget.rowCount()):
                dialog_widget = self.table_widget.cellWidget(row, self.COL_DIALOGUE)
                if dialog_widget:
                    self.dataframe.at[row, 'DIÁLOGO'] = dialog_widget.toPlainText()
            # No incluir la columna 'ID' en la exportación
            df_to_export = self.dataframe.drop(columns=['ID'])
            df_to_export.to_excel(path, index=False)
        except Exception as e:
            self.handle_exception(e, "Error al guardar en Excel")
            raise e


    def import_from_excel(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Excel", "", "Archivos Excel (*.xlsx)")
            if path:
                self.load_from_excel(path)
            else:
                # El usuario canceló la carga
                QMessageBox.information(self, "Carga cancelada", "La carga del archivo Excel ha sido cancelada.")
        except Exception as e:
            self.handle_exception(e, "Error al importar desde Excel")

    def split_intervention(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Separar Intervención", "Por favor, selecciona una fila para separar.")
                return

            dialog_widget = self.table_widget.cellWidget(selected_row, self.COL_DIALOGUE)
            if not dialog_widget:
                QMessageBox.warning(self, "Separar Intervención", "No hay diálogo para separar.")
                return

            cursor = dialog_widget.textCursor()
            if cursor.hasSelection():
                position = cursor.selectionEnd()
            else:
                position = cursor.position()

            text = dialog_widget.toPlainText()
            if position >= len(text):
                QMessageBox.warning(self, "Separar Intervención", "No hay texto para separar después de la posición seleccionada.")
                return

            before = text[:position]
            after = text[position:]

            # Crear comando para separar intervención
            command = SplitInterventionCommand(self, selected_row, before, after)
            self.undo_stack.push(command)
            self.unsaved_changes = True
        except Exception as e:
            self.handle_exception(e, "Error al separar intervención")

    def update_in_out(self, action, position_ms):
        try:
            if not action or position_ms is None:
                return

            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Error", "No hay fila seleccionada para actualizar IN/OUT.")
                return

            time_code = self.convert_milliseconds_to_time_code(position_ms)
            if action.upper() == "IN":
                old_value = self.dataframe.at[selected_row, 'IN']
                if time_code != old_value:
                    command = EditCommand(self, selected_row, self.COL_IN, old_value, time_code)
                    self.undo_stack.push(command)
                    self.unsaved_changes = True
            elif action.upper() == "OUT":
                old_value = self.dataframe.at[selected_row, 'OUT']
                if time_code != old_value:
                    command = EditCommand(self, selected_row, self.COL_OUT, old_value, time_code)
                    self.undo_stack.push(command)
                    self.unsaved_changes = True
        except Exception as e:
            self.handle_exception(e, "Error en update_in_out")

    def select_next_row_and_set_in(self):
        try:
            current_row = self.table_widget.currentRow()
            if current_row == -1:
                return

            current_out_time = self.dataframe.at[current_row, 'OUT']
            current_out_ms = self.convert_time_code_to_milliseconds(current_out_time)

            next_row = current_row + 1
            if next_row < self.table_widget.rowCount():
                self.table_widget.selectRow(next_row)
                time_code = self.convert_milliseconds_to_time_code(current_out_ms)
                old_in = self.dataframe.at[next_row, 'IN']
                if time_code != old_in:
                    command = EditCommand(self, next_row, self.COL_IN, old_in, time_code)
                    self.undo_stack.push(command)
                    self.unsaved_changes = True
                self.adjust_row_height(next_row)
                self.table_widget.scrollToItem(self.table_widget.item(next_row, self.COL_SCENE), QAbstractItemView.PositionAtCenter)
        except Exception as e:
            self.handle_exception(e, "Error al seleccionar la siguiente fila")

    def load_from_excel(self, path=None):
        try:
            if not path:
                path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Excel", "", "Archivos Excel (*.xlsx)")
            if path:
                df = pd.read_excel(path)
                # Asignar IDs si no existen
                if 'ID' not in df.columns:
                    df.insert(0, 'ID', range(len(df)))
                required_columns = [col for col in self.TABLE_TO_DF_COL_MAP.values() if col != 'ID']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
                # Verificar si 'SCENE' está presente
                if 'SCENE' not in df.columns:
                    self.has_scene_numbers = False
                    df['SCENE'] = '1'  # Asignar '1' a todas las escenas si no están presentes
                    print("Importación desde Excel sin números de escena. Asignando '1' a todas las escenas.")
                else:
                    # Verificar si 'SCENE' tiene múltiples valores
                    scene_values = df['SCENE'].astype(str).tolist()
                    unique_scenes = set(scene_values)
                    if len(unique_scenes) > 1 or (len(unique_scenes) == 1 and unique_scenes.pop() != '1'):
                        self.has_scene_numbers = True
                        print("Importación desde Excel con números de escena. Preservando escenas existentes.")
                    else:
                        self.has_scene_numbers = False
                        df['SCENE'] = '1'  # Asignar '1' a todas las escenas si todos son '1'
                        print("Importación desde Excel sin números de escena (todos '1'). Asignando '1' a todas las escenas.")
                self.dataframe = df
                self.populate_table()
                QMessageBox.information(self, "Éxito", "Datos importados correctamente desde Excel.")
                self.unsaved_changes = False  # Datos cargados, no hay cambios sin guardar
                # Agregar a archivos recientes
                if self.main_window:
                    self.main_window.add_to_recent_files(path)
            else:
                # El usuario canceló la carga
                QMessageBox.information(self, "Carga cancelada", "La carga del archivo Excel ha sido cancelada.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde Excel")

    def merge_interventions(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Juntar Intervenciones", "Por favor, selecciona una fila para juntar.")
                return

            if selected_row >= self.table_widget.rowCount() - 1:
                QMessageBox.warning(self, "Juntar Intervenciones", "No hay una segunda fila para juntar.")
                return

            personaje_current = self.dataframe.at[selected_row, 'PERSONAJE']
            personaje_next = self.dataframe.at[selected_row + 1, 'PERSONAJE']

            if personaje_current != personaje_next:
                QMessageBox.warning(self, "Juntar Intervenciones", "Las filas seleccionadas no tienen el mismo personaje.")
                return

            dialog_current_widget = self.table_widget.cellWidget(selected_row, self.COL_DIALOGUE)
            dialog_next_widget = self.table_widget.cellWidget(selected_row + 1, self.COL_DIALOGUE)
            if not dialog_current_widget or not dialog_next_widget:
                QMessageBox.warning(self, "Juntar Intervenciones", "No hay diálogos para juntar.")
                return

            dialog_current = dialog_current_widget.toPlainText().strip()
            dialog_next = dialog_next_widget.toPlainText().strip()

            if not dialog_current and not dialog_next:
                QMessageBox.warning(self, "Juntar Intervenciones", "Ambos diálogos están vacíos.")
                return

            merged_dialog = f"{dialog_current} {dialog_next}".strip()

            # Crear comando para juntar intervenciones
            command = MergeInterventionsCommand(self, selected_row, merged_dialog)
            self.undo_stack.push(command)
            self.unsaved_changes = True

            QMessageBox.information(self, "Juntar Intervenciones", "Las intervenciones han sido juntadas exitosamente.")
        except Exception as e:
            self.handle_exception(e, "Error al juntar intervenciones")

    def save_to_json(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                self.save_to_json_file(path)
                QMessageBox.information(self, "Éxito", "Datos guardados correctamente en JSON.")
                self.unsaved_changes = False  # Cambios guardados
            else:
                # El usuario canceló la exportación
                QMessageBox.information(self, "Exportación cancelada", "La exportación ha sido cancelada.")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en JSON")

    def save_to_json_file(self, path):
        try:
            # Actualizar el DataFrame con los diálogos actuales
            for row in range(self.table_widget.rowCount()):
                dialog_widget = self.table_widget.cellWidget(row, self.COL_DIALOGUE)
                if dialog_widget:
                    self.dataframe.at[row, 'DIÁLOGO'] = dialog_widget.toPlainText()
            # No incluir la columna 'ID' en la exportación
            data = self.dataframe.drop(columns=['ID']).to_dict(orient='records')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.handle_exception(e, "Error al guardar en JSON")
            raise e


    def load_from_json(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                # Asignar IDs si no existen
                if 'ID' not in df.columns:
                    df.insert(0, 'ID', range(len(df)))
                required_columns = [col for col in self.TABLE_TO_DF_COL_MAP.values() if col != 'ID']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
                # Verificar si 'SCENE' está presente
                if 'SCENE' not in df.columns:
                    self.has_scene_numbers = False
                    df['SCENE'] = '1'  # Asignar '1' a todas las escenas si no están presentes
                    print("Importación desde JSON sin números de escena. Asignando '1' a todas las escenas.")
                else:
                    # Verificar si 'SCENE' tiene múltiples valores
                    scene_values = df['SCENE'].astype(str).tolist()
                    unique_scenes = set(scene_values)
                    if len(unique_scenes) > 1 or (len(unique_scenes) == 1 and unique_scenes.pop() != '1'):
                        self.has_scene_numbers = True
                        print("Importación desde JSON con números de escena. Preservando escenas existentes.")
                    else:
                        self.has_scene_numbers = False
                        df['SCENE'] = '1'  # Asignar '1' a todas las escenas si todos son '1'
                        print("Importación desde JSON sin números de escena (todos '1'). Asignando '1' a todas las escenas.")
                self.dataframe = df
                self.populate_table()
                QMessageBox.information(self, "Éxito", "Datos cargados correctamente desde JSON.")
                self.unsaved_changes = False  # Datos cargados, no hay cambios sin guardar
            else:
                # El usuario canceló la carga
                QMessageBox.information(self, "Carga cancelada", "La carga del archivo JSON ha sido cancelada.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde JSON")

    def copy_in_out_to_next(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Copiar IN/OUT", "Por favor, selecciona una fila para copiar IN y OUT.")
                return

            if selected_row >= self.table_widget.rowCount() - 1:
                QMessageBox.warning(self, "Copiar IN/OUT", "No hay una fila siguiente para pegar los tiempos.")
                return

            # Obtener los tiempos IN y OUT de la fila seleccionada
            in_time = self.dataframe.at[selected_row, 'IN']
            out_time = self.dataframe.at[selected_row, 'OUT']

            # Crear comandos para copiar IN y OUT
            next_row = selected_row + 1

            # Copiar IN
            old_in = self.dataframe.at[next_row, 'IN']
            if in_time != old_in:
                command_in = EditCommand(self, next_row, self.COL_IN, old_in, in_time)
                self.undo_stack.push(command_in)
                self.unsaved_changes = True

            # Copiar OUT
            old_out = self.dataframe.at[next_row, 'OUT']
            if out_time != old_out:
                command_out = EditCommand(self, next_row, self.COL_OUT, old_out, out_time)
                self.undo_stack.push(command_out)
                self.unsaved_changes = True

            QMessageBox.information(self, "Copiar IN/OUT", "Tiempos IN y OUT copiados a la siguiente intervención.")
        except Exception as e:
            self.handle_exception(e, "Error al copiar IN/OUT a la siguiente intervención")

    def get_character_names(self):
        return sorted(set(self.dataframe['PERSONAJE'].tolist()))

    def update_character_completer(self):
        # Actualizar el completer en el delegado
        self.table_widget.setItemDelegateForColumn(self.COL_CHARACTER, CharacterDelegate(get_names_callback=self.get_character_names, parent=self.table_widget))

    def update_character_name(self, old_name, new_name):
        # Actualizar nombres en el dataframe
        self.dataframe.loc[self.dataframe['PERSONAJE'] == old_name, 'PERSONAJE'] = new_name
        # Actualizar la tabla visualmente
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, self.COL_CHARACTER)
            if item and item.text() == old_name:
                item.setText(new_name)
        self.unsaved_changes = True
        self.update_character_completer()
        # Emitir señal de cambio de nombre
        self.character_name_changed.emit()

    def find_and_replace(self, find_text, replace_text, search_in_character=True, search_in_dialogue=True):
        try:
            for row in range(self.table_widget.rowCount()):
                # Reemplazar en diálogos si está seleccionado
                if search_in_dialogue:
                    dialog_widget = self.table_widget.cellWidget(row, self.COL_DIALOGUE)
                    if dialog_widget:
                        text = dialog_widget.toPlainText()
                        if find_text in text:
                            new_text = text.replace(find_text, replace_text)
                            command = EditCommand(self, row, self.COL_DIALOGUE, text, new_text)
                            self.undo_stack.push(command)
                            self.unsaved_changes = True

                # Reemplazar en personajes si está seleccionado
                if search_in_character:
                    character_item = self.table_widget.item(row, self.COL_CHARACTER)
                    if character_item:
                        text = character_item.text()
                        if find_text in text:
                            new_text = text.replace(find_text, replace_text)
                            command = EditCommand(self, row, self.COL_CHARACTER, text, new_text)
                            self.undo_stack.push(command)
                            self.unsaved_changes = True
            QMessageBox.information(self, "Buscar y Reemplazar", "Reemplazo completado.")
        except Exception as e:
            self.handle_exception(e, "Error en buscar y reemplazar")


    def handle_exception(self, exception, message):
        QMessageBox.critical(self, "Error", f"{message}: {str(exception)}")

    def get_dataframe_column_name(self, table_col_index):
        """Mapea el índice de columna de la tabla al nombre de columna del DataFrame."""
        return self.TABLE_TO_DF_COL_MAP.get(table_col_index, None)

    def renumerar_escenas(self):
        """Asigna '1' a todas las escenas si los datos importados no contienen números de escena."""
        try:
            if not self.has_scene_numbers:
                print("Renumerando escenas: Asignando '1' a todas las escenas.")
                for row in range(self.table_widget.rowCount()):
                    self.dataframe.at[row, 'SCENE'] = '1'
                    # Actualizar la vista de la tabla
                    item = self.table_widget.item(row, self.COL_SCENE)
                    if item:
                        item.setText('1')
                self.unsaved_changes = True
            else:
                print("No se renumeran escenas porque los datos importados tienen números de escena.")
        except Exception as e:
            self.handle_exception(e, "Error al renumerar escenas")

    def get_next_id(self):
        if not self.dataframe.empty and 'ID' in self.dataframe.columns:
            return int(self.dataframe['ID'].max()) + 1
        else:
            return 0

    def find_dataframe_index_by_id(self, id_value):
        df_index = self.dataframe.index[self.dataframe['ID'] == id_value]
        if not df_index.empty:
            return df_index[0]
        else:
            return None

    def find_table_row_by_id(self, id_value):
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, self.COL_ID)
            if item and int(item.text()) == id_value:
                return row
        return None


# Clases de comandos para deshacer/rehacer
class EditCommand(QUndoCommand):
    def __init__(self, table_window, row, column, old_value, new_value):
        super().__init__()
        self.table_window = table_window
        self.row = row
        self.column = column
        self.old_value = old_value
        self.new_value = new_value
        column_name = table_window.columns[column]
        self.setText(f"Editar {column_name} en fila {row + 1}")

    def undo(self):
        self._apply_value(self.old_value)

    def redo(self):
        self._apply_value(self.new_value)

    def _apply_value(self, value):
        df_col_name = self.table_window.get_dataframe_column_name(self.column)
        if df_col_name is None:
            # La columna no está en el DataFrame
            return

        # Asignar el valor al DataFrame
        self.table_window.dataframe.at[self.row, df_col_name] = value

        # Actualizar la interfaz de usuario
        if self.column == self.table_window.COL_DIALOGUE:
            # Actualizar el QTextEdit en la celda
            text_widget = self.table_window.table_widget.cellWidget(self.row, self.column)
            if text_widget:
                text_widget.blockSignals(True)
                text_widget.setPlainText(str(value))
                text_widget.blockSignals(False)
            # Ajustar la altura de la fila si es necesario
            self.table_window.adjust_row_height(self.row)
        else:
            item = self.table_window.table_widget.item(self.row, self.column)
            if item:
                item.setText(str(value))

class AddRowCommand(QUndoCommand):
    def __init__(self, table_window, row):
        super().__init__()
        self.table_window = table_window
        self.row = row
        self.new_row_data = {
            'ID': self.table_window.get_next_id(),
            'SCENE': '1',  # Número de SCENE por defecto
            'IN': '00:00:00:00',
            'OUT': '00:00:00:00',
            'PERSONAJE': 'Personaje',
            'DIÁLOGO': 'Nuevo diálogo'
        }
        self.setText("Agregar fila")

    def undo(self):
        # Remove the row from the table and DataFrame
        self.table_window.table_widget.removeRow(self.row)
        df_row = self.table_window.find_dataframe_index_by_id(self.new_row_data['ID'])
        if df_row is not None:
            self.table_window.dataframe = self.table_window.dataframe.drop(df_row).reset_index(drop=True)

    def redo(self):
        # Insert row into the table
        self.table_window.table_widget.insertRow(self.row)
        for col_index, col_name in enumerate(self.table_window.columns):
            value = self.new_row_data.get(col_name, '')
            if col_name == "DIÁLOGO":
                dialogo_item = self.table_window.create_text_edit(value, self.row, self.table_window.COL_DIALOGUE)
                self.table_window.table_widget.setCellWidget(self.row, self.table_window.COL_DIALOGUE, dialogo_item)
            else:
                item = self.table_window.create_table_item(str(value), col_index)
                self.table_window.table_widget.setItem(self.row, col_index, item)
        self.table_window.adjust_row_height(self.row)

        # Insert data into the DataFrame
        df_new_row = pd.DataFrame([self.new_row_data])
        self.table_window.dataframe = pd.concat(
            [
                self.table_window.dataframe.iloc[:self.row],
                df_new_row,
                self.table_window.dataframe.iloc[self.row:]
            ],
            ignore_index=True
        )


class RemoveRowsCommand(QUndoCommand):
    def __init__(self, table_window, rows):
        super().__init__()
        self.table_window = table_window
        self.rows = sorted(rows)
        self.removed_data = self.table_window.dataframe.iloc[self.rows].copy()
        self.setText("Eliminar filas")

    def undo(self):
        for i, row in enumerate(self.rows):
            self.table_window.table_widget.insertRow(row)
            data_row = self.removed_data.iloc[i]

            # Asignar los valores de la fila
            for col_index, col_name in enumerate(self.table_window.columns):
                value = data_row[col_name]
                if col_name == "DIÁLOGO":
                    dialogo_text = str(value)
                    dialogo_item = self.table_window.create_text_edit(dialogo_text, row, self.table_window.COL_DIALOGUE)
                    self.table_window.table_widget.setCellWidget(row, self.table_window.COL_DIALOGUE, dialogo_item)
                else:
                    item = self.table_window.create_table_item(str(value), col_index)
                    self.table_window.table_widget.setItem(row, col_index, item)

            self.table_window.adjust_row_height(row)

            # Insertar datos en el DataFrame
            upper_df = self.table_window.dataframe.iloc[:row] if row > 0 else pd.DataFrame(columns=self.table_window.dataframe.columns)
            lower_df = self.table_window.dataframe.iloc[row:] if row < self.table_window.dataframe.shape[0] else pd.DataFrame(columns=self.table_window.dataframe.columns)
            new_df = pd.DataFrame([data_row.to_dict()])
            self.table_window.dataframe = pd.concat([upper_df, new_df, lower_df], ignore_index=True)

    def redo(self):
        for row in reversed(self.rows):
            self.table_window.table_widget.removeRow(row)
            df_row = self.table_window.find_dataframe_index_by_id(self.removed_data.at[row, 'ID'])
            if df_row is not None:
                self.table_window.dataframe = self.table_window.dataframe.drop(df_row).reset_index(drop=True)


class MoveRowCommand(QUndoCommand):
    def __init__(self, table_window, source_row, target_row):
        super().__init__()
        self.table_window = table_window
        self.source_row = source_row
        self.target_row = target_row
        self.setText("Mover fila")

    def undo(self):
        self._move_row(self.target_row, self.source_row)

    def redo(self):
        self._move_row(self.source_row, self.target_row)

    def _move_row(self, from_row, to_row):
        # Mover datos en el DataFrame
        df = self.table_window.dataframe
        row_data = df.iloc[from_row].copy()
        df = df.drop(from_row).reset_index(drop=True)
        df = pd.concat([df.iloc[:to_row], pd.DataFrame([row_data]), df.iloc[to_row:]]).reset_index(drop=True)
        self.table_window.dataframe = df

        # Mover visualmente en la tabla
        self.table_widget = self.table_window.table_widget
        self.table_widget.blockSignals(True)

        # Extraer datos antes de eliminar la fila
        row_data_items = {}
        for col in range(self.table_widget.columnCount()):
            if col == self.table_window.COL_DIALOGUE:
                widget = self.table_widget.cellWidget(from_row, col)
                if widget:
                    text = widget.toPlainText()
                    row_data_items[col] = text
            else:
                item = self.table_widget.item(from_row, col)
                if item:
                    text = item.text()
                    row_data_items[col] = text

        self.table_widget.removeRow(from_row)
        self.table_widget.insertRow(to_row)

        for col in range(self.table_widget.columnCount()):
            if col == self.table_window.COL_DIALOGUE:
                text = row_data_items.get(col, '')
                text_edit = self.table_window.create_text_edit(text, to_row, col)
                self.table_widget.setCellWidget(to_row, col, text_edit)
            else:
                text = row_data_items.get(col, '')
                item = self.table_window.create_table_item(text, col)
                self.table_window.table_widget.setItem(to_row, col, item)

        self.table_widget.blockSignals(False)
        self.table_window.adjust_row_height(to_row)


class SplitInterventionCommand(QUndoCommand):
    def __init__(self, table_window, row, before_text, after_text):
        super().__init__()
        self.table_window = table_window
        self.before_text = before_text
        self.after_text = after_text
        self.original_text = before_text + after_text
        # Capturar el ID, PERSONAJE y SCENE de la fila actual
        self.row_id = int(self.table_window.dataframe.at[row, 'ID'])
        self.personaje = self.table_window.dataframe.at[row, 'PERSONAJE']
        self.scene = self.table_window.dataframe.at[row, 'SCENE']
        self.new_row_id = self.table_window.get_next_id()
        self.new_row_data = {
            'ID': self.new_row_id,
            'SCENE': self.scene,
            'IN': '00:00:00:00',
            'OUT': '00:00:00:00',
            'PERSONAJE': self.personaje,
            'DIÁLOGO': self.after_text
        }
        self.setText("Separar intervención")

    def undo(self):
        # Restaurar el diálogo original
        df_row = self.table_window.find_dataframe_index_by_id(self.row_id)
        if df_row is None:
            return
        self.table_window.dataframe.at[df_row, 'DIÁLOGO'] = self.original_text

        table_row = self.table_window.find_table_row_by_id(self.row_id)
        if table_row is None:
            return
        text_widget = self.table_window.table_widget.cellWidget(table_row, self.table_window.COL_DIALOGUE)
        if text_widget:
            text_widget.blockSignals(True)
            text_widget.setPlainText(self.original_text)
            text_widget.blockSignals(False)
            self.table_window.adjust_row_height(table_row)

        # Eliminar la nueva fila
        new_df_row = self.table_window.find_dataframe_index_by_id(self.new_row_id)
        if new_df_row is not None:
            self.table_window.dataframe = self.table_window.dataframe.drop(new_df_row).reset_index(drop=True)

        new_table_row = self.table_window.find_table_row_by_id(self.new_row_id)
        if new_table_row is not None:
            self.table_window.table_widget.removeRow(new_table_row)

    def redo(self):
        # Actualizar el diálogo en la fila original
        df_row = self.table_window.find_dataframe_index_by_id(self.row_id)
        if df_row is None:
            return
        self.table_window.dataframe.at[df_row, 'DIÁLOGO'] = self.before_text

        table_row = self.table_window.find_table_row_by_id(self.row_id)
        if table_row is None:
            return
        text_widget = self.table_window.table_widget.cellWidget(table_row, self.table_window.COL_DIALOGUE)
        if text_widget:
            text_widget.blockSignals(True)
            text_widget.setPlainText(self.before_text)
            text_widget.blockSignals(False)
            self.table_window.adjust_row_height(table_row)

        # Insertar nueva fila en el DataFrame
        df_new_row = df_row + 1
        self.table_window.dataframe = pd.concat([
            self.table_window.dataframe.iloc[:df_new_row],
            pd.DataFrame([self.new_row_data]),
            self.table_window.dataframe.iloc[df_new_row:]
        ]).reset_index(drop=True)

        # Insertar nueva fila en la tabla
        table_new_row = table_row + 1
        self.table_window.table_widget.insertRow(table_new_row)
        for col_index, col_name in enumerate(self.table_window.columns):
            if col_name == "DIÁLOGO":
                dialogo_text = self.new_row_data['DIÁLOGO']
                dialogo_item = self.table_window.create_text_edit(dialogo_text, table_new_row, self.table_window.COL_DIALOGUE)
                self.table_window.table_widget.setCellWidget(table_new_row, self.table_window.COL_DIALOGUE, dialogo_item)
            else:
                value = self.new_row_data.get(col_name, '')
                item = self.table_window.create_table_item(str(value), col_index)
                self.table_window.table_widget.setItem(table_new_row, col_index, item)
        self.table_window.adjust_row_height(table_new_row)


class MergeInterventionsCommand(QUndoCommand):
    def __init__(self, table_window, row, merged_dialog):
        super().__init__()
        self.table_window = table_window
        self.row = row
        self.merged_dialog = merged_dialog
        self.next_row_data = self.table_window.dataframe.iloc[row + 1].copy()
        self.original_dialog = self.table_window.dataframe.at[row, 'DIÁLOGO']
        self.setText("Juntar intervenciones")

    def undo(self):
        # Restaurar diálogo original
        command = EditCommand(self.table_window, self.row, self.table_window.COL_DIALOGUE, self.merged_dialog, self.original_dialog)
        self.table_window.undo_stack.push(command)

        # Restaurar fila eliminada
        self.table_window.table_widget.insertRow(self.row + 1)
        for col_index, col_name in enumerate(self.table_window.columns):
            if col_name == "DIÁLOGO":
                dialogo_text = self.next_row_data[col_name]
                dialogo_item = self.table_window.create_text_edit(dialogo_text, self.row + 1, self.table_window.COL_DIALOGUE)
                self.table_window.table_widget.setCellWidget(self.row + 1, self.table_window.COL_DIALOGUE, dialogo_item)
            else:
                value = self.next_row_data[col_name]
                item = self.table_window.create_table_item(str(value), col_index)
                self.table_window.table_widget.setItem(self.row + 1, col_index, item)

        self.table_window.adjust_row_height(self.row + 1)

        # Insertar datos en el DataFrame
        upper_df = self.table_window.dataframe.iloc[:self.row + 1]
        lower_df = self.table_window.dataframe.iloc[self.row + 1:]
        new_df = pd.DataFrame([self.next_row_data.to_dict()])
        self.table_window.dataframe = pd.concat([upper_df, new_df, lower_df], ignore_index=True)

    def redo(self):
        # Actualizar diálogo
        command = EditCommand(self.table_window, self.row, self.table_window.COL_DIALOGUE, self.original_dialog, self.merged_dialog)
        self.table_window.undo_stack.push(command)

        # Eliminar siguiente fila
        self.table_window.table_widget.removeRow(self.row + 1)
        self.table_window.dataframe = self.table_window.dataframe.drop(self.row + 1).reset_index(drop=True)

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

    class KeyPressFilter(QObject):
        def __init__(self, table_window):
            super().__init__()
            self.table_window = table_window

        def eventFilter(self, obj, event):
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_F11 and not event.isAutoRepeat():
                    self.table_window.video_player_widget.start_out_timer()
                    return True
            elif event.type() == QEvent.KeyRelease:
                if event.key() == Qt.Key_F11 and not event.isAutoRepeat():
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
        self.dataframe = pd.DataFrame()
        self.unsaved_changes = False  # Bandera para cambios sin guardar
        self.undo_stack = QUndoStack(self)  # Pila para deshacer/rehacer
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
        self.table_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Permitir selección múltiple con Shift/Ctrl
        self.table_widget.setEditTriggers(QAbstractItemView.DoubleClicked)
        layout.addWidget(self.table_widget)
        self.table_widget.setItemDelegateForColumn(0, TimeCodeDelegate(self.table_widget))
        self.table_widget.setItemDelegateForColumn(1, TimeCodeDelegate(self.table_widget))

        # Pasar el método get_character_names al delegado
        self.table_widget.setItemDelegateForColumn(2, CharacterDelegate(get_names_callback=self.get_character_names, parent=self.table_widget))


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
            self.main_window.add_to_recent_files(file_name)

    def load_data(self, file_name):
        try:
            guion_data = leer_guion(file_name)
            self.dataframe = pd.DataFrame(guion_data)
            required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
            if not all(col in self.dataframe.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
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
            self.table_widget.setColumnCount(self.dataframe.shape[1])
            self.table_widget.setHorizontalHeaderLabels(self.dataframe.columns.tolist())

            for i in range(self.dataframe.shape[0]):
                for j in range(self.dataframe.shape[1]):
                    if j == 3:
                        dialog_text = str(self.dataframe.iloc[i, j])
                        text_edit = self.create_text_edit(dialog_text, i, j)
                        self.table_widget.setCellWidget(i, j, text_edit)
                    else:
                        item = self.create_table_item(str(self.dataframe.iloc[i, j]))
                        self.table_widget.setItem(i, j, item)

            self.table_widget.resizeColumnsToContents()
            self.table_widget.horizontalHeader().setStretchLastSection(True)
            self.adjust_all_row_heights()
            self.table_widget.blockSignals(False)  # Desbloquear señales
        except Exception as e:
            self.handle_exception(e, "Error al llenar la tabla")

    def create_text_edit(self, text, row, column):
        text_edit = QTextEdit(text)
        text_edit.setStyleSheet("font-size: 16px;")
        text_edit.setFont(QFont("Arial", 12))
        text_edit.textChanged.connect(self.generate_text_changed_callback(row, column))
        return text_edit

    def create_table_item(self, text):
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
                text_widget = self.table_widget.cellWidget(i, 3)
                if text_widget:
                    dialogo_actual = text_widget.toPlainText()
                    dialogo_ajustado = ajustar_dialogo(dialogo_actual)
                    text_widget.blockSignals(True)
                    text_widget.setText(dialogo_ajustado)
                    text_widget.blockSignals(False)
                    old_text = self.dataframe.at[i, 'DIÁLOGO']
                    if dialogo_actual != dialogo_ajustado:
                        command = EditCommand(self, i, 3, old_text, dialogo_ajustado)
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
            text_widget = self.table_widget.cellWidget(row, 3)
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
            text_widget = self.table_widget.cellWidget(row, column)
            new_text = text_widget.toPlainText()
            old_text = self.dataframe.at[row, self.dataframe.columns[column]]
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
            new_text = item.text()
            old_text = self.dataframe.at[row, self.dataframe.columns[column]]
            if new_text != old_text:
                command = EditCommand(self, row, column, old_text, new_text)
                self.undo_stack.push(command)
                self.unsaved_changes = True
                if column == 2:
                    # Actualizar el completer
                    self.update_character_completer()
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
            for row in range(self.table_widget.rowCount()):
                dialog_widget = self.table_widget.cellWidget(row, 3)
                if dialog_widget:
                    self.dataframe.at[row, 'DIÁLOGO'] = dialog_widget.toPlainText()
            self.dataframe.to_excel(path, index=False)
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

            dialog_widget = self.table_widget.cellWidget(selected_row, 3)
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
                    command = EditCommand(self, selected_row, 0, old_value, time_code)
                    self.undo_stack.push(command)
                    self.unsaved_changes = True
            elif action.upper() == "OUT":
                old_value = self.dataframe.at[selected_row, 'OUT']
                if time_code != old_value:
                    command = EditCommand(self, selected_row, 1, old_value, time_code)
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
                old_value = self.dataframe.at[next_row, 'IN']
                if time_code != old_value:
                    command = EditCommand(self, next_row, 0, old_value, time_code)
                    self.undo_stack.push(command)
                    self.unsaved_changes = True
                self.adjust_row_height(next_row)
                self.table_widget.scrollToItem(self.table_widget.item(next_row, 0), QAbstractItemView.PositionAtCenter)
        except Exception as e:
            self.handle_exception(e, "Error al seleccionar la siguiente fila")

    def load_from_excel(self, path=None):
        try:
            if not path:
                path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Excel", "", "Archivos Excel (*.xlsx)")
            if path:
                df = pd.read_excel(path)
                required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
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

            dialog_current_widget = self.table_widget.cellWidget(selected_row, 3)
            dialog_next_widget = self.table_widget.cellWidget(selected_row + 1, 3)
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
                data = self.dataframe.to_dict(orient='records')
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Éxito", "Datos guardados correctamente en JSON.")
                self.unsaved_changes = False  # Cambios guardados
            else:
                # El usuario canceló la exportación
                QMessageBox.information(self, "Exportación cancelada", "La exportación ha sido cancelada.")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en JSON")

    def load_from_json(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
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
                command_in = EditCommand(self, next_row, 0, old_in, in_time)
                self.undo_stack.push(command_in)
                self.unsaved_changes = True

            # Copiar OUT
            old_out = self.dataframe.at[next_row, 'OUT']
            if out_time != old_out:
                command_out = EditCommand(self, next_row, 1, old_out, out_time)
                self.undo_stack.push(command_out)
                self.unsaved_changes = True

            QMessageBox.information(self, "Copiar IN/OUT", "Tiempos IN y OUT copiados a la siguiente intervención.")
        except Exception as e:
            self.handle_exception(e, "Error al copiar IN/OUT a la siguiente intervención")

    def get_character_names(self):
        return sorted(set(self.dataframe['PERSONAJE'].tolist()))

    def update_character_completer(self):
        # Actualizar el completer en el delegado
        self.table_widget.setItemDelegateForColumn(2, CharacterDelegate(get_names_callback=self.get_character_names, parent=self.table_widget))

    def update_character_name(self, old_name, new_name):
        # Actualizar nombres en el dataframe
        self.dataframe.loc[self.dataframe['PERSONAJE'] == old_name, 'PERSONAJE'] = new_name
        # Actualizar la tabla visualmente
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 2)
            if item and item.text() == old_name:
                item.setText(new_name)
        self.unsaved_changes = True
        self.update_character_completer()
        # Emitir señal de cambio de nombre
        self.character_name_changed.emit()

    def find_and_replace(self, find_text, replace_text):
        try:
            for row in range(self.table_widget.rowCount()):
                # Reemplazar en diálogos
                dialog_widget = self.table_widget.cellWidget(row, 3)
                if dialog_widget:
                    text = dialog_widget.toPlainText()
                    if find_text in text:
                        new_text = text.replace(find_text, replace_text)
                        command = EditCommand(self, row, 3, text, new_text)
                        self.undo_stack.push(command)
                        self.unsaved_changes = True

                # Reemplazar en personajes
                character_item = self.table_widget.item(row, 2)
                if character_item:
                    text = character_item.text()
                    if find_text in text:
                        new_text = text.replace(find_text, replace_text)
                        command = EditCommand(self, row, 2, text, new_text)
                        self.undo_stack.push(command)
                        self.unsaved_changes = True
            QMessageBox.information(self, "Buscar y Reemplazar", "Reemplazo completado.")
        except Exception as e:
            self.handle_exception(e, "Error en buscar y reemplazar")

    def handle_exception(self, exception, message):
        QMessageBox.critical(self, "Error", f"{message}: {str(exception)}")

# Clases de comandos para deshacer/rehacer
class EditCommand(QUndoCommand):
    def __init__(self, table_window, row, column, old_value, new_value):
        super().__init__()
        self.table_window = table_window
        self.row = row
        self.column = column
        self.old_value = old_value
        self.new_value = new_value

    def undo(self):
        self._apply_value(self.old_value)

    def redo(self):
        self._apply_value(self.new_value)

    def _apply_value(self, value):
        self.table_window.dataframe.iat[self.row, self.column] = value
        if self.column == 3:
            text_widget = self.table_window.table_widget.cellWidget(self.row, self.column)
            if text_widget:
                text_widget.blockSignals(True)
                text_widget.setPlainText(value)
                text_widget.blockSignals(False)
                self.table_window.adjust_row_height(self.row)
        else:
            item = self.table_window.table_widget.item(self.row, self.column)
            if item:
                item.setText(value)
        # Actualizar el completer si es necesario
        if self.column == 2:
            self.table_window.update_character_completer()

class AddRowCommand(QUndoCommand):
    def __init__(self, table_window, row):
        super().__init__()
        self.table_window = table_window
        self.row = row
        self.new_row_data = {
            'IN': '00:00:00:00',
            'OUT': '00:00:00:00',
            'PERSONAJE': 'Personaje',
            'DIÁLOGO': 'Nuevo diálogo'
        }
        self.setText("Agregar fila")

    def undo(self):
        self.table_window.table_widget.removeRow(self.row)
        self.table_window.dataframe = self.table_window.dataframe.drop(self.row).reset_index(drop=True)

    def redo(self):
        self.table_window.table_widget.insertRow(self.row)
        in_item = self.table_window.create_table_item(self.new_row_data['IN'])
        out_item = self.table_window.create_table_item(self.new_row_data['OUT'])
        personaje_item = self.table_window.create_table_item(self.new_row_data['PERSONAJE'])

        self.table_window.table_widget.setItem(self.row, 0, in_item)
        self.table_window.table_widget.setItem(self.row, 1, out_item)
        self.table_window.table_widget.setItem(self.row, 2, personaje_item)

        text_edit = self.table_window.create_text_edit(self.new_row_data['DIÁLOGO'], self.row, 3)
        self.table_window.table_widget.setCellWidget(self.row, 3, text_edit)

        self.table_window.adjust_row_height(self.row)

        upper_df = self.table_window.dataframe.iloc[:self.row] if self.row > 0 else pd.DataFrame()
        lower_df = self.table_window.dataframe.iloc[self.row:] if self.row < self.table_window.dataframe.shape[0] else pd.DataFrame()
        new_df = pd.DataFrame([self.new_row_data])
        self.table_window.dataframe = pd.concat([upper_df, new_df, lower_df], ignore_index=True)

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
            in_item = self.table_window.create_table_item(data_row['IN'])
            out_item = self.table_window.create_table_item(data_row['OUT'])
            personaje_item = self.table_window.create_table_item(data_row['PERSONAJE'])

            self.table_window.table_widget.setItem(row, 0, in_item)
            self.table_window.table_widget.setItem(row, 1, out_item)
            self.table_window.table_widget.setItem(row, 2, personaje_item)

            text_edit = self.table_window.create_text_edit(data_row['DIÁLOGO'], row, 3)
            self.table_window.table_widget.setCellWidget(row, 3, text_edit)

            self.table_window.adjust_row_height(row)

            self.table_window.dataframe = pd.concat([
                self.table_window.dataframe.iloc[:row],
                pd.DataFrame([data_row]),
                self.table_window.dataframe.iloc[row:]
            ]).reset_index(drop=True)

    def redo(self):
        for row in reversed(self.rows):
            self.table_window.table_widget.removeRow(row)
            self.table_window.dataframe = self.table_window.dataframe.drop(row).reset_index(drop=True)

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
        # Mover datos en el dataframe
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
            if col == 3:
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
            if col == 3:
                text = row_data_items.get(col, '')
                text_edit = self.table_window.create_text_edit(text, to_row, col)
                self.table_widget.setCellWidget(to_row, col, text_edit)
            else:
                text = row_data_items.get(col, '')
                item = self.table_window.create_table_item(text)
                self.table_widget.setItem(to_row, col, item)

        self.table_widget.blockSignals(False)
        self.table_window.adjust_row_height(to_row)

class SplitInterventionCommand(QUndoCommand):
    def __init__(self, table_window, row, before_text, after_text):
        super().__init__()
        self.table_window = table_window
        self.row = row
        self.before_text = before_text
        self.after_text = after_text
        self.new_row_data = {
            'IN': '00:00:00:00',
            'OUT': '00:00:00:00',
            'PERSONAJE': self.table_window.dataframe.at[row, 'PERSONAJE'],
            'DIÁLOGO': self.after_text
        }
        self.setText("Separar intervención")

    def undo(self):
        # Restaurar el texto original
        command = EditCommand(self.table_window, self.row, 3, self.before_text, self.before_text + self.after_text)
        command.redo()
        self.table_window.table_widget.removeRow(self.row + 1)
        self.table_window.dataframe = self.table_window.dataframe.drop(self.row + 1).reset_index(drop=True)

    def redo(self):
        # Actualizar el texto de la fila original
        command = EditCommand(self.table_window, self.row, 3, self.before_text + self.after_text, self.before_text)
        command.redo()

        # Insertar nueva fila
        self.table_window.table_widget.insertRow(self.row + 1)
        in_item = self.table_window.create_table_item(self.new_row_data['IN'])
        out_item = self.table_window.create_table_item(self.new_row_data['OUT'])
        personaje_item = self.table_window.create_table_item(self.new_row_data['PERSONAJE'])

        self.table_window.table_widget.setItem(self.row + 1, 0, in_item)
        self.table_window.table_widget.setItem(self.row + 1, 1, out_item)
        self.table_window.table_widget.setItem(self.row + 1, 2, personaje_item)

        text_edit = self.table_window.create_text_edit(self.new_row_data['DIÁLOGO'], self.row + 1, 3)
        self.table_window.table_widget.setCellWidget(self.row + 1, 3, text_edit)

        self.table_window.adjust_row_height(self.row + 1)

        upper_df = self.table_window.dataframe.iloc[:self.row + 1] if self.row >= 0 else pd.DataFrame()
        lower_df = self.table_window.dataframe.iloc[self.row + 1:] if self.row + 1 < self.table_window.dataframe.shape[0] else pd.DataFrame()
        new_df = pd.DataFrame([self.new_row_data])
        self.table_window.dataframe = pd.concat([upper_df, new_df, lower_df], ignore_index=True)

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
        command = EditCommand(self.table_window, self.row, 3, self.merged_dialog, self.original_dialog)
        command.redo()
        # Restaurar fila eliminada
        self.table_window.table_widget.insertRow(self.row + 1)
        in_item = self.table_window.create_table_item(self.next_row_data['IN'])
        out_item = self.table_window.create_table_item(self.next_row_data['OUT'])
        personaje_item = self.table_window.create_table_item(self.next_row_data['PERSONAJE'])

        self.table_window.table_widget.setItem(self.row + 1, 0, in_item)
        self.table_window.table_widget.setItem(self.row + 1, 1, out_item)
        self.table_window.table_widget.setItem(self.row + 1, 2, personaje_item)

        text_edit = self.table_window.create_text_edit(self.next_row_data['DIÁLOGO'], self.row + 1, 3)
        self.table_window.table_widget.setCellWidget(self.row + 1, 3, text_edit)

        self.table_window.adjust_row_height(self.row + 1)

        upper_df = self.table_window.dataframe.iloc[:self.row + 1]
        lower_df = self.table_window.dataframe.iloc[self.row + 1:]
        self.table_window.dataframe = pd.concat([upper_df, pd.DataFrame([self.next_row_data]), lower_df], ignore_index=True)

    def redo(self):
        # Actualizar diálogo
        command = EditCommand(self.table_window, self.row, 3, self.original_dialog, self.merged_dialog)
        command.redo()
        # Eliminar siguiente fila
        self.table_window.table_widget.removeRow(self.row + 1)
        self.table_window.dataframe = self.table_window.dataframe.drop(self.row + 1).reset_index(drop=True)


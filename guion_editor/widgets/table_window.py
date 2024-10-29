# guion_editor/widgets/table_window.py

import json
import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QTableWidgetItem, QTextEdit, QFileDialog, QAbstractItemView,
    QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton
)

import pandas as pd

from guion_editor.delegates.custom_delegates import TimeCodeDelegate, CharacterDelegate
from guion_editor.utils.dialog_utils import leer_guion, ajustar_dialogo
from guion_editor.widgets.custom_table_widget import CustomTableWidget

# Configuración del logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


class TableWindow(QWidget):
    # Señal para comunicar el establecimiento de la posición del video
    in_out_signal = pyqtSignal(str, int)  # Emitirá 'IN'/'OUT' y la posición en milisegundos

    def __init__(self, video_player_widget):
        super().__init__()
        self.setWindowTitle("Editor de Guion")
        self.setGeometry(100, 100, 800, 600)
        self.video_player_widget = video_player_widget  # Almacenar referencia al VideoPlayerWidget
        self.video_player_widget.in_out_signal.connect(self.update_in_out)
        self.dataframe = pd.DataFrame()

        self.setup_ui()
        logger.debug("TableWindow inicializado correctamente.")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.setup_buttons(layout)
        self.setup_table_widget(layout)

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
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Deshabilitar edición directa
        layout.addWidget(self.table_widget)
        
        # Configurar delegados personalizados
        self.table_widget.setItemDelegateForColumn(0, TimeCodeDelegate(self.table_widget))
        self.table_widget.setItemDelegateForColumn(1, TimeCodeDelegate(self.table_widget))
        self.table_widget.setItemDelegateForColumn(2, CharacterDelegate(self.table_widget))
        
        # Conectar la señal de Ctrl + clic a un método
        self.table_widget.cellCtrlClicked.connect(self.handle_ctrl_click)

    def handle_exception(self, e, message):
        logger.error(f"{message}: {e}")
        QMessageBox.warning(self, "Error", f"{message}: {str(e)}")

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Abrir guion", "", "Documentos de Word (*.docx)"
        )
        if file_name:
            logger.info(f"Abriendo archivo: {file_name}")
            self.load_data(file_name)

    def load_data(self, file_name):
        try:
            guion_data = leer_guion(file_name)
            self.dataframe = pd.DataFrame(guion_data)
            logger.debug(f"Datos cargados en DataFrame: {self.dataframe.head()}")
            required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
            if not all(col in self.dataframe.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
            self.populate_table()
        except Exception as e:
            self.handle_exception(e, "Error al cargar los datos")

    def populate_table(self):
        try:
            if self.dataframe.empty:
                QMessageBox.information(self, "Información", "El archivo está vacío.")
                return

            self.table_widget.clear()
            self.table_widget.setRowCount(self.dataframe.shape[0])
            self.table_widget.setColumnCount(self.dataframe.shape[1])
            self.table_widget.setHorizontalHeaderLabels(self.dataframe.columns.tolist())

            for i in range(self.dataframe.shape[0]):
                for j in range(self.dataframe.shape[1]):
                    if j == 3:  # Columna de diálogo
                        dialog_text = str(self.dataframe.iloc[i, j])
                        text_edit = self.create_text_edit(dialog_text, i, j)
                        self.table_widget.setCellWidget(i, j, text_edit)
                    else:
                        item = self.create_table_item(str(self.dataframe.iloc[i, j]))
                        self.table_widget.setItem(i, j, item)

            self.table_widget.resizeColumnsToContents()
            self.table_widget.horizontalHeader().setStretchLastSection(True)
            self.adjust_all_row_heights()
            logger.info("Tabla poblada correctamente.")
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
                    self.dataframe.at[i, 'DIÁLOGO'] = dialogo_ajustado
                    self.adjust_row_height(i)
            QMessageBox.information(self, "Éxito", "Diálogos ajustados correctamente.")
            logger.info("Diálogos ajustados correctamente.")
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
                total_height = text_height + margins.top() + margins.bottom() + 10  # Padding adicional
                self.table_widget.setRowHeight(row, int(total_height))
        except Exception as e:
            self.handle_exception(e, f"Error al ajustar la altura de la fila {row}")

    def on_text_changed(self, row, column):
        try:
            text_widget = self.table_widget.cellWidget(row, column)
            new_text = text_widget.toPlainText()
            self.dataframe.at[row, self.dataframe.columns[column]] = new_text
            logger.debug(f"Texto cambiado en fila {row}, columna {column}: {new_text}")
            if column == 3:
                self.adjust_row_height(row)
        except Exception as e:
            self.handle_exception(e, "Error al actualizar texto en la tabla")

    def add_new_row(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                selected_row = self.table_widget.rowCount()
            else:
                selected_row += 1

            self.table_widget.insertRow(selected_row)

            in_item = self.create_table_item("00:00:00:00")
            out_item = self.create_table_item("00:00:00:00")
            personaje_item = self.create_table_item("Personaje")

            self.table_widget.setItem(selected_row, 0, in_item)
            self.table_widget.setItem(selected_row, 1, out_item)
            self.table_widget.setItem(selected_row, 2, personaje_item)

            text_edit = self.create_text_edit("Nuevo diálogo", selected_row, 3)
            self.table_widget.setCellWidget(selected_row, 3, text_edit)

            self.adjust_row_height(selected_row)

            new_row = {
                'IN': '00:00:00:00',
                'OUT': '00:00:00:00',
                'PERSONAJE': 'Personaje',
                'DIÁLOGO': 'Nuevo diálogo'
            }
            upper_df = self.dataframe.iloc[:selected_row] if selected_row > 0 else pd.DataFrame()
            lower_df = self.dataframe.iloc[selected_row:] if selected_row < self.dataframe.shape[0] else pd.DataFrame()
            new_df = pd.DataFrame([new_row])
            self.dataframe = pd.concat([upper_df, new_df, lower_df], ignore_index=True)
            logger.info(f"Nueva fila agregada en la posición {selected_row}.")
        except Exception as e:
            self.handle_exception(e, "Error al agregar una nueva fila")

    def remove_row(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row != -1:
                confirm = QMessageBox.question(
                    self, "Confirmar Eliminación",
                    f"¿Estás seguro de que deseas eliminar la fila {selected_row + 1}?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm == QMessageBox.Yes:
                    self.table_widget.removeRow(selected_row)
                    self.dataframe = self.dataframe.drop(selected_row).reset_index(drop=True)
                    logger.info(f"Fila {selected_row} eliminada.")
                    QMessageBox.information(self, "Fila Eliminada", "La fila ha sido eliminada con éxito.")
            else:
                QMessageBox.warning(self, "Eliminar Fila", "Por favor, selecciona una fila para eliminar.")
        except Exception as e:
            self.handle_exception(e, "Error al eliminar la fila")

    def move_row_up(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row > 0:
                self.swap_rows(selected_row, selected_row - 1)
                self.table_widget.selectRow(selected_row - 1)
                logger.info(f"Fila {selected_row} movida hacia arriba.")
        except Exception as e:
            self.handle_exception(e, "Error al mover la fila hacia arriba")

    def move_row_down(self):
        try:
            selected_row = self.table_widget.currentRow()
            if selected_row < self.table_widget.rowCount() - 1:
                self.swap_rows(selected_row, selected_row + 1)
                self.table_widget.selectRow(selected_row + 1)
                logger.info(f"Fila {selected_row} movida hacia abajo.")
        except Exception as e:
            self.handle_exception(e, "Error al mover la fila hacia abajo")

    def swap_rows(self, row1, row2):
        try:
            # Intercambiar los elementos de las columnas que no son QTextEdit
            for col in range(self.table_widget.columnCount()):
                if col != 3:  # Excepto la columna de diálogos
                    item1 = self.table_widget.item(row1, col)
                    item2 = self.table_widget.item(row2, col)
                    if item1 and item2:
                        text1 = item1.text()
                        text2 = item2.text()
                        font1 = item1.font()
                        font2 = item2.font()
                        new_item1 = self.create_table_item(text2)
                        new_item1.setFont(font2)
                        new_item2 = self.create_table_item(text1)
                        new_item2.setFont(font1)
                        self.table_widget.setItem(row1, col, new_item1)
                        self.table_widget.setItem(row2, col, new_item2)

            # Intercambiar los QTextEdit
            widget1 = self.table_widget.cellWidget(row1, 3)
            widget2 = self.table_widget.cellWidget(row2, 3)
            if widget1 and widget2:
                text1 = widget1.toPlainText()
                text2 = widget2.toPlainText()
                widget1.blockSignals(True)
                widget2.blockSignals(True)
                widget1.setPlainText(text2)
                widget2.setPlainText(text1)
                widget1.blockSignals(False)
                widget2.blockSignals(False)
                # Preservar la fuente
                font1 = widget1.font()
                font2 = widget2.font()
                widget1.setFont(font2)
                widget2.setFont(font1)

            # Intercambiar los datos en el DataFrame
            self.dataframe.iloc[[row1, row2]] = self.dataframe.iloc[[row2, row1]].values
            logger.debug(f"Filas {row1} y {row2} intercambiadas en el DataFrame.")
        except Exception as e:
            self.handle_exception(e, "Error al intercambiar filas")

    def handle_ctrl_click(self, row):
        """
        Maneja el evento de Ctrl + clic en una fila.
        Emite la señal in_out_signal con la posición en milisegundos.
        """
        try:
            in_time_code = self.dataframe.at[row, 'IN']
            logger.debug(f"Ctrl + clic en fila {row}: IN={in_time_code}")
            milliseconds = self.convert_time_code_to_milliseconds(in_time_code)
            self.in_out_signal.emit("IN", milliseconds)
            logger.info(f"Video desplazado a {in_time_code} ({milliseconds} ms)")
        except Exception as e:
            self.handle_exception(e, "Error al desplazar el video")

    def convert_time_code_to_milliseconds(self, time_code):
        """
        Convierte un time code en formato HH:MM:SS:FF a milisegundos.
        Asume 25 frames por segundo.
        """
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
        """
        Convierte milisegundos a formato de time code HH:MM:SS:FF.
        Asume 25 frames por segundo.
        """
        try:
            total_seconds = ms // 1000
            frames = int((ms % 1000) / (1000 / 25))
            seconds = total_seconds % 60
            minutes = (total_seconds // 60) % 60
            hours = total_seconds // 3600
            return f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}"
        except Exception as e:
            logger.error(f"Error al convertir milisegundos a time code: {e}")
            return "00:00:00:00"

    def export_to_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", "", "Archivos Excel (*.xlsx)")
            if path:
                self.save_to_excel(path)
                QMessageBox.information(self, "Éxito", "Datos exportados correctamente a Excel.")
                logger.info(f"Datos exportados a Excel en: {path}")
        except Exception as e:
            self.handle_exception(e, "Error al exportar a Excel")

    def save_to_excel(self, path):
        try:
            # Actualizar el DataFrame con los diálogos actuales
            for row in range(self.table_widget.rowCount()):
                dialog_widget = self.table_widget.cellWidget(row, 3)
                if dialog_widget:
                    self.dataframe.at[row, 'DIÁLOGO'] = dialog_widget.toPlainText()
            self.dataframe.to_excel(path, index=False)
            logger.debug("Datos guardados correctamente en Excel.")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en Excel")
            raise e  # Será manejado por el método que llama

    def import_from_excel(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Excel", "", "Archivos Excel (*.xlsx)")
            if path:
                self.load_from_excel(path)
        except Exception as e:
            self.handle_exception(e, "Error al importar desde Excel")

    def load_from_excel(self, path):
        try:
            df = pd.read_excel(path)
            logger.debug(f"Datos importados desde Excel: {df.head()}")
            required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
            if not all(col in df.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
            self.dataframe = df
            self.populate_table()
            QMessageBox.information(self, "Éxito", "Datos importados correctamente desde Excel.")
            logger.info("Datos importados correctamente desde Excel.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde Excel")

    def save_to_json(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                data = self.dataframe.to_dict(orient='records')
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Éxito", "Datos guardados correctamente en JSON.")
                logger.info(f"Datos guardados en JSON en: {path}")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en JSON")

    def load_from_json(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                logger.debug(f"Datos cargados desde JSON: {df.head()}")
                required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
                self.dataframe = df
                self.populate_table()
                QMessageBox.information(self, "Éxito", "Datos cargados correctamente desde JSON.")
                logger.info("Datos cargados correctamente desde JSON.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde JSON")

    def split_intervention(self):
        """
        Funcionalidad para separar una intervención en dos filas basándose en la selección de texto.
        Shortcut: Alt+I
        """
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

            # Split the text
            before = text[:position]
            after = text[position:]

            # Update current dialog
            dialog_widget.blockSignals(True)
            dialog_widget.setPlainText(before)
            dialog_widget.blockSignals(False)
            self.dataframe.at[selected_row, 'DIÁLOGO'] = before
            self.adjust_row_height(selected_row)

            # Insert a new row below
            self.table_widget.insertRow(selected_row + 1)

            # Crear elementos de las celdas con la misma fuente que las filas anteriores
            in_item = self.create_table_item("00:00:00:00")
            out_item = self.create_table_item("00:00:00:00")
            personaje = self.dataframe.at[selected_row, 'PERSONAJE']
            personaje_item = self.create_table_item(personaje)

            self.table_widget.setItem(selected_row + 1, 0, in_item)
            self.table_widget.setItem(selected_row + 1, 1, out_item)
            self.table_widget.setItem(selected_row + 1, 2, personaje_item)

            # Crear el QTextEdit para el diálogo
            new_dialog_widget = self.create_text_edit(after, selected_row + 1, 3)
            self.table_widget.setCellWidget(selected_row + 1, 3, new_dialog_widget)

            self.adjust_row_height(selected_row + 1)

            # Insertar la nueva fila en el DataFrame
            new_row = {
                'IN': '00:00:00:00',
                'OUT': '00:00:00:00',
                'PERSONAJE': personaje,
                'DIÁLOGO': after
            }
            upper_df = self.dataframe.iloc[:selected_row + 1] if selected_row >= 0 else pd.DataFrame()
            lower_df = self.dataframe.iloc[selected_row + 1:] if selected_row + 1 < self.dataframe.shape[0] else pd.DataFrame()
            new_df = pd.DataFrame([new_row])
            self.dataframe = pd.concat([upper_df, new_df, lower_df], ignore_index=True)
            logger.info(f"Intervención separada en la fila {selected_row} en dos filas.")
        except Exception as e:
            self.handle_exception(e, "Error al separar intervención")

    def merge_interventions(self):
        """
        Funcionalidad para juntar dos intervenciones consecutivas del mismo personaje en una sola fila.
        Shortcut: Alt+J
        """
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

            # Obtener diálogos
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

            # Merge the dialogues with a space
            merged_dialog = f"{dialog_current} {dialog_next}".strip()

            # Actualizar el diálogo de la primera fila
            dialog_current_widget.blockSignals(True)
            dialog_current_widget.setPlainText(merged_dialog)
            dialog_current_widget.blockSignals(False)
            self.dataframe.at[selected_row, 'DIÁLOGO'] = merged_dialog
            self.adjust_row_height(selected_row)

            # Eliminar la segunda fila
            self.table_widget.removeRow(selected_row + 1)
            self.dataframe = self.dataframe.drop(selected_row + 1).reset_index(drop=True)

            logger.info(f"Intervenciones de la fila {selected_row} y {selected_row + 1} juntadas.")

            QMessageBox.information(self, "Juntar Intervenciones", "Las intervenciones han sido juntadas exitosamente.")
        except Exception as e:
            self.handle_exception(e, "Error al juntar intervenciones")

    def update_in_out(self, action, position_ms):
        """
        Actualiza los campos IN y OUT en la tabla basándose en los códigos de tiempo recibidos.
        """
        try:
            if not action or not position_ms:
                logger.warning("Datos de in_out_signal incompletos.")
                return

            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                logger.warning("No hay fila seleccionada para actualizar IN/OUT.")
                QMessageBox.warning(self, "Error", "No hay fila seleccionada para actualizar IN/OUT.")
                return

            time_code = self.convert_milliseconds_to_time_code(position_ms)
            if action.upper() == "IN":
                item = self.table_widget.item(selected_row, 0)
                if item:
                    item.setText(time_code)
                    self.dataframe.at[selected_row, 'IN'] = time_code
                    logger.debug(f"Actualizado IN en fila {selected_row} a {time_code}")
            elif action.upper() == "OUT":
                item = self.table_widget.item(selected_row, 1)
                if item:
                    item.setText(time_code)
                    self.dataframe.at[selected_row, 'OUT'] = time_code
                    logger.debug(f"Actualizado OUT en fila {selected_row} a {time_code}")
                self.select_next_row_and_set_in(position_ms)
            else:
                logger.warning(f"Tipo de acción in_out desconocido: {action}")
                QMessageBox.warning(self, "Error", f"Tipo de acción in_out desconocido: {action}")
        except Exception as e:
            self.handle_exception(e, "Error en update_in_out")

    def select_next_row_and_set_in(self, current_out_ms):
        try:
            next_row = self.table_widget.currentRow() + 1
            if next_row < self.table_widget.rowCount():
                self.table_widget.selectRow(next_row)
                item = self.table_widget.item(next_row, 0)
                if item:
                    time_code = self.convert_milliseconds_to_time_code(current_out_ms)
                    item.setText(time_code)
                    self.dataframe.at[next_row, 'IN'] = time_code
                self.adjust_row_height(next_row)
                self.table_widget.scrollToItem(self.table_widget.item(next_row, 0), QAbstractItemView.PositionAtCenter)
                logger.debug(f"Establecido IN en la fila {next_row} a {time_code}")
        except Exception as e:
            self.handle_exception(e, "Error al seleccionar la siguiente fila")

    def convert_time_code_to_milliseconds(self, time_code):
        """
        Convierte un time code en formato HH:MM:SS:FF a milisegundos.
        Asume 25 frames por segundo.
        """
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
        """
        Convierte milisegundos a formato de time code HH:MM:SS:FF.
        Asume 25 frames por segundo.
        """
        try:
            total_seconds = ms // 1000
            frames = int((ms % 1000) / (1000 / 25))
            seconds = total_seconds % 60
            minutes = (total_seconds // 60) % 60
            hours = total_seconds // 3600
            return f"{hours:02}:{minutes:02}:{seconds:02}:{frames:02}"
        except Exception as e:
            logger.error(f"Error al convertir milisegundos a time code: {e}")
            return "00:00:00:00"

    def export_to_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", "", "Archivos Excel (*.xlsx)")
            if path:
                self.save_to_excel(path)
                QMessageBox.information(self, "Éxito", "Datos exportados correctamente a Excel.")
                logger.info(f"Datos exportados a Excel en: {path}")
        except Exception as e:
            self.handle_exception(e, "Error al exportar a Excel")

    def save_to_excel(self, path):
        try:
            # Actualizar el DataFrame con los diálogos actuales
            for row in range(self.table_widget.rowCount()):
                dialog_widget = self.table_widget.cellWidget(row, 3)
                if dialog_widget:
                    self.dataframe.at[row, 'DIÁLOGO'] = dialog_widget.toPlainText()
            self.dataframe.to_excel(path, index=False)
            logger.debug("Datos guardados correctamente en Excel.")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en Excel")
            raise e  # Será manejado por el método que llama

    def import_from_excel(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Excel", "", "Archivos Excel (*.xlsx)")
            if path:
                self.load_from_excel(path)
        except Exception as e:
            self.handle_exception(e, "Error al importar desde Excel")

    def load_from_excel(self, path):
        try:
            df = pd.read_excel(path)
            logger.debug(f"Datos importados desde Excel: {df.head()}")
            required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
            if not all(col in df.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
            self.dataframe = df
            self.populate_table()
            QMessageBox.information(self, "Éxito", "Datos importados correctamente desde Excel.")
            logger.info("Datos importados correctamente desde Excel.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde Excel")

    def save_to_json(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                data = self.dataframe.to_dict(orient='records')
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Éxito", "Datos guardados correctamente en JSON.")
                logger.info(f"Datos guardados en JSON en: {path}")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en JSON")

    def load_from_json(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                logger.debug(f"Datos cargados desde JSON: {df.head()}")
                required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
                self.dataframe = df
                self.populate_table()
                QMessageBox.information(self, "Éxito", "Datos cargados correctamente desde JSON.")
                logger.info("Datos cargados correctamente desde JSON.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde JSON")

    def split_intervention(self):
        """
        Funcionalidad para separar una intervención en dos filas basándose en la selección de texto.
        Shortcut: Alt+I
        """
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

            # Split the text
            before = text[:position]
            after = text[position:]

            # Update current dialog
            dialog_widget.blockSignals(True)
            dialog_widget.setPlainText(before)
            dialog_widget.blockSignals(False)
            self.dataframe.at[selected_row, 'DIÁLOGO'] = before
            self.adjust_row_height(selected_row)

            # Insert a new row below
            self.table_widget.insertRow(selected_row + 1)

            # Crear elementos de las celdas con la misma fuente que las filas anteriores
            in_item = self.create_table_item("00:00:00:00")
            out_item = self.create_table_item("00:00:00:00")
            personaje = self.dataframe.at[selected_row, 'PERSONAJE']
            personaje_item = self.create_table_item(personaje)

            self.table_widget.setItem(selected_row + 1, 0, in_item)
            self.table_widget.setItem(selected_row + 1, 1, out_item)
            self.table_widget.setItem(selected_row + 1, 2, personaje_item)

            # Crear el QTextEdit para el diálogo
            new_dialog_widget = self.create_text_edit(after, selected_row + 1, 3)
            self.table_widget.setCellWidget(selected_row + 1, 3, new_dialog_widget)

            self.adjust_row_height(selected_row + 1)

            # Insertar la nueva fila en el DataFrame
            new_row = {
                'IN': '00:00:00:00',
                'OUT': '00:00:00:00',
                'PERSONAJE': personaje,
                'DIÁLOGO': after
            }
            upper_df = self.dataframe.iloc[:selected_row + 1] if selected_row >= 0 else pd.DataFrame()
            lower_df = self.dataframe.iloc[selected_row + 1:] if selected_row + 1 < self.dataframe.shape[0] else pd.DataFrame()
            new_df = pd.DataFrame([new_row])
            self.dataframe = pd.concat([upper_df, new_df, lower_df], ignore_index=True)
            logger.info(f"Intervención separada en la fila {selected_row} en dos filas.")
        except Exception as e:
            self.handle_exception(e, "Error al separar intervención")

    def merge_interventions(self):
        """
        Funcionalidad para juntar dos intervenciones consecutivas del mismo personaje en una sola fila.
        Shortcut: Alt+J
        """
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

            # Obtener diálogos
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

            # Merge the dialogues with a space
            merged_dialog = f"{dialog_current} {dialog_next}".strip()

            # Actualizar el diálogo de la primera fila
            dialog_current_widget.blockSignals(True)
            dialog_current_widget.setPlainText(merged_dialog)
            dialog_current_widget.blockSignals(False)
            self.dataframe.at[selected_row, 'DIÁLOGO'] = merged_dialog
            self.adjust_row_height(selected_row)

            # Eliminar la segunda fila
            self.table_widget.removeRow(selected_row + 1)
            self.dataframe = self.dataframe.drop(selected_row + 1).reset_index(drop=True)

            logger.info(f"Intervenciones de la fila {selected_row} y {selected_row + 1} juntadas.")

            QMessageBox.information(self, "Juntar Intervenciones", "Las intervenciones han sido juntadas exitosamente.")
        except Exception as e:
            self.handle_exception(e, "Error al juntar intervenciones")

    def update_in_out(self, action, position_ms):
        """
        Actualiza los campos IN y OUT en la tabla basándose en los códigos de tiempo recibidos.
        """
        try:
            if not action or not position_ms:
                logger.warning("Datos de in_out_signal incompletos.")
                return

            selected_row = self.table_widget.currentRow()
            if selected_row == -1:
                logger.warning("No hay fila seleccionada para actualizar IN/OUT.")
                QMessageBox.warning(self, "Error", "No hay fila seleccionada para actualizar IN/OUT.")
                return

            time_code = self.convert_milliseconds_to_time_code(position_ms)
            if action.upper() == "IN":
                item = self.table_widget.item(selected_row, 0)
                if item:
                    item.setText(time_code)
                    self.dataframe.at[selected_row, 'IN'] = time_code
                    logger.debug(f"Actualizado IN en fila {selected_row} a {time_code}")
            elif action.upper() == "OUT":
                item = self.table_widget.item(selected_row, 1)
                if item:
                    item.setText(time_code)
                    self.dataframe.at[selected_row, 'OUT'] = time_code
                    logger.debug(f"Actualizado OUT en fila {selected_row} a {time_code}")
                self.select_next_row_and_set_in(position_ms)
            else:
                logger.warning(f"Tipo de acción in_out desconocido: {action}")
                QMessageBox.warning(self, "Error", f"Tipo de acción in_out desconocido: {action}")
        except Exception as e:
            self.handle_exception(e, "Error en update_in_out")

    def select_next_row_and_set_in(self, current_out_ms):
        try:
            next_row = self.table_widget.currentRow() + 1
            if next_row < self.table_widget.rowCount():
                self.table_widget.selectRow(next_row)
                item = self.table_widget.item(next_row, 0)
                if item:
                    time_code = self.convert_milliseconds_to_time_code(current_out_ms)
                    item.setText(time_code)
                    self.dataframe.at[next_row, 'IN'] = time_code
                self.adjust_row_height(next_row)
                self.table_widget.scrollToItem(self.table_widget.item(next_row, 0), QAbstractItemView.PositionAtCenter)
                logger.debug(f"Establecido IN en la fila {next_row} a {time_code}")
        except Exception as e:
            self.handle_exception(e, "Error al seleccionar la siguiente fila")

    def export_to_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", "", "Archivos Excel (*.xlsx)")
            if path:
                self.save_to_excel(path)
                QMessageBox.information(self, "Éxito", "Datos exportados correctamente a Excel.")
                logger.info(f"Datos exportados a Excel en: {path}")
        except Exception as e:
            self.handle_exception(e, "Error al exportar a Excel")

    def save_to_excel(self, path):
        try:
            # Actualizar el DataFrame con los diálogos actuales
            for row in range(self.table_widget.rowCount()):
                dialog_widget = self.table_widget.cellWidget(row, 3)
                if dialog_widget:
                    self.dataframe.at[row, 'DIÁLOGO'] = dialog_widget.toPlainText()
            self.dataframe.to_excel(path, index=False)
            logger.debug("Datos guardados correctamente en Excel.")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en Excel")
            raise e  # Será manejado por el método que llama

    def import_from_excel(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Excel", "", "Archivos Excel (*.xlsx)")
            if path:
                self.load_from_excel(path)
        except Exception as e:
            self.handle_exception(e, "Error al importar desde Excel")

    def load_from_excel(self, path):
        try:
            df = pd.read_excel(path)
            logger.debug(f"Datos importados desde Excel: {df.head()}")
            required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
            if not all(col in df.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
            self.dataframe = df
            self.populate_table()
            QMessageBox.information(self, "Éxito", "Datos importados correctamente desde Excel.")
            logger.info("Datos importados correctamente desde Excel.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde Excel")

    def save_to_json(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                data = self.dataframe.to_dict(orient='records')
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Éxito", "Datos guardados correctamente en JSON.")
                logger.info(f"Datos guardados en JSON en: {path}")
        except Exception as e:
            self.handle_exception(e, "Error al guardar en JSON")

    def load_from_json(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                logger.debug(f"Datos cargados desde JSON: {df.head()}")
                required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
                self.dataframe = df
                self.populate_table()
                QMessageBox.information(self, "Éxito", "Datos cargados correctamente desde JSON.")
                logger.info("Datos cargados correctamente desde JSON.")
        except Exception as e:
            self.handle_exception(e, "Error al cargar desde JSON")

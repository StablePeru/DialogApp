# guion_editor/widgets/table_window.py

from PyQt5.QtWidgets import (
    QWidget, QTableWidgetItem, QTextEdit, QFileDialog, QAbstractItemView,
    QMessageBox, QVBoxLayout, QHBoxLayout, QPushButton
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

import pandas as pd
import logging
import json

from guion_editor.utils.dialog_utils import leer_guion, ajustar_dialogo
from guion_editor.delegates.custom_delegates import TimeCodeDelegate, CharacterDelegate
from guion_editor.widgets.custom_table_widget import CustomTableWidget  # Asegúrate de tener esta clase


class TableWindow(QWidget):
    # Señal para comunicar el establecimiento de la posición del video
    inOutSignal = pyqtSignal(str, int)  # Emitirá 'IN'/'OUT' y la posición en milisegundos

    def __init__(self, video_player_widget):
        super().__init__()
        self.setWindowTitle("Editor de Guion")
        self.setGeometry(100, 100, 800, 600)
        self.setup_logging()
        self.setup_ui()
        self.video_player_widget = video_player_widget  # Almacenar referencia al VideoPlayerWidget
        self.video_player_widget.inOutSignal.connect(self.update_in_out)
        self.logger.debug("TableWindow inicializado correctamente.")

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

    def setup_ui(self):
        self.dataframe = pd.DataFrame()
        layout = QVBoxLayout(self)

        # Crear botones para funcionalidades adicionales
        buttons_layout = QHBoxLayout()
        self.addRowButton = QPushButton("Agregar Línea")
        self.addRowButton.clicked.connect(self.add_new_row)
        self.removeRowButton = QPushButton("Eliminar Fila")
        self.removeRowButton.clicked.connect(self.remove_row)
        self.moveUpButton = QPushButton("Mover Arriba")
        self.moveUpButton.clicked.connect(self.move_row_up)
        self.moveDownButton = QPushButton("Mover Abajo")
        self.moveDownButton.clicked.connect(self.move_row_down)
        self.adjustDialogsButton = QPushButton("Ajustar Diálogos")
        self.adjustDialogsButton.clicked.connect(self.adjust_dialogs)
        self.splitInterventionButton = QPushButton("Separar Intervención")
        self.splitInterventionButton.clicked.connect(self.split_intervention)
        self.mergeInterventionButton = QPushButton("Juntar Intervenciones")
        self.mergeInterventionButton.clicked.connect(self.merge_interventions)

        buttons_layout.addWidget(self.addRowButton)
        buttons_layout.addWidget(self.removeRowButton)
        buttons_layout.addWidget(self.moveUpButton)
        buttons_layout.addWidget(self.moveDownButton)
        buttons_layout.addWidget(self.adjustDialogsButton)
        buttons_layout.addWidget(self.splitInterventionButton)
        buttons_layout.addWidget(self.mergeInterventionButton)

        layout.addLayout(buttons_layout)

        self.tableWidget = CustomTableWidget()
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Deshabilitar edición directa
        layout.addWidget(self.tableWidget)

        # Configurar delegados personalizados
        self.tableWidget.setItemDelegateForColumn(0, TimeCodeDelegate(self.tableWidget))
        self.tableWidget.setItemDelegateForColumn(1, TimeCodeDelegate(self.tableWidget))
        self.tableWidget.setItemDelegateForColumn(2, CharacterDelegate(self.tableWidget))

        # Conectar la señal de Ctrl + clic a un método
        self.tableWidget.cellCtrlClicked.connect(self.handle_ctrl_click)

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Abrir guion", "", "Documentos de Word (*.docx)"
        )
        if file_name:
            self.logger.info(f"Abriendo archivo: {file_name}")
            self.load_data(file_name)

    def load_data(self, file_name):
        try:
            guion_data = leer_guion(file_name)
            self.dataframe = pd.DataFrame(guion_data)
            self.logger.debug(f"Datos cargados en DataFrame: {self.dataframe.head()}")
            required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
            if not all(col in self.dataframe.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
            self.populate_table(self.dataframe)
        except Exception as e:
            self.logger.error(f"Error al cargar los datos: {e}")
            QMessageBox.warning(self, "Error", f"Error al cargar los datos: {str(e)}")

    def populate_table(self, dataframe):
        try:
            if dataframe.empty:
                QMessageBox.information(self, "Información", "El archivo está vacío.")
                return

            self.tableWidget.clear()
            self.tableWidget.setRowCount(dataframe.shape[0])
            self.tableWidget.setColumnCount(dataframe.shape[1])
            self.tableWidget.setHorizontalHeaderLabels(dataframe.columns.tolist())

            for i in range(dataframe.shape[0]):
                for j in range(dataframe.shape[1]):
                    if j == 3:  # Columna de diálogo
                        dialog_text = str(dataframe.iloc[i, j])
                        text_edit = QTextEdit(dialog_text)
                        text_edit.setStyleSheet("font-size: 16px;")
                        text_edit.setFont(QFont("Arial", 12))
                        text_edit.textChanged.connect(
                            self.generate_text_changed_callback(i, j)
                        )
                        self.tableWidget.setCellWidget(i, j, text_edit)
                    else:
                        item = QTableWidgetItem(str(dataframe.iloc[i, j]))
                        item.setFont(QFont("Arial", 12))
                        self.tableWidget.setItem(i, j, item)

            self.tableWidget.resizeColumnsToContents()
            self.tableWidget.horizontalHeader().setStretchLastSection(True)
            self.adjust_all_row_heights()
            self.logger.info("Tabla poblada correctamente.")
        except Exception as e:
            self.logger.error(f"Error al llenar la tabla: {e}")
            QMessageBox.warning(self, "Error", f"Error al llenar la tabla: {str(e)}")

    def generate_text_changed_callback(self, row, column):
        def callback():
            self.on_text_changed(row, column)
        return callback

    def adjust_dialogs(self):
        try:
            for i in range(self.dataframe.shape[0]):
                if self.tableWidget.cellWidget(i, 3):
                    text_widget = self.tableWidget.cellWidget(i, 3)
                    dialogo_actual = text_widget.toPlainText()
                    dialogo_ajustado = ajustar_dialogo(dialogo_actual)
                    text_widget.blockSignals(True)
                    text_widget.setText(dialogo_ajustado)
                    text_widget.blockSignals(False)
                    self.dataframe.at[i, 'DIÁLOGO'] = dialogo_ajustado
                    self.adjust_row_height(i)
            QMessageBox.information(self, "Éxito", "Diálogos ajustados correctamente.")
            self.logger.info("Diálogos ajustados correctamente.")
        except Exception as e:
            self.logger.error(f"Error al ajustar diálogos: {e}")
            QMessageBox.warning(self, "Error", f"Error al ajustar diálogos: {str(e)}")

    def adjust_all_row_heights(self):
        for row in range(self.tableWidget.rowCount()):
            self.adjust_row_height(row)

    def adjust_row_height(self, row):
        try:
            text_widget = self.tableWidget.cellWidget(row, 3)
            if text_widget:
                document = text_widget.document()
                text_height = document.size().height()
                margins = text_widget.contentsMargins()
                total_height = text_height + margins.top() + margins.bottom() + 10  # Padding adicional
                self.tableWidget.setRowHeight(row, int(total_height))
        except Exception as e:
            self.logger.error(f"Error al ajustar la altura de la fila {row}: {e}")

    def on_text_changed(self, row, column):
        try:
            text_widget = self.tableWidget.cellWidget(row, column)
            new_text = text_widget.toPlainText()
            self.dataframe.at[row, self.dataframe.columns[column]] = new_text
            self.logger.debug(f"Texto cambiado en fila {row}, columna {column}: {new_text}")
            if column == 3:
                self.adjust_row_height(row)
        except Exception as e:
            self.logger.error(f"Error al actualizar texto en la tabla: {e}")

    def add_new_row(self):
        try:
            selected_row = self.tableWidget.currentRow()
            if selected_row == -1:
                selected_row = self.tableWidget.rowCount()
            else:
                selected_row += 1

            self.tableWidget.insertRow(selected_row)

            in_item = QTableWidgetItem("00:00:00:00")
            out_item = QTableWidgetItem("00:00:00:00")
            personaje_item = QTableWidgetItem("Personaje")

            font = QFont("Arial", 12)
            in_item.setFont(font)
            out_item.setFont(font)
            personaje_item.setFont(font)

            self.tableWidget.setItem(selected_row, 0, in_item)
            self.tableWidget.setItem(selected_row, 1, out_item)
            self.tableWidget.setItem(selected_row, 2, personaje_item)

            text_edit = QTextEdit("Nuevo diálogo")
            text_edit.setStyleSheet("font-size: 16px;")
            text_edit.setFont(QFont("Arial", 12))
            text_edit.textChanged.connect(
                self.generate_text_changed_callback(selected_row, 3)
            )
            self.tableWidget.setCellWidget(selected_row, 3, text_edit)

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
            self.logger.info(f"Nueva fila agregada en la posición {selected_row}.")
        except Exception as e:
            self.logger.error(f"Error al agregar una nueva fila: {e}")
            QMessageBox.warning(self, "Error", f"Error al agregar una nueva fila: {str(e)}")

    def remove_row(self):
        try:
            selected_row = self.tableWidget.currentRow()
            if selected_row != -1:
                confirm = QMessageBox.question(
                    self, "Confirmar Eliminación",
                    f"¿Estás seguro de que deseas eliminar la fila {selected_row + 1}?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if confirm == QMessageBox.Yes:
                    self.tableWidget.removeRow(selected_row)
                    self.dataframe = self.dataframe.drop(selected_row).reset_index(drop=True)
                    self.logger.info(f"Fila {selected_row} eliminada.")
                    QMessageBox.information(self, "Fila Eliminada", "La fila ha sido eliminada con éxito.")
            else:
                QMessageBox.warning(self, "Eliminar Fila", "Por favor, selecciona una fila para eliminar.")
        except Exception as e:
            self.logger.error(f"Error al eliminar la fila: {e}")
            QMessageBox.warning(self, "Error", f"Error al eliminar la fila: {str(e)}")

    def move_row_up(self):
        try:
            selected_row = self.tableWidget.currentRow()
            if selected_row > 0:
                self.swap_rows(selected_row, selected_row - 1)
                self.tableWidget.selectRow(selected_row - 1)
                self.logger.info(f"Fila {selected_row} movida hacia arriba.")
        except Exception as e:
            self.logger.error(f"Error al mover la fila hacia arriba: {e}")
            QMessageBox.warning(self, "Error", f"Error al mover la fila hacia arriba: {str(e)}")

    def move_row_down(self):
        try:
            selected_row = self.tableWidget.currentRow()
            if selected_row < self.tableWidget.rowCount() - 1:
                self.swap_rows(selected_row, selected_row + 1)
                self.tableWidget.selectRow(selected_row + 1)
                self.logger.info(f"Fila {selected_row} movida hacia abajo.")
        except Exception as e:
            self.logger.error(f"Error al mover la fila hacia abajo: {e}")
            QMessageBox.warning(self, "Error", f"Error al mover la fila hacia abajo: {str(e)}")

    def swap_rows(self, row1, row2):
        try:
            # Intercambiar los elementos de las columnas que no son QTextEdit
            for col in range(self.tableWidget.columnCount()):
                if col != 3:  # Excepto la columna de diálogos
                    item1 = self.tableWidget.item(row1, col)
                    item2 = self.tableWidget.item(row2, col)
                    if item1 and item2:
                        text1 = item1.text()
                        text2 = item2.text()
                        font1 = item1.font()
                        font2 = item2.font()
                        new_item1 = QTableWidgetItem(text2)
                        new_item1.setFont(font2)
                        new_item2 = QTableWidgetItem(text1)
                        new_item2.setFont(font1)
                        self.tableWidget.setItem(row1, col, new_item1)
                        self.tableWidget.setItem(row2, col, new_item2)

            # Intercambiar los QTextEdit
            widget1 = self.tableWidget.cellWidget(row1, 3)
            widget2 = self.tableWidget.cellWidget(row2, 3)
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
            self.logger.debug(f"Filas {row1} y {row2} intercambiadas en el DataFrame.")
        except Exception as e:
            self.logger.error(f"Error al intercambiar filas: {e}")
            QMessageBox.warning(self, "Error", f"Error al intercambiar filas: {str(e)}")

    def handle_ctrl_click(self, row):
        """
        Maneja el evento de Ctrl + clic en una fila.
        Emite la señal inOutSignal con la posición en milisegundos.
        """
        try:
            in_time_code = self.dataframe.at[row, 'IN']
            self.logger.debug(f"Ctrl + clic en fila {row}: IN={in_time_code}")
            milliseconds = self.convert_time_code_to_milliseconds(in_time_code)
            self.inOutSignal.emit("IN", milliseconds)
            self.logger.info(f"Video desplazado a {in_time_code} ({milliseconds} ms)")
        except Exception as e:
            self.logger.error(f"Error al manejar Ctrl + clic: {e}")
            QMessageBox.warning(self, "Error", f"Error al desplazar el video: {str(e)}")

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
            self.logger.error(f"Error al convertir time code a milisegundos: {e}")
            raise

    def export_to_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", "", "Archivos Excel (*.xlsx)")
            if path:
                self.save_to_excel(path)
                QMessageBox.information(self, "Éxito", "Datos exportados correctamente a Excel.")
                self.logger.info(f"Datos exportados a Excel en: {path}")
        except Exception as e:
            self.logger.error(f"Error al exportar a Excel: {e}")
            QMessageBox.warning(self, "Error", f"Error al exportar a Excel: {str(e)}")

    def save_to_excel(self, path):
        try:
            # Actualizar el DataFrame con los diálogos actuales
            for row in range(self.tableWidget.rowCount()):
                dialog_widget = self.tableWidget.cellWidget(row, 3)
                if dialog_widget:
                    self.dataframe.at[row, 'DIÁLOGO'] = dialog_widget.toPlainText()
            self.dataframe.to_excel(path, index=False)
            self.logger.debug("Datos guardados correctamente en Excel.")
        except Exception as e:
            self.logger.error(f"Error al guardar en Excel: {e}")
            raise e

    def import_from_excel(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo Excel", "", "Archivos Excel (*.xlsx)")
            if path:
                self.load_from_excel(path)
        except Exception as e:
            self.logger.error(f"Error al importar desde Excel: {e}")
            QMessageBox.warning(self, "Error", f"Error al importar desde Excel: {str(e)}")

    def load_from_excel(self, path):
        try:
            df = pd.read_excel(path)
            self.logger.debug(f"Datos importados desde Excel: {df.head()}")
            required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
            if not all(col in df.columns for col in required_columns):
                raise ValueError("Faltan columnas requeridas en los datos.")
            self.dataframe = df
            self.populate_table(self.dataframe)
            QMessageBox.information(self, "Éxito", "Datos importados correctamente desde Excel.")
            self.logger.info("Datos importados correctamente desde Excel.")
        except Exception as e:
            self.logger.error(f"Error al cargar desde Excel: {e}")
            QMessageBox.warning(self, "Error", f"Error al importar desde Excel: {str(e)}")

    def save_to_json(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Guardar archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                data = self.dataframe.to_dict(orient='records')
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Éxito", "Datos guardados correctamente en JSON.")
                self.logger.info(f"Datos guardados en JSON en: {path}")
        except Exception as e:
            self.logger.error(f"Error al guardar en JSON: {e}")
            QMessageBox.warning(self, "Error", f"Error al guardar en JSON: {str(e)}")

    def load_from_json(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo JSON", "", "Archivos JSON (*.json)")
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                self.logger.debug(f"Datos cargados desde JSON: {df.head()}")
                required_columns = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError("Faltan columnas requeridas en los datos.")
                self.dataframe = df
                self.populate_table(self.dataframe)
                QMessageBox.information(self, "Éxito", "Datos cargados correctamente desde JSON.")
                self.logger.info("Datos cargados correctamente desde JSON.")
        except Exception as e:
            self.logger.error(f"Error al cargar desde JSON: {e}")
            QMessageBox.warning(self, "Error", f"Error al cargar desde JSON: {str(e)}")

    def split_intervention(self):
        """
        Funcionalidad para separar una intervención en dos filas basándose en la selección de texto.
        Shortcut: Alt+I
        """
        try:
            selected_row = self.tableWidget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Separar Intervención", "Por favor, selecciona una fila para separar.")
                return

            dialog_widget = self.tableWidget.cellWidget(selected_row, 3)
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
            self.tableWidget.insertRow(selected_row + 1)

            # Crear elementos de las celdas con la misma fuente que las filas anteriores
            in_item = QTableWidgetItem("00:00:00:00")
            out_item = QTableWidgetItem("00:00:00:00")
            personaje = self.dataframe.at[selected_row, 'PERSONAJE']
            personaje_item = QTableWidgetItem(personaje)

            # Establecer la fuente de los nuevos elementos
            font = QFont("Arial", 12)
            in_item.setFont(font)
            out_item.setFont(font)
            personaje_item.setFont(font)

            self.tableWidget.setItem(selected_row + 1, 0, in_item)
            self.tableWidget.setItem(selected_row + 1, 1, out_item)
            self.tableWidget.setItem(selected_row + 1, 2, personaje_item)

            # Crear el QTextEdit para el diálogo
            new_dialog_widget = QTextEdit(after)
            new_dialog_widget.setStyleSheet("font-size: 16px;")
            new_dialog_widget.setFont(QFont("Arial", 12))
            new_dialog_widget.textChanged.connect(
                self.generate_text_changed_callback(selected_row + 1, 3)
            )
            self.tableWidget.setCellWidget(selected_row + 1, 3, new_dialog_widget)

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
            self.logger.info(f"Intervención separada en la fila {selected_row} en dos filas.")
        except Exception as e:
            self.logger.error(f"Error al separar intervención: {e}")
            QMessageBox.warning(self, "Error", f"Error al separar intervención: {str(e)}")

    def merge_interventions(self):
        """
        Funcionalidad para juntar dos intervenciones consecutivas del mismo personaje en una sola fila.
        Shortcut: Alt+J
        """
        try:
            selected_row = self.tableWidget.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Juntar Intervenciones", "Por favor, selecciona una fila para juntar.")
                return

            if selected_row >= self.tableWidget.rowCount() - 1:
                QMessageBox.warning(self, "Juntar Intervenciones", "No hay una segunda fila para juntar.")
                return

            personaje_current = self.dataframe.at[selected_row, 'PERSONAJE']
            personaje_next = self.dataframe.at[selected_row + 1, 'PERSONAJE']

            if personaje_current != personaje_next:
                QMessageBox.warning(self, "Juntar Intervenciones", "Las filas seleccionadas no tienen el mismo personaje.")
                return

            # Obtener diálogos
            dialog_current_widget = self.tableWidget.cellWidget(selected_row, 3)
            dialog_next_widget = self.tableWidget.cellWidget(selected_row + 1, 3)
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
            self.tableWidget.removeRow(selected_row + 1)
            self.dataframe = self.dataframe.drop(selected_row + 1).reset_index(drop=True)

            self.logger.info(f"Intervenciones de la fila {selected_row} y {selected_row +1} juntadas.")

            QMessageBox.information(self, "Juntar Intervenciones", "Las intervenciones han sido juntadas exitosamente.")
        except Exception as e:
            self.logger.error(f"Error al juntar intervenciones: {e}")
            QMessageBox.warning(self, "Error", f"Error al juntar intervenciones: {str(e)}")

    def update_in_out(self, action, position_ms):
        """
        Actualiza los campos IN y OUT en la tabla basándose en los códigos de tiempo recibidos.
        """
        try:
            if not action or not position_ms:
                self.logger.warning("Datos de in_outSignal incompletos.")
                return

            selected_row = self.tableWidget.currentRow()
            if selected_row == -1:
                self.logger.warning("No hay fila seleccionada para actualizar IN/OUT.")
                QMessageBox.warning(self, "Error", "No hay fila seleccionada para actualizar IN/OUT.")
                return

            if action.upper() == "IN":
                if self.tableWidget.item(selected_row, 0):
                    self.tableWidget.item(selected_row, 0).setText(self.convert_milliseconds_to_time_code(position_ms))
                    self.dataframe.at[selected_row, 'IN'] = self.convert_milliseconds_to_time_code(position_ms)
                    self.logger.debug(f"Actualizado IN en fila {selected_row} a {self.convert_milliseconds_to_time_code(position_ms)}")
            elif action.upper() == "OUT":
                if self.tableWidget.item(selected_row, 1):
                    self.tableWidget.item(selected_row, 1).setText(self.convert_milliseconds_to_time_code(position_ms))
                    self.dataframe.at[selected_row, 'OUT'] = self.convert_milliseconds_to_time_code(position_ms)
                    self.logger.debug(f"Actualizado OUT en fila {selected_row} a {self.convert_milliseconds_to_time_code(position_ms)}")
                self.select_next_row_and_set_in(position_ms)
            else:
                self.logger.warning(f"Tipo de acción inOut desconocido: {action}")
                QMessageBox.warning(self, "Error", f"Tipo de acción inOut desconocido: {action}")
        except Exception as e:
            self.logger.error(f"Error en update_in_out: {e}")
            QMessageBox.warning(self, "Error", f"Error en update_in_out: {str(e)}")

    def select_next_row_and_set_in(self, current_out_ms):
        try:
            next_row = self.tableWidget.currentRow() + 1
            if next_row < self.tableWidget.rowCount():
                self.tableWidget.selectRow(next_row)
                if self.tableWidget.item(next_row, 0):
                    self.tableWidget.item(next_row, 0).setText(self.convert_milliseconds_to_time_code(current_out_ms))
                    self.dataframe.at[next_row, 'IN'] = self.convert_milliseconds_to_time_code(current_out_ms)
                self.adjust_row_height(next_row)
                self.tableWidget.scrollToItem(self.tableWidget.item(next_row, 0), QAbstractItemView.PositionAtCenter)
                self.logger.debug(f"Establecido IN en la fila {next_row} a {self.convert_milliseconds_to_time_code(current_out_ms)}")
        except Exception as e:
            self.logger.error(f"Error al seleccionar la siguiente fila: {e}")

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
            self.logger.error(f"Error al convertir milisegundos a time code: {e}")
            return "00:00:00:00"

    def handle_ctrl_click(self, row):
        """
        Maneja el evento de Ctrl + clic en una fila.
        Emite la señal inOutSignal con la posición en milisegundos.
        """
        try:
            in_time_code = self.dataframe.at[row, 'IN']
            self.logger.debug(f"Ctrl + clic en fila {row}: IN={in_time_code}")
            milliseconds = self.convert_time_code_to_milliseconds(in_time_code)
            self.inOutSignal.emit("IN", milliseconds)
            self.logger.info(f"Video desplazado a {in_time_code} ({milliseconds} ms)")
        except Exception as e:
            self.logger.error(f"Error al manejar Ctrl + clic: {e}")
            QMessageBox.warning(self, "Error", f"Error al desplazar el video: {str(e)}")

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
            self.logger.error(f"Error al convertir time code a milisegundos: {e}")
            raise


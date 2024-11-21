# guion_editor/widgets/find_replace_dialog.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QMessageBox

class FindReplaceDialog(QDialog):
    def __init__(self, table_window):
        super().__init__()
        self.table_window = table_window
        self.setWindowTitle("Buscar y Reemplazar")
        self.current_search_results = []
        self.current_search_index = -1

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.find_text_input = QLineEdit()
        self.replace_text_input = QLineEdit()

        form_layout.addRow("Buscar:", self.find_text_input)
        form_layout.addRow("Reemplazar por:", self.replace_text_input)
        layout.addLayout(form_layout)

        # Botones
        button_layout = QHBoxLayout()
        self.find_prev_button = QPushButton("Buscar Anterior")
        self.find_next_button = QPushButton("Buscar Siguiente")
        self.replace_button = QPushButton("Reemplazar Todo")
        self.close_button = QPushButton("Cerrar")

        button_layout.addWidget(self.find_prev_button)
        button_layout.addWidget(self.find_next_button)
        button_layout.addWidget(self.replace_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        # Conectar señales
        self.find_text_input.textChanged.connect(self.reset_search)
        self.find_next_button.clicked.connect(self.find_next)
        self.find_prev_button.clicked.connect(self.find_previous)
        self.replace_button.clicked.connect(self.replace_all)
        self.close_button.clicked.connect(self.close)

    def perform_search(self):
        search_text = self.find_text_input.text().lower()
        self.current_search_results = []
        if not search_text:
            return
        for row in range(self.table_window.table_widget.rowCount()):
            # Buscar en la columna 'PERSONAJE' (índice 2)
            personaje_item = self.table_window.table_widget.item(row, 2)
            personaje_text = personaje_item.text().lower() if personaje_item else ''
            # Buscar en la columna 'DIÁLOGO' (índice 3)
            dialog_widget = self.table_window.table_widget.cellWidget(row, 3)
            dialog_text = dialog_widget.toPlainText().lower() if dialog_widget else ''
            if search_text in personaje_text or search_text in dialog_text:
                self.current_search_results.append(row)

    def find_next(self):
        search_text = self.find_text_input.text().lower()
        if not search_text:
            QMessageBox.information(self, "Buscar", "Por favor, ingrese el texto a buscar.")
            return
        if not self.current_search_results:
            self.perform_search()
        if not self.current_search_results:
            QMessageBox.information(self, "Buscar", "No se encontraron coincidencias.")
            return
        self.current_search_index = (self.current_search_index + 1) % len(self.current_search_results)
        self.select_search_result()

    def find_previous(self):
        search_text = self.find_text_input.text().lower()
        if not search_text:
            QMessageBox.information(self, "Buscar", "Por favor, ingrese el texto a buscar.")
            return
        if not self.current_search_results:
            self.perform_search()
        if not self.current_search_results:
            QMessageBox.information(self, "Buscar", "No se encontraron coincidencias.")
            return
        self.current_search_index = (self.current_search_index - 1) % len(self.current_search_results)
        self.select_search_result()

    def select_search_result(self):
        row = self.current_search_results[self.current_search_index]
        self.table_window.table_widget.selectRow(row)
        self.table_window.table_widget.scrollToItem(self.table_window.table_widget.item(row, 0))
        # Opcionalmente, puedes resaltar el texto encontrado

    def reset_search(self):
        self.current_search_results = []
        self.current_search_index = -1

    def replace_all(self):
        find_text = self.find_text_input.text()
        replace_text = self.replace_text_input.text()
        if not find_text:
            QMessageBox.information(self, "Reemplazar", "Por favor, ingrese el texto a buscar.")
            return
        self.table_window.find_and_replace(find_text, replace_text)

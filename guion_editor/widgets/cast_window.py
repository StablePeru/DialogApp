# guion_editor/widgets/cast_window.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt

class CastWindow(QWidget):
    def __init__(self, parent_table_window):
        super().__init__()
        self.parent_table_window = parent_table_window
        self.setWindowTitle("Reparto Completo")
        self.setGeometry(200, 200, 400, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Personaje", "Intervenciones"])
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_widget)
        self.setLayout(layout)
        self.populate_table()

    def populate_table(self):
        character_counts = self.parent_table_window.dataframe['PERSONAJE'].value_counts()
        self.table_widget.setRowCount(len(character_counts))
        for row, (character, count) in enumerate(character_counts.items()):
            character_item = QTableWidgetItem(character)
            interventions_item = QTableWidgetItem(str(count))
            self.table_widget.setItem(row, 0, character_item)
            self.table_widget.setItem(row, 1, interventions_item)
        self.table_widget.itemChanged.connect(self.on_item_changed)

    def on_item_changed(self, item):
        if item.column() == 0:
            old_name = item.data(Qt.UserRole)
            new_name = item.text()
            if old_name != new_name:
                self.parent_table_window.update_character_name(old_name, new_name)
                item.setData(Qt.UserRole, new_name)
                QMessageBox.information(self, "Nombre Actualizado", f"'{old_name}' ha sido cambiado a '{new_name}'.")

    def showEvent(self, event):
        super().showEvent(event)
        self.populate_table()

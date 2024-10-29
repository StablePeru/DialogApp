# guion_editor/widgets/custom_table_widget.py

from PyQt5.QtWidgets import QTableWidget, QApplication
from PyQt5.QtCore import pyqtSignal, Qt


class CustomTableWidget(QTableWidget):
    cellCtrlClicked = pyqtSignal(int)  # Emite la fila clicada

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and QApplication.keyboardModifiers() == Qt.ControlModifier:
            index = self.indexAt(event.pos())
            if index.isValid():
                self.cellCtrlClicked.emit(index.row())
        super().mousePressEvent(event)

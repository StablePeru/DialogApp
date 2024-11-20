# guion_editor/widgets/custom_table_widget.py

from PyQt5.QtWidgets import QTableWidget, QApplication
from PyQt5.QtCore import pyqtSignal, Qt


class CustomTableWidget(QTableWidget):
    cellCtrlClicked = pyqtSignal(int)  # Emite la fila clicada
    cellAltClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                if modifiers == Qt.ControlModifier:
                    self.cellCtrlClicked.emit(index.row())
                    event.accept()
                elif modifiers == Qt.AltModifier:
                    self.cellAltClicked.emit(index.row())  # Emitir señal para Alt + Click
                    event.accept()
                else:
                    super().mousePressEvent(event)
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

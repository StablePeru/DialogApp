# guion_editor/widgets/custom_text_edit.py

from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import pyqtSignal, Qt

class CustomTextEdit(QTextEdit):
    # Señal personalizada que emite el texto final cuando se pierde el foco
    editingFinished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        # Emitir la señal con el texto actual cuando se pierde el foco
        self.editingFinished.emit(self.toPlainText())

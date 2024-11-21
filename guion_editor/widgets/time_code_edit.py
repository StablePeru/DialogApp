# guion_editor/widgets/time_code_edit.py

from PyQt5.QtWidgets import QLineEdit, QMessageBox
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QFont, QKeyEvent

class TimeCodeEdit(QLineEdit):
    def __init__(self, parent=None, initial_time_code="00:00:00:00"):
        super().__init__(parent)
        self.setFixedWidth(120)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Arial", 12))
        self.setStyleSheet("font-size: 16px;")
        self.setMaxLength(11)
        self.setReadOnly(False)  # Permitir edición
        self.setText(initial_time_code)
        
        # Inicializar los dígitos como una lista de enteros
        self.digits = [int(c) for c in initial_time_code if c.isdigit()]
        if len(self.digits) != 8:
            self.digits = [0] * 8
            self.update_display()

    def keyPressEvent(self, event: QKeyEvent):
        """
        Maneja los eventos de teclas para permitir la inserción controlada de dígitos.
        Solo permite la inserción de dígitos numéricos.
        """
        if event.text().isdigit():
            new_digit = int(event.text())
            self.shift_digits_left(new_digit)
            self.update_display()
            self.textChanged.emit(self.text())
        elif event.key() in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
            # Opcional: manejar navegación si es necesario
            super().keyPressEvent(event)
        else:
            # Ignorar cualquier otra tecla
            event.ignore()

    def insertFromMimeData(self, source: QMimeData):
        """
        Maneja la inserción de múltiples dígitos, como al pegar una cadena de números.
        Procesa cada dígito individualmente, desplazando los existentes hacia la izquierda.
        """
        text = source.text()
        for char in text:
            if char.isdigit():
                new_digit = int(char)
                self.shift_digits_left(new_digit)
        self.update_display()
        self.textChanged.emit(self.text())

    def shift_digits_left(self, new_digit: int):
        """
        Desplaza los dígitos hacia la izquierda y agrega un nuevo dígito al final.
        """
        self.digits.pop(0)        # Eliminar el primer dígito
        self.digits.append(new_digit)  # Agregar el nuevo dígito al final

    def update_display(self):
        """
        Actualiza la visualización del código de tiempo en el formato HH:MM:SS:FF.
        Aplica validaciones de rangos para cada segmento.
        """
        hours = self.digits[0] * 10 + self.digits[1]
        minutes = self.digits[2] * 10 + self.digits[3]
        seconds = self.digits[4] * 10 + self.digits[5]
        frames = self.digits[6] * 10 + self.digits[7]

        formatted = "{:02}:{:02}:{:02}:{:02}".format(hours, minutes, seconds, frames)
        self.blockSignals(True)  # Evitar emitir señales mientras se actualiza el texto
        self.setText(formatted)
        self.blockSignals(False)

    def set_time_code(self, time_code: str):
        """
        Establece un nuevo código de tiempo, asegurándose de que tenga el formato correcto.
        """
        try:
            parts = time_code.split(':')
            if len(parts) != 4:
                raise ValueError
            self.digits = [
                int(parts[0][0]), int(parts[0][1]),
                int(parts[1][0]), int(parts[1][1]),
                int(parts[2][0]), int(parts[2][1]),
                int(parts[3][0]), int(parts[3][1]),
            ]
            self.update_display()
        except:
            QMessageBox.warning(self, "Error", "Formato de Time Code inválido.")

    def get_time_code(self) -> str:
        """
        Devuelve el valor actual del código de tiempo en formato HH:MM:SS:FF.
        """
        return self.text()

    def mousePressEvent(self, event):
        """
        Maneja los eventos de ratón para evitar que el usuario mueva el cursor.
        Siempre mantiene el cursor al final.
        """
        super().mousePressEvent(event)
        self.setCursorPosition(len(self.text()))  # Mover el cursor al final

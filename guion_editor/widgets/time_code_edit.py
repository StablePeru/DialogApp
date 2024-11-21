# guion_editor/widgets/time_code_edit.py

from PyQt5.QtWidgets import QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class TimeCodeEdit(QLineEdit):
    def __init__(self, parent=None, initial_time_code="00:00:00:00"):
        super().__init__(parent)
        self.setFixedWidth(120)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Arial", 12))
        self.setStyleSheet("font-size: 16px;")
        self.setMaxLength(11)
        self.setText(initial_time_code)
        self.digits = [int(c) for c in initial_time_code if c.isdigit()]
        if len(self.digits) != 8:
            self.digits = [0]*8
            self.update_display()
        self.setReadOnly(False)  # Permitir edición
        self.insert_pos = 7  # Posición inicial para insertar desde la derecha

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
            # Ignorar acciones de navegación y edición estándar
            event.ignore()
            return
        elif event.text().isdigit():
            new_digit = int(event.text())
            # Reemplazar el dígito en la posición actual de inserción
            if 0 <= self.insert_pos < 8:
                self.digits[self.insert_pos] = new_digit
                self.update_display()
                self.textChanged.emit(self.text())
                # Mover la posición de inserción hacia la izquierda
                if self.insert_pos > 0:
                    self.insert_pos -= 1
            # Si insert_pos es menor que 0, no hacer nada
        else:
            # Ignorar cualquier otro carácter
            event.ignore()

    def update_display(self):
        formatted = "{:02}:{:02}:{:02}:{:02}".format(
            self.digits[0]*10 + self.digits[1],
            self.digits[2]*10 + self.digits[3],
            self.digits[4]*10 + self.digits[5],
            self.digits[6]*10 + self.digits[7]
        )
        self.blockSignals(True)  # Evitar emitir señales mientras se actualiza el texto
        self.setText(formatted)
        self.blockSignals(False)

    def set_time_code(self, time_code):
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
            self.insert_pos = 7  # Reiniciar la posición de inserción
        except:
            QMessageBox.warning(self, "Error", "Formato de Time Code inválido.")

    def get_time_code(self):
        return self.text()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Reiniciar la posición de inserción al hacer clic (independientemente de la posición)
        self.insert_pos = 7

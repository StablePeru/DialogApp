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
        self.setReadOnly(True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
            event.ignore()
            return
        elif event.text().isdigit():
            new_digit = int(event.text())
            self.digits.pop(0)
            self.digits.append(new_digit)
            self.update_display()
            self.textChanged.emit(self.text())
        else:
            event.ignore()

    def update_display(self):
        formatted = "{:02}:{:02}:{:02}:{:02}".format(
            self.digits[0]*10 + self.digits[1],
            self.digits[2]*10 + self.digits[3],
            self.digits[4]*10 + self.digits[5],
            self.digits[6]*10 + self.digits[7]
        )
        self.setText(formatted)

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
        except:
            QMessageBox.warning(self, "Error", "Formato de Time Code inválido.")

    def get_time_code(self):
        return self.text()

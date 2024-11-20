# guion_editor/widgets/find_replace_dialog.py

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class FindReplaceDialog(QDialog):
    def __init__(self, table_window):
        super().__init__()
        self.table_window = table_window
        self.setWindowTitle("Buscar y Reemplazar")
        self.setFixedSize(400, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        find_layout = QHBoxLayout()
        find_label = QLabel("Buscar:")
        self.find_input = QLineEdit()
        find_layout.addWidget(find_label)
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_label = QLabel("Reemplazar con:")
        self.replace_input = QLineEdit()
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        buttons_layout = QHBoxLayout()
        self.replace_all_button = QPushButton("Reemplazar Todo")
        self.replace_all_button.clicked.connect(self.replace_all)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.replace_all_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def replace_all(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not find_text:
            return

        self.table_window.find_and_replace(find_text, replace_text)
        self.accept()

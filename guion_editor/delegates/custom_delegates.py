# guion_editor/delegates/custom_delegates.py

from PyQt5.QtWidgets import QStyledItemDelegate, QLineEdit, QMessageBox
from PyQt5.QtCore import Qt
from guion_editor.widgets.time_code_edit import TimeCodeEdit

class TimeCodeDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = TimeCodeEdit(parent)
        return editor

    def setEditorData(self, editor, index):
        time_code = index.model().data(index, Qt.EditRole)
        editor.set_time_code(time_code)

    def setModelData(self, editor, model, index):
        time_code = editor.get_time_code()
        model.setData(index, time_code, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)

class CharacterDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.EditRole)
        editor.setText(text)

    def setModelData(self, editor, model, index):
        text = editor.text().strip()
        if not text:
            QMessageBox.warning(editor, "Entrada Inválida", "El nombre del personaje no puede estar vacío.")
            return
        model.setData(index, text, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
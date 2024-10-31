# guion_editor/widgets/shortcut_config_dialog.py
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QInputDialog, QKeySequenceEdit
)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class ShortcutConfigDialog(QDialog):
    def __init__(self, shortcut_manager):
        super().__init__()
        logger.debug("Inicializando ShortcutConfigDialog.")
        self.shortcut_manager = shortcut_manager
        self.setWindowTitle("Configurar Shortcuts")
        self.setMinimumSize(600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Label de instrucciones
        layout.addWidget(QLabel("Seleccione una acción para cambiar su shortcut:"))

        # Tabla para mostrar acciones y shortcuts
        self.action_table = QTableWidget()
        self.action_table.setColumnCount(2)
        self.action_table.setHorizontalHeaderLabels(["Acción", "Shortcut"])
        self.action_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Evitar edición directa
        self.action_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.action_table.setSelectionMode(QTableWidget.SingleSelection)
        self.action_table.horizontalHeader().setStretchLastSection(True)

        # Rellenar la tabla con acciones y shortcuts
        self.populate_table()

        layout.addWidget(self.action_table)

        # Label para el nuevo shortcut
        layout.addWidget(QLabel("Presione las teclas para asignar el nuevo shortcut:"))

        # Widget para editar la secuencia de teclas
        self.shortcut_edit = QKeySequenceEdit()
        self.shortcut_edit.setKeySequence(QKeySequence())  # Inicializar vacío
        self.shortcut_edit.keySequenceChanged.connect(self.on_key_sequence_changed)
        layout.addWidget(self.shortcut_edit)

        # Botones
        btn_layout = QHBoxLayout()
        self.assign_btn = QPushButton("Asignar")
        self.assign_btn.setEnabled(False)  # Deshabilitado hasta que se ingrese un shortcut válido
        self.assign_btn.clicked.connect(self.assign_shortcut)
        btn_layout.addWidget(self.assign_btn)

        self.save_config_btn = QPushButton("Guardar Configuración")
        self.save_config_btn.clicked.connect(self.save_configuration)
        btn_layout.addWidget(self.save_config_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # Variables para almacenar la acción seleccionada y el shortcut
        self.selected_action_internal = None
        self.new_shortcut = ""

        # Conectar señal de selección de la tabla
        self.action_table.itemSelectionChanged.connect(self.on_action_selected)

    def populate_table(self):
        logger.debug("Populando la tabla de acciones y shortcuts.")
        actions = self.shortcut_manager.main_window.actions
        self.action_table.setRowCount(len(actions))
        for row, (action_name, action) in enumerate(actions.items()):
            # Mantener el carácter '&' en los nombres de las acciones
            display_name = action_name
            shortcut = action.shortcut().toString()

            action_item = QTableWidgetItem(display_name)
            shortcut_item = QTableWidgetItem(shortcut if shortcut else "")

            # Almacenar el nombre original de la acción en UserRole
            action_item.setData(Qt.UserRole, action_name)

            self.action_table.setItem(row, 0, action_item)
            self.action_table.setItem(row, 1, shortcut_item)

    def on_action_selected(self):
        selected_items = self.action_table.selectedItems()
        if selected_items:
            action_item = selected_items[0]
            shortcut_item = selected_items[1]
            display_name = action_item.text()
            shortcut = shortcut_item.text()
            self.selected_action_internal = action_item.data(Qt.UserRole)
            self.shortcut_edit.setKeySequence(QKeySequence(shortcut))
            self.new_shortcut = shortcut
            self.assign_btn.setEnabled(bool(shortcut))
            logger.debug(f"Acción seleccionada: '{display_name}' con shortcut '{shortcut}'.")
        else:
            self.selected_action_internal = None
            self.shortcut_edit.setKeySequence(QKeySequence())
            self.new_shortcut = ""
            self.assign_btn.setEnabled(False)

    def on_key_sequence_changed(self, key_seq):
        logger.debug(f"Secuencia de teclas cambiada: {key_seq.toString(QKeySequence.NativeText)}")
        if key_seq.isEmpty():
            self.assign_btn.setEnabled(False)
            self.new_shortcut = ""
        else:
            self.assign_btn.setEnabled(True)
            self.new_shortcut = key_seq.toString(QKeySequence.NativeText)

    def assign_shortcut(self):
        logger.debug("Intentando asignar un nuevo shortcut.")
        if not self.selected_action_internal:
            QMessageBox.warning(self, "Advertencia", "Seleccione una acción primero.")
            logger.warning("No se seleccionó ninguna acción antes de intentar asignar un shortcut.")
            return
        if not self.new_shortcut:
            QMessageBox.warning(self, "Advertencia", "Ingrese un shortcut válido.")
            logger.warning("No se ingresó un shortcut válido antes de intentar asignar.")
            return

        # Validar si el shortcut ya está en uso
        for action_name, shortcut in self.shortcut_manager.configurations[self.shortcut_manager.current_config].items():
            if shortcut == self.new_shortcut and action_name != self.selected_action_internal:
                # Mostrar el nombre de la acción sin &
                display_conflict_action = action_name.replace("&", "")
                QMessageBox.warning(
                    self,
                    "Advertencia",
                    f"El shortcut '{self.new_shortcut}' ya está asignado a '{display_conflict_action}'."
                )
                logger.warning(f"Conflicto de shortcut: '{self.new_shortcut}' ya está asignado a '{display_conflict_action}'.")
                return

        # Asignar el shortcut a la acción
        action = self.shortcut_manager.main_window.actions.get(self.selected_action_internal)
        if action:
            try:
                # Validar el QKeySequence
                key_seq = QKeySequence(self.new_shortcut)
                if key_seq.isEmpty():
                    raise ValueError(f"Shortcut '{self.new_shortcut}' es inválido.")

                action.setShortcut(key_seq)
                # Actualizar en la configuración actual
                self.shortcut_manager.configurations[self.shortcut_manager.current_config][self.selected_action_internal] = self.new_shortcut
                self.shortcut_manager.save_shortcuts()
                QMessageBox.information(self, "Éxito", f"Shortcut asignado a '{self.selected_action_internal.replace('&', '')}'.")
                logger.info(f"Shortcut '{self.new_shortcut}' asignado a la acción '{self.selected_action_internal}'.")
                self.new_shortcut = ""
                self.shortcut_edit.setKeySequence(QKeySequence())
                self.assign_btn.setEnabled(False)
                # Actualizar la tabla para reflejar el cambio
                self.populate_table()
            except Exception as e:
                logger.error(f"Error al asignar shortcut: {e}")
                QMessageBox.warning(self, "Error", f"Error al asignar shortcut: {str(e)}")
        else:
            QMessageBox.warning(self, "Error", f"Acción '{self.selected_action_internal}' no encontrada.")
            logger.error(f"Acción '{self.selected_action_internal}' no encontrada durante la asignación de shortcut.")

    def save_configuration(self):
        logger.debug("Intentando guardar una nueva configuración de shortcuts.")
        name, ok = QInputDialog.getText(self, "Guardar Configuración", "Ingrese el nombre para la configuración:")
        if ok and name:
            if name in self.shortcut_manager.configurations:
                overwrite = QMessageBox.question(
                    self, "Confirmar",
                    f"Ya existe una configuración llamada '{name}'. ¿Desea sobrescribirla?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if overwrite == QMessageBox.No:
                    logger.info(f"Usuario canceló la sobrescritura de la configuración '{name}'.")
                    return
            # Copiar la configuración actual
            current_shortcuts = self.shortcut_manager.configurations[self.shortcut_manager.current_config].copy()
            self.shortcut_manager.configurations[name] = current_shortcuts
            self.shortcut_manager.save_shortcuts()
            QMessageBox.information(self, "Éxito", f"Configuración '{name}' guardada exitosamente.")
            logger.info(f"Configuración '{name}' guardada exitosamente.")

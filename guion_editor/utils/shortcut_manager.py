# guion_editor/utils/shortcut_manager.py
# -*- coding: utf-8 -*-

import json
import os
from PyQt5.QtWidgets import QMessageBox, QShortcut
from PyQt5.QtGui import QKeySequence
import logging

logger = logging.getLogger(__name__)

# Ruta relativa correcta a shortcuts.json
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../shortcuts.json'))

class ShortcutManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.configurations = {}
        self.current_config = 'default'
        self.shortcuts = {}  # Inicializar el diccionario para almacenar los atajos
        logger.debug("Inicializando ShortcutManager.")
        self.load_shortcuts()

    def load_shortcuts(self):
        logger.debug(f"Intentando cargar shortcuts desde {CONFIG_FILE}.")
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_config = data.get("current_config", "default")
                    self.configurations = data.get("configs", {})
                logger.debug(f"Shortcuts cargados: {self.configurations}")
            except Exception as e:
                logger.error(f"Error al cargar shortcuts desde {CONFIG_FILE}: {e}")
                QMessageBox.warning(self.main_window, "Error", f"Error al cargar shortcuts: {str(e)}")
                self.configurations = {}
        else:
            # Configuración predeterminada con nombres internos (con &)
            self.configurations = {
                "default": {
                    "&Abrir Video": "Ctrl+O",
                    "&Abrir Guion": "Ctrl+G",
                    "&Exportar Guion a Excel": "Ctrl+E",
                    "&Importar Guion desde Excel": "Ctrl+I",
                    "&Guardar Guion como JSON": "Ctrl+S",
                    "&Cargar Guion desde JSON": "Ctrl+D",
                    "&Agregar Línea": "Ctrl+N",
                    "&Eliminar Fila": "Ctrl+Del",
                    "Mover &Arriba": "Alt+Up",
                    "Mover &Abajo": "Alt+Down",
                    "&Separar Intervención": "Alt+I",
                    "&Juntar Intervenciones": "Alt+J",
                    "&Configuración": "Ctrl+K",
                    "Pausar/Reproducir": "Ctrl+Up",
                    "Retroceder": "Ctrl+Left",
                    "Avanzar": "Ctrl+Right",
                    "Copiar IN/OUT a Siguiente": "Ctrl+B",
                    "change_scene": "Ctrl+R"
                }
            }
            self.current_config = "default"
            self.save_shortcuts()
            logger.debug(f"Configuración predeterminada guardada en {CONFIG_FILE}.")

        self.apply_shortcuts(self.current_config)

    def save_shortcuts(self):
        logger.debug(f"Guardando shortcuts en {CONFIG_FILE}.")
        data = {
            "current_config": self.current_config,
            "configs": self.configurations
        }
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.debug("Shortcuts guardados correctamente.")
        except Exception as e:
            logger.error(f"Error al guardar shortcuts en {CONFIG_FILE}: {e}")
            QMessageBox.warning(self.main_window, "Error", f"Error al guardar shortcuts: {str(e)}")

    def apply_shortcuts(self, config_name):
        logger.debug(f"Aplicando configuración de shortcuts: '{config_name}'.")
        if config_name not in self.configurations:
            logger.warning(f"Configuración '{config_name}' no encontrada.")
            return
        self.current_config = config_name
        shortcuts = self.configurations[config_name]
        for action_name, shortcut in shortcuts.items():
            action = self.main_window.actions.get(action_name)
            if action:
                try:
                    action.setShortcut(QKeySequence(shortcut))
                    logger.debug(f"Shortcut '{shortcut}' asignado a la acción '{action_name}'.")
                except Exception as e:
                    logger.error(f"Error al asignar shortcut '{shortcut}' a la acción '{action_name}': {e}")
            elif action_name == "change_scene":
                # Crear un QShortcut para "change_scene" y conectarlo
                shortcut_obj = QShortcut(QKeySequence(shortcut), self.main_window)
                shortcut_obj.activated.connect(self.main_window.change_scene)
                self.shortcuts[action_name] = shortcut_obj
                logger.debug(f"Shortcut '{shortcut}' asignado a la acción '{action_name}'.")
            else:
                logger.warning(f"Acción '{action_name}' no existe.")

    def get_available_configs(self):
        logger.debug("Obteniendo configuraciones disponibles.")
        return list(self.configurations.keys())

    def add_configuration(self, name, shortcuts):
        if name in self.configurations:
            QMessageBox.warning(self.main_window, "Error", f"Ya existe una configuración con el nombre '{name}'.")
            logger.warning(f"Intento de añadir una configuración duplicada: '{name}'.")
            return False
        self.configurations[name] = shortcuts
        self.save_shortcuts()
        logger.info(f"Configuración '{name}' añadida.")
        return True

    def delete_configuration(self, name):
        if name == "default":
            QMessageBox.warning(self.main_window, "Error", "No se puede eliminar la configuración 'default'.")
            logger.warning("Intento de eliminar la configuración 'default'.")
            return False
        if name in self.configurations:
            del self.configurations[name]
            self.save_shortcuts()
            logger.info(f"Configuración '{name}' eliminada.")
            return True
        QMessageBox.warning(self.main_window, "Error", f"Configuración '{name}' no encontrada.")
        logger.warning(f"Intento de eliminar una configuración inexistente: '{name}'.")
        return False

    def update_configuration(self, name, shortcuts):
        if name not in self.configurations:
            QMessageBox.warning(self.main_window, "Error", f"Configuración '{name}' no encontrada.")
            logger.warning(f"Intento de actualizar una configuración inexistente: '{name}'.")
            return False
        self.configurations[name] = shortcuts
        self.save_shortcuts()
        logger.info(f"Configuración '{name}' actualizada.")
        return True

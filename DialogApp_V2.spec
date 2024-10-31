# DialogApp_V2.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os

project_dir = os.path.abspath('.')

# Recopila todos los submódulos de 'guion_editor'
hidden_imports = collect_submodules('guion_editor') + [
    'guion_editor.widgets.video_player_widget',
    'guion_editor.widgets.video_window',
    'guion_editor.widgets.table_window',
    'guion_editor.widgets.config_dialog',
    'guion_editor.widgets.custom_table_widget',
    'guion_editor.widgets.shortcut_config_dialog',
    'guion_editor.delegates.custom_delegates',
    'guion_editor.utils.dialog_utils',
    'guion_editor.utils.guion_manager',
    'guion_editor.utils.shortcut_manager',
    'openpyxl',  # Añadir openpyxl aquí
]

# Recopila todos los archivos de datos dentro de 'guion_editor'
datas = collect_data_files('guion_editor')

# Añade otros archivos de datos necesarios
datas += [
    ('shortcuts.json', '.'),          # Copia shortcuts.json al directorio raíz del ejecutable
    ('guion_editor/styles/*.css', 'guion_editor/styles'),  # Incluye todos los archivos CSS
]

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
    
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
    
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DialogApp_V2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False para GUI, True para consola
)
    
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DialogApp_V2',
)

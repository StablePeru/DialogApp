# guion_editor/utils/dialog_utils.py

import re
from docx import Document
import warnings

def ajustar_dialogo(dialogo):
    palabras = dialogo.split()
    linea_actual = ""
    lineas_ajustadas = []

    for palabra in palabras:
        test_linea = linea_actual + (" " if linea_actual else "") + palabra
        if contar_caracteres(test_linea) > 60:
            lineas_ajustadas.append(linea_actual)
            linea_actual = palabra
        else:
            linea_actual = test_linea

    if linea_actual:
        lineas_ajustadas.append(linea_actual)

    return "\n".join(lineas_ajustadas)

def contar_caracteres(dialogo):
    dialogo_limpio = re.sub(r'\([^)]*\)', '', dialogo)
    return len(dialogo_limpio)

def leer_guion(docx_file):
    try:
        doc = Document(docx_file)
        guion = []
        personaje_actual = None

        # Lista de encabezados comunes que queremos filtrar
        encabezados_excluir = ["NUMB CHUCKS 1A"]

        for para in doc.paragraphs:
            texto = para.text.strip()
            if texto:
                # Filtrar encabezados
                if texto.isupper() and texto not in encabezados_excluir and len(texto.split()) <= 5:
                    personaje_actual = texto
                elif personaje_actual:
                    dialogo_ajustado = ajustar_dialogo(texto)
                    guion.append({
                        'IN': '00:00:00:00',
                        'OUT': '00:00:00:00',
                        'PERSONAJE': personaje_actual,
                        'DIÁLOGO': dialogo_ajustado
                    })
                    # No reiniciar personaje_actual aquí, en caso de que haya más líneas del mismo personaje
        return guion
    except Exception as e:
        warnings.warn(f"Error en leer_guion: {e}", PendingDeprecationWarning)


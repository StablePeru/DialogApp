# guion_editor/utils/guion_manager.py

import pandas as pd
import json
from typing import List, Dict


class GuionManager:
    REQUIRED_COLUMNS = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']

    def __init__(self):
        self.dataframe = pd.DataFrame(columns=self.REQUIRED_COLUMNS)

    def load_from_excel(self, path: str) -> pd.DataFrame:
        """
        Carga datos desde un archivo Excel.

        Args:
            path (str): Ruta al archivo Excel.

        Returns:
            pd.DataFrame: DataFrame cargado.

        Raises:
            ValueError: Si faltan columnas requeridas.
        """
        df = pd.read_excel(path)
        if not self.validate_columns(df):
            raise ValueError("Faltan columnas requeridas en los datos.")
        self.dataframe = df
        return self.dataframe

    def save_to_excel(self, path: str) -> None:
        """
        Guarda los datos actuales en un archivo Excel.

        Args:
            path (str): Ruta donde guardar el archivo Excel.
        """
        self.dataframe.to_excel(path, index=False)

    def load_from_json(self, path: str) -> pd.DataFrame:
        """
        Carga datos desde un archivo JSON.

        Args:
            path (str): Ruta al archivo JSON.

        Returns:
            pd.DataFrame: DataFrame cargado.

        Raises:
            ValueError: Si faltan columnas requeridas.
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if not self.validate_columns(df):
            raise ValueError("Faltan columnas requeridas en los datos.")
        self.dataframe = df
        return self.dataframe

    def save_to_json(self, path: str) -> None:
        """
        Guarda los datos actuales en un archivo JSON.

        Args:
            path (str): Ruta donde guardar el archivo JSON.
        """
        data = self.dataframe.to_dict(orient='records')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def validate_columns(self, df: pd.DataFrame) -> bool:
        """
        Valida que el DataFrame contenga todas las columnas requeridas.

        Args:
            df (pd.DataFrame): DataFrame a validar.

        Returns:
            bool: True si contiene todas las columnas, False de lo contrario.
        """
        return all(col in df.columns for col in self.REQUIRED_COLUMNS)

    def load_from_docx(self, docx_file: str, leer_guion_func) -> pd.DataFrame:
        """
        Carga datos desde un archivo DOCX usando una función proporcionada.

        Args:
            docx_file (str): Ruta al archivo DOCX.
            leer_guion_func (callable): Función para leer el guion.

        Returns:
            pd.DataFrame: DataFrame cargado.

        Raises:
            ValueError: Si faltan columnas requeridas.
        """
        guion_data = leer_guion_func(docx_file)
        df = pd.DataFrame(guion_data)
        if not self.validate_columns(df):
            raise ValueError("Faltan columnas requeridas en los datos.")
        self.dataframe = df
        return self.dataframe

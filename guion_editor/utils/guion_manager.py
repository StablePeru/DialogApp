# guion_editor/utils/guion_manager.py

import pandas as pd
import json

class GuionManager:
    REQUIRED_COLUMNS = ['IN', 'OUT', 'PERSONAJE', 'DIÁLOGO']

    def __init__(self):
        self.dataframe = pd.DataFrame(columns=self.REQUIRED_COLUMNS)

    def load_from_excel(self, path: str) -> pd.DataFrame:
        df = pd.read_excel(path)
        if not self.validate_columns(df):
            raise ValueError("Faltan columnas requeridas en los datos.")
        # Añadir la columna "Escena" si no existe
        if "Escena" not in df.columns:
            df.insert(0, "Escena", 1)
        self.dataframe = df
        return self.dataframe

    def save_to_excel(self, path: str) -> None:
        self.dataframe.to_excel(path, index=False)

    def load_from_json(self, path: str) -> pd.DataFrame:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if not self.validate_columns(df):
            raise ValueError("Faltan columnas requeridas en los datos.")
        if "Escena" not in df.columns:
            df.insert(0, "Escena", 1)
        self.dataframe = df
        return self.dataframe

    def save_to_json(self, path: str) -> None:
        data = self.dataframe.to_dict(orient='records')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def validate_columns(self, df: pd.DataFrame) -> bool:
        return all(col in df.columns for col in self.REQUIRED_COLUMNS)

    def load_from_docx(self, docx_file: str, leer_guion_func) -> pd.DataFrame:
        guion_data = leer_guion_func(docx_file)
        df = pd.DataFrame(guion_data)
        if not self.validate_columns(df):
            raise ValueError("Faltan columnas requeridas en los datos.")
        if "Escena" not in df.columns:
            df.insert(0, "Escena", 1)
        self.dataframe = df
        return self.dataframe

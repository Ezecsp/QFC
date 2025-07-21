from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    Clase base abstracta para todas las estrategias de trading.
    Define la interfaz que todas las estrategias deben implementar,
    asegurando que el AnalystAgent pueda trabajar con ellas de forma consistente.
    """
    def __init__(self, config: dict):
        """
        Inicializa la estrategia con su configuración específica.
        
        Args:
            config (dict): Un diccionario que contiene los parámetros
                           necesarios para esta estrategia.
        """
        self.config = config

    @abstractmethod
    def analyze(self, data: pd.DataFrame, pair: str) -> pd.DataFrame: # <-- Añadir pair: str
        """
        Método principal que aplica la lógica de la estrategia.
        Debe ser implementado por cada estrategia hija.

        Args:
            data (pd.DataFrame): DataFrame con los datos históricos del mercado.

        Returns:
            pd.DataFrame: El DataFrame original enriquecido con las 
                          columnas de análisis de la estrategia (indicadores, señales, etc.).
        """
        pass
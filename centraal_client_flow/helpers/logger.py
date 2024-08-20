"""Utilidades para logger."""

# pylint: disable=too-few-public-methods
import logging
from typing import Optional


class LoggerMixin:
    """Clase base abstracta para proveer funcionalidad de logging."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Inicializa la clase base con un logger opcional.

        Parameters:
            logger: Instancia de logging.Logger para registrar eventos.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

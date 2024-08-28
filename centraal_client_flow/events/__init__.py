"""Codigo compartido por los submodulos."""

from abc import ABC, abstractmethod
from typing import List

from centraal_client_flow.helpers.logger import LoggerMixin
from centraal_client_flow.models.schemas import BaseModel, EventoBase


class EventProcessor(LoggerMixin, ABC):
    """Clase base abstracta para procesadores de eventos."""

    @abstractmethod
    def process_event(self, event: BaseModel) -> EventoBase:
        """
        Procesa el evento recibido. y retorna el modelo de EventoBase

        Parameters:
            event: Objeto que corresponde a modelo pydantic.
        """


class PullProcessor(LoggerMixin, ABC):
    """Clase base abstracta para procesadores de eventos."""

    @abstractmethod
    def get_data(self) -> List[BaseModel]:
        """
        Obtiene la informacion
        """

    @abstractmethod
    def process_event(self, event_data: BaseModel) -> EventoBase:
        """
        Procesa el evento recibido. y retorna el modelo de EventoBase

        Parameters:
            event_data: Objeto que corresponde a modelo pydantic.
        """

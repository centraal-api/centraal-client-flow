"""Codigo compartido por los submodulos."""

from typing import List
from abc import ABC, abstractmethod

from centraal_client_flow.models.schemas import EventoBase, BaseModel


class EventProcessor(ABC):
    """Clase base abstracta para procesadores de eventos."""

    @abstractmethod
    def process_event(self, event: BaseModel) -> EventoBase:
        """
        Procesa el evento recibido. y retorna el modelo de EventoBase

        Parameters:
            event: Objeto que corresponde a modelo pydantic.
        """


class PullProcessor(ABC):
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
            event: Objeto que corresponde a modelo pydantic.
        """

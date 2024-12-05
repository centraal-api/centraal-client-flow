"""Definicion de clase EventProcessor."""

from abc import ABC, abstractmethod
from typing import Any, List, Union
from pydantic import ValidationError


from centraal_client_flow.models.schemas import EventoBase

"""
TODO:
implementar unsado estas ideas:

# centraal_client_flow/connections/ibus_service_bus_client.py

from abc import ABC, abstractmethod
from typing import List
from azure.servicebus import ServiceBusMessage

class IBServiceBusClient(ABC):
    @abstractmethod
    async def get_sender(self, queue_name: str):
        pass

    @abstractmethod
    async def send_messages(self, sender, messages: List[ServiceBusMessage]):
        pass

    @abstractmethod
    async def close(self):
        pass
        

        # centraal_client_flow/connections/service_bus.py

from centra_client_flow.connections.ibus_service_bus_client import IBServiceBusClient
from azure.servicebus.aio import ServiceBusClient, ServiceBusSender
from azure.servicebus import ServiceBusMessage
import json

class ServiceBusClientSingleton(IBServiceBusClient):
    _instance = None

    def __new__(cls, connection_str: str):
        if cls._instance is None:
            cls._instance = super(ServiceBusClientSingleton, cls).__new__(cls)
            cls._instance.connection_str = connection_str
            cls._instance.client = ServiceBusClient.from_connection_string(connection_str)
            cls._instance.senders = {}
        return cls._instance

    async def get_sender(self, queue_name: str) -> ServiceBusSender:
        if queue_name not in self.senders and self.client:
            self.senders[queue_name] = self.client.get_queue_sender(queue_name)
        return self.senders[queue_name]

    async def send_messages(self, sender, messages: List[ServiceBusMessage]):
        await sender.send_messages(messages)

    async def close(self):
        for sender in self.senders.values():
            await sender.close()
        if self.client:
            await self.client.close()

from abc import ABC, abstractmethod
from typing import Any, List, Union
from pydantic import ValidationError
import logging
from azure.servicebus import ServiceBusMessage
from centraal_client_flow.connections.ibus_service_bus_client import IBServiceBusClient
from centraal_client_flow.models.schemas import EventoBase

class EventProcessor(ABC):
    def __init__(self, logger: logging.Logger, service_bus_client: IBServiceBusClient):
        self.logger = logger
        self.service_bus_client = service_bus_client

    @abstractmethod
    def process_event(self, event: Any) -> Union[EventoBase, List[EventoBase]]:

        pass

    async def handle_event(self, data: Any) -> None:
        try:
            eventos = self.process_event(data)
            if not isinstance(eventos, list):
                eventos = [eventos]
            await self.send_to_queue(eventos)
        except ValidationError as ve:
            self.logger.error(f"Error de validación: {ve}")
        except Exception as e:
            self.logger.error(f"Error al procesar el evento: {e}")

    async def send_to_queue(self, eventos: List[EventoBase]) -> None:
        if not eventos:
            self.logger.warning("No hay eventos para enviar a la cola.")
            return

        BATCH_THRESHOLD = 10
        messages = [ServiceBusMessage(body=event.json()) for event in eventos]
        queue_name = "QUEUE_NAME"  # Reemplaza con tu cola

        if len(messages) >= BATCH_THRESHOLD:
            self.logger.info("Enviando mensajes en batch.")
            try:
                sender = await self.service_bus_client.get_sender(queue_name=queue_name)
                batch_message = await sender.create_message_batch()
                for msg in messages:
                    try:
                        batch_message.add_message(msg)
                    except ValueError:
                        await self.service_bus_client.send_messages(sender, [batch_message])
                        batch_message = await sender.create_message_batch()
                        batch_message.add_message(msg)
                await self.service_bus_client.send_messages(sender, [batch_message])
                self.logger.info(f"Enviados {len(messages)} mensajes en batch.")
            except Exception as e:
                self.logger.error(f"Error al enviar batch de mensajes: {e}")
        else:
            self.logger.info("Enviando mensajes individualmente.")
            try:
                await self.service_bus_client.send_messages(sender, messages)
                self.logger.info(f"Enviados {len(messages)} mensajes individualmente.")
            except Exception as e:
                self.logger.error(f"Error al enviar mensajes individualmente: {e}")

                # centraal_client_flow/events/concrete_processor.py

from centraal_client_flow.events.processor import EventProcessor
from centraal_client_flow.models.schemas import EventoBase
from typing import Any, Union, List
from pydantic import ValidationError
import logging

class ConcreteEventProcessor(EventProcessor):
    def __init__(self, logger: logging.Logger, service_bus_client: IBServiceBusClient):
        super().__init__(logger, service_bus_client)

    def process_event(self, event: Any) -> Union[EventoBase, List[EventoBase]]:
        try:
            evento = EventoBase(**event)
            return evento
        except ValidationError as ve:
            self.logger.error(f"Validación fallida para el evento: {ve}")
            raise ve 

                # Configurar el cliente de Service Bus
    connection_str = "YOUR_CONNECTION_STRING"  # Configura esto adecuadamente
    service_bus_client = ServiceBusClientSingleton(connection_str)

    # Crear una instancia del procesador de eventos
    processor = ConcreteEventProcessor(logger=logger, service_bus_client=service_bus_client)

    # Evento de ejemplo
    sample_event = {
        "id": "123",
        "name": "Test Event",
        # Otros campos según el esquema de EventoBase
    }

    # Manejar el evento
    await processor.handle_event(sample_event)

    # Cerrar conexiones
    await service_bus_client.close()
"""


class EventProcessor(ABC):
    """Clase para procesar eventos.
    Esta clase estandariza la manera de procesar eventos basado en pydantic.

    La clase sirve coom clase a heredar y debe implementar un metodo:
    - process_event que general puede recibir cualquier tipo de dato pero debe devolver un evento validado (EventoBase) o una lista
    de evento validados (List[EventoBase]).

    el usuario solo tiene implemenetar ese metodo ya que luego la clase se encarga de:
    1. controlar errores de validación, para hacer un logger adecuado
    2. enviar el evento a la cola de eventos  de manera asincrona(usando batch si es necesario).
    """

    @abstractmethod
    def process_event(self, event: Any) -> Union[EventoBase, List[EventoBase]]:
        """Procesa un evento."""
        pass

    def handle_event(self, data: Any) -> None:
        try:
            eventos = self.process_event(data)
            if not isinstance(eventos, list):
                eventos = [eventos]
            self.send_to_queue(eventos)
        except ValidationError as ve:
            # Aquí manejarías el logging adecuado de los errores de validación
            print(f"Error de validación: {ve}")
        except Exception as e:
            # Manejo de otras excepciones
            print(f"Error al procesar el evento: {e}")

    def send_to_queue(self, eventos: List[EventoBase]) -> None:
        """Envia un evento a la cola de eventos."""
        pass

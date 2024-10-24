"""Conexiones a service bus."""

import json
from typing import Protocol, runtime_checkable, Optional

from azure.servicebus import ServiceBusClient, ServiceBusMessage


@runtime_checkable
class IServiceBusClient(Protocol):
    """Interfaz."""

    client: Optional[ServiceBusClient] = None
    connection_str: Optional[str] = None

    def send_message_to_queue(self, message: dict, session_id: str, queue_name: str):
        """Envía un mensaje a la cola de Service Bus especificada.

        Args:
            message: El mensaje a enviar representado como un diccionario.
            session_id: ID de sesión para el mensaje. Debe ser el id del modelo.
            queue_name: Nombre de la cola a la que se enviará el mensaje.
        """


class ServiceBusClientSingleton(IServiceBusClient):
    """Singleton para manejar la conexión a Azure Service Bus."""

    _instance = None
    client: Optional[ServiceBusClient] = None
    connection_str: Optional[str] = None
    senders = {}

    def __new__(cls, connection_str: str):
        """Crea una instancia única de ServiceBusClientSingleton si no existe.

        Args:
            connection_str: Cadena de conexión a Azure Service Bus.
        """
        if cls._instance is None:
            cls._instance = super(ServiceBusClientSingleton, cls).__new__(cls)
            cls._instance.connection_str = connection_str
            cls._instance.client = ServiceBusClient.from_connection_string(
                connection_str
            )

        return cls._instance

    def get_sender(self, queue_name: str):
        """Envía un mensaje a la cola de Service Bus especificada."""
        if queue_name not in self.senders and self.client:
            self.senders[queue_name] = self.client.get_queue_sender(queue_name)
        return self.senders[queue_name]

    def send_message_to_queue(self, message: dict, session_id: str, queue_name: str):
        """Envía un mensaje a la cola de Service Bus especificada. Concreta"""
        sender = self.get_sender(queue_name)
        msg = ServiceBusMessage(body=json.dumps(message))
        msg.session_id = session_id
        sender.send_messages(msg)

    def close(self):
        """Cierra la conexión con Azure Service Bus."""
        for sender in self.senders.values():
            sender.close()
        if self.client:
            self.client.close()

"""Conexiones a service bus."""

import json
from typing import Protocol, runtime_checkable

from azure.servicebus import ServiceBusClient, ServiceBusMessage


@runtime_checkable
class IServiceBusClient(Protocol):
    """Interfaz."""

    client: ServiceBusClient = None
    connection_str: str = None

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
    client: ServiceBusClient = None
    connection_str: str = None

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

    def send_message_to_queue(self, message: dict, session_id: str, queue_name: str):
        """Envía un mensaje a la cola de Service Bus especificada. Concreta"""
        sender = self.client.get_queue_sender(queue_name)
        msg = ServiceBusMessage(body=json.dumps(message))
        msg.session_id = session_id

        with sender:
            sender.send_messages(msg)

    def close(self):
        """Cierra la conexión a Service Bus y resetea la instancia del Singleton."""
        if self.client:
            self.client.close()
            ServiceBusClientSingleton._instance = None

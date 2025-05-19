"""Conexiones a service bus."""

import json
import logging
from typing import Protocol, runtime_checkable, Optional
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.servicebus.exceptions import ServiceBusError, ServiceBusConnectionError
from azure.core.exceptions import ServiceRequestError
import time

logger = logging.getLogger(__name__)


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
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    def __new__(cls, connection_str: str):
        """Crea una instancia única de ServiceBusClientSingleton si no existe.

        Args:
            connection_str: Cadena de conexión a Azure Service Bus.
        """
        if cls._instance is None:
            cls._instance = super(ServiceBusClientSingleton, cls).__new__(cls)
            cls._instance.connection_str = connection_str
            cls._instance._initialize_client()

        return cls._instance

    def _initialize_client(self):
        """Initialize the Service Bus client with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                self.client = ServiceBusClient.from_connection_string(self.connection_str)
                logger.info("Successfully initialized Service Bus client")
                return
            except (ServiceBusError, ServiceBusConnectionError, AttributeError) as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(
                        f"Failed to initialize Service Bus client after {self.MAX_RETRIES} attempts: {str(e)}")
                    raise
                logger.warning(
                    f"Attempt {attempt + 1} failed to initialize Service Bus client: {str(e)}")
                time.sleep(self.RETRY_DELAY)

    def _ensure_client_connection(self):
        """Ensure the client is connected and valid."""
        if not self.client:
            self._initialize_client()
        return self.client

    def get_sender(self, queue_name: str):
        """Get or create a sender for the specified queue with retry logic."""
        if queue_name not in self.senders:
            for attempt in range(self.MAX_RETRIES):
                try:
                    client = self._ensure_client_connection()
                    if queue_name in self.senders:
                        try:
                            self.senders[queue_name].close()
                        except Exception as e:
                            logger.warning(f"Error closing existing sender: {str(e)}")

                    self.senders[queue_name] = client.get_queue_sender(queue_name)
                    logger.info(f"Successfully created sender for queue: {queue_name}")
                    break
                except (ServiceBusError, ServiceBusConnectionError, AttributeError) as e:
                    if attempt == self.MAX_RETRIES - 1:
                        logger.error(
                            f"Failed to create sender for queue {queue_name} after {self.MAX_RETRIES} attempts: {str(e)}")
                        raise
                    logger.warning(
                        f"Attempt {attempt + 1} failed to create sender for queue {queue_name}: {str(e)}")
                    time.sleep(self.RETRY_DELAY)
                    self._initialize_client()  # Try to reinitialize the client

        return self.senders[queue_name]

    def send_message_to_queue(self, message: dict, session_id: str, queue_name: str):
        """Envía un mensaje a la cola de Service Bus especificada con retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                sender = self.get_sender(queue_name)

                msg = ServiceBusMessage(body=json.dumps(message))
                msg.session_id = session_id
                sender.send_messages(msg)
                logger.info(
                    f"Successfully sent message to queue {queue_name} with session_id {session_id}")
                return
            except (ServiceBusError, ServiceBusConnectionError, ServiceRequestError, AttributeError) as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(
                        f"Failed to send message to queue {queue_name} after {self.MAX_RETRIES} attempts: {str(e)}")
                    raise e
                logger.warning(
                    f"Attempt {attempt + 1} failed to send message to queue {queue_name}: {str(e)}")
                time.sleep(self.RETRY_DELAY)
                self._initialize_client()
                if queue_name in self.senders:
                    try:
                        self.senders[queue_name].close()
                    except Exception as close_error:
                        logger.warning(f"Error closing sender during retry: {str(close_error)}")
                    del self.senders[queue_name]

    def close(self):
        """Cierra la conexión con Azure Service Bus."""
        try:
            for queue_name, sender in list(self.senders.items()):
                try:
                    sender.close()
                    logger.info(f"Successfully closed sender for queue: {queue_name}")
                except Exception as e:
                    logger.warning(f"Error closing sender for queue {queue_name}: {str(e)}")

            if self.client:
                try:
                    self.client.close()
                    logger.info("Successfully closed Service Bus client")
                except Exception as e:
                    logger.warning(f"Error closing client: {str(e)}")

            self.senders.clear()
            self.client = None
            logger.info("Successfully closed all Service Bus connections")
        except Exception as e:
            logger.error(f"Error during Service Bus cleanup: {str(e)}")
            raise

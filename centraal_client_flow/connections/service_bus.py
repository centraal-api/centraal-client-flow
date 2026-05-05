"""Conexiones a service bus."""

import json
import logging
import threading
from typing import Protocol, runtime_checkable, Optional
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.servicebus.exceptions import ServiceBusError, ServiceBusConnectionError
from azure.core.exceptions import ServiceRequestError
import time

logger = logging.getLogger(__name__)


class _LockedQueueSenderContext:
    """Context manager que mantiene el lock del singleton mientras vive el sender."""

    def __init__(self, singleton: "ServiceBusClientSingleton", queue_name: str):
        self._singleton = singleton
        self._queue_name = queue_name
        self._inner_cm = None

    def __enter__(self):
        self._singleton._lock.acquire()
        try:
            client = self._singleton._ensure_client_connection()
            self._inner_cm = client.get_queue_sender(self._queue_name)
            return self._inner_cm.__enter__()
        except BaseException:
            self._singleton._lock.release()
            raise

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._inner_cm is not None:
                return self._inner_cm.__exit__(exc_type, exc, tb)
            return False
        finally:
            self._singleton._lock.release()


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
    """Singleton para manejar la conexión a Azure Service Bus.

    No se cachea el sender: se obtiene uno nuevo por envío (with client.get_queue_sender)
    para evitar el error AttributeError por sesión AMQP cerrada (issue #32967).

    ``ServiceBusSender`` y la recreación del cliente bajo reintentos no son seguros entre
    hilos: un ``threading.Lock`` a nivel de instancia serializa ``send_message_to_queue``,
    el uso de ``get_sender`` y ``close``.
    """

    _instance = None
    _lock: threading.Lock
    client: Optional[ServiceBusClient] = None
    connection_str: Optional[str] = None
    logging_enable: bool = False
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    def __new__(cls, connection_str: str, logging_enable: bool = False):
        """Crea una instancia única de ServiceBusClientSingleton si no existe.

        Args:
            connection_str: Cadena de conexión a Azure Service Bus.
            logging_enable: Si True, habilita logging del cliente (útil para depurar
                timeouts/conexión, p. ej. "Failed to initiate the connection due to exception").
        """
        if cls._instance is None:
            cls._instance = super(ServiceBusClientSingleton, cls).__new__(cls)
            cls._instance._lock = threading.Lock()
            cls._instance.connection_str = connection_str
            cls._instance.logging_enable = logging_enable
            cls._instance._initialize_client()

        return cls._instance

    def _initialize_client(self):
        """Initialize the Service Bus client with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                self.client = ServiceBusClient.from_connection_string(
                    self.connection_str,
                    logging_enable=self.logging_enable,
                )
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

    def _ensure_client_connection(self) -> ServiceBusClient:
        """Ensure the client is connected and valid."""
        if not self.client:
            self._initialize_client()
        return self.client

    def synchronize(self):
        """Context manager que toma el mismo lock que envíos y ``get_sender``.

        Usar al acceder a ``client`` directamente (p. ej. ``get_topic_sender``) para
        no competir con otros hilos que usan el singleton.
        """
        return self._lock

    def get_sender(self, queue_name: str):
        """Obtiene un sender para la cola (retrocompatibilidad).

        Cada llamada devuelve un sender nuevo (no cacheado) para evitar sesión AMQP
        cerrada (issue #32967). Usar como context manager y cerrar después de usar:

            with service_bus_client.get_sender(queue_name) as sender:
                sender.send_messages(msg)

        El lock del singleton se mantiene durante todo el bloque ``with`` para evitar
        condiciones de carrera entre hilos (p. ej. Azure Functions worker).
        """
        return _LockedQueueSenderContext(self, queue_name)

    def send_message_to_queue(self, message: dict, session_id: str, queue_name: str):
        """Envía un mensaje a la cola de Service Bus especificada con retry logic.

        Obtiene un sender nuevo por operación (no cacheado) para evitar reutilizar
        una conexión/sesión AMQP cerrada que provoca AttributeError en create_sender_link.
        """
        with self._lock:
            for attempt in range(self.MAX_RETRIES):
                try:
                    client = self._ensure_client_connection()
                    with client.get_queue_sender(queue_name) as sender:
                        msg = ServiceBusMessage(body=json.dumps(message))
                        msg.session_id = session_id
                        sender.send_messages(msg)
                    logger.debug(
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

    def close(self):
        """Cierra la conexión con Azure Service Bus."""
        with self._lock:
            try:
                if self.client:
                    try:
                        self.client.close()
                        logger.info("Successfully closed Service Bus client")
                    except Exception as e:
                        logger.warning(f"Error closing client: {str(e)}")
                    self.client = None
                logger.info("Successfully closed all Service Bus connections")
            except Exception as e:
                logger.error(f"Error during Service Bus cleanup: {str(e)}")
                raise

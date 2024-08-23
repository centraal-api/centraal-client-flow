"""Módulo para recibir eventos desde una fuente externa y procesarlos a través de Azure Functions."""

import logging

from azure.functions import Blueprint, HttpRequest, HttpResponse
from pydantic import BaseModel

from centraal_client_flow.connections.service_bus import IServiceBusClient
from centraal_client_flow.events import EventProcessor


class EventFunctionBuilder:
    """
    Clase para construir y registrar funciones de Azure para recibir y procesar eventos.

    Esta clase permite construir dinámicamente funciones de Azure que se desencadenan
    por solicitudes HTTP POST para recibir y procesar eventos utilizando un modelo de evento
    específico y un procesador de eventos.
    """

    def __init__(
        self,
        function_name: str,
        event_source: str,
        queue_name: str,
        service_bus_client: IServiceBusClient,
        processor: EventProcessor,
        event_model: type[BaseModel],
    ):
        """
        Inicializa un constructor de funciones para eventos con los parámetros especificados.

        Args:
            function_name: Nombre único de la función que se va a registrar.
            event_source: Nombre de la fuente del evento.
            queue_name: Nombre de la cola de Service Bus donde se enviarán los mensajes.
            service_bus_client: Cliente de Service Bus para enviar mensajes.
            processor: Procesador de eventos que hereda de EventProcessor.
            event_model: Modelo Pydantic para validar y parsear los eventos.
        """
        self.function_name = function_name
        self.event_source = event_source
        self.queue_name = queue_name
        self.service_bus_client = service_bus_client
        self.processor = processor
        self.event_model = event_model

    def build_function(self):
        """
        Construye la función de Azure para recibir y procesar eventos.

        Returns:
            Una función que procesa solicitudes HTTP POST, valida los eventos recibidos
            y los envía a una cola de Service Bus.
        """

        def receive_event(req: HttpRequest) -> HttpResponse:
            event_data = req.get_json()
            logging.info("validando informacion")
            event = self.event_model.model_validate(event_data)

            event_validado = self.processor.process_event(event)
            data_validada = event_validado.model_dump(mode="json", exclude_none=True)
            logging.info("enviando informacion")
            self.service_bus_client.send_message_to_queue(
                data_validada, str(event_validado.id), self.queue_name
            )

            return HttpResponse(
                f"Evento de {self.event_source} es procesado.", status_code=200
            )

        return receive_event

    def register_function(self, bp: Blueprint):
        """
        Registra la función construida en el Blueprint proporcionado.

        Args:
            bp: Blueprint de Azure Functions donde se registrará la función.

        Returns:
            El Blueprint actualizado con la función registrada.
        """
        receive_event = self.build_function()

        bp.function_name(name=self.function_name)(
            bp.route(methods=["POST"])(receive_event)
        )
        return bp


class Recieve:
    """
    Clase para manejar la recepción y procesamiento de eventos desde una fuente específica.

    Esta clase define y registra reglas de procesamiento de eventos utilizando una fuente de eventos,
    un modelo de evento, y un procesador de eventos.
    """

    def __init__(
        self,
        event_source: str,
        queue_name: str,
        service_bus_client: IServiceBusClient,
    ):
        """
        Inicializa una instancia de Receiver.

        Args:
            event_source: Nombre de la fuente del evento.
            queue_name: Nombre de la cola de Service Bus donde se enviarán los mensajes.
            service_bus_client: Cliente de Service Bus para enviar mensajes.
        """
        self.function_name = f"{event_source.lower()}_receive_event"
        self.event_source = event_source
        self.queue_name = queue_name
        self.service_bus_client = service_bus_client

    def register_function(
        self,
        bp: Blueprint,
        processor: EventProcessor,
        event_model: type[BaseModel],
    ) -> None:
        """
        Crea y registra una función para recibir y procesar eventos en el Blueprint proporcionado.

        Args:
            bp: Blueprint de Azure Functions donde se registrará la función.
            processor: Instancia de una clase que hereda de EventProcessor.
            event_model: Modelo Pydantic para validar y parsear el evento.

        Returns:
            El Blueprint actualizado con la función de procesamiento de eventos registrada.
        """
        builder = EventFunctionBuilder(
            function_name=self.function_name,
            event_source=self.event_source,
            queue_name=self.queue_name,
            service_bus_client=self.service_bus_client,
            processor=processor,
            event_model=event_model,
        )
        builder.register_function(bp)

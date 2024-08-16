"""Módulo para recibir eventos desde una fuente externa y procesarlos a través de Azure Functions."""

import logging


from azure.functions import Blueprint, HttpRequest, HttpResponse
from pydantic import BaseModel

from centraal_client_flow.connections.service_bus import IServiceBusClient
from centraal_client_flow.events import EventProcessor


class Recieve:
    """Clase para manejar la recepción y procesamiento de eventos desde una fuente específica."""

    def __init__(
        self, event_source: str, queue_name: str, service_bus_client: IServiceBusClient
    ):
        """
        Inicializa una instancia de Receiver.

        Parameters:
            event_source: Nombre de la fuente del evento.
            queue_name: Nombre de la cola de Service Bus donde se enviarán los mensajes.
            service_bus_client: cliente service_bus_client.
        """
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
        Registra una función en un Blueprint de Azure Function para recibir y procesar eventos.

        Parameters:
            bp: Blueprint en el cual se registrará la función.
            processor: Instancia de una clase que hereda de EventProcessor.
            event_model: Modelo Pydantic para validar y parsear el evento.
        """

        function_name = f"{self.event_source}-receive-event"

        @bp.function_name(function_name)
        @bp.route(methods=["POST"])
        def receive_event(req: HttpRequest) -> HttpResponse:

            event_data = req.get_json()
            logging.info("validando informacion")
            event = event_model.model_validate(event_data)

            event_validado = processor.process_event(event)
            data_validada = event_validado.model_dump(mode="json", exclude_none=True)
            logging.info("enviando informacion")
            self.service_bus_client.send_message_to_queue(
                data_validada, str(event_validado.id), self.queue_name
            )

            return HttpResponse(
                f"Evento de {self.event_source} es procesado.", status_code=200
            )

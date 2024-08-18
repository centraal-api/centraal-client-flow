"""Módulo para recibir eventos desde una fuente externa y procesarlos a través de Azure Functions."""

import logging

from azure.functions import Blueprint, TimerRequest
from pydantic import ValidationError

from centraal_client_flow.connections.service_bus import IServiceBusClient
from centraal_client_flow.events import PullProcessor


class Pull:
    """Clase para manejar la ejecución de tareas programadas y el envío de datos a Service Bus."""

    def __init__(
        self,
        schedule: str,
        event_source: str,
        queue_name: str,
        service_bus_client: IServiceBusClient,
    ):
        """
        Inicializa una instancia de Timer.

        Parameters:
            event_source: Nombre de la fuente del evento.
            queue_name (str): Nombre de la cola de Service Bus donde se enviarán los mensajes.
            connection_str (str): Cadena de conexión a Service Bus.
        """
        self.event_source = event_source
        self.schedule = schedule
        self.queue_name = queue_name
        self.service_bus_client = service_bus_client

    def register_function(
        self,
        bp: Blueprint,
        processor: PullProcessor,
    ) -> None:
        """
        Registra una función en un Blueprint de Azure Function para recibir y procesar eventos.

        Parameters:
            bp: Blueprint en el cual se registrará la función.
            processor: Instancia de una clase que hereda de PullProcessor.

        """

        function_name = f"{self.event_source}-receive-event"

        @bp.function_name(function_name)
        @bp.schedule(schedule=self.schedule, arg_name="mytimer", run_on_startup=False)
        def timer_function(mytimer: TimerRequest):
            if mytimer.past_due:
                logging.info("The timer is past due!")

            event_data = processor.get_data()

            for event_in_data in event_data:

                try:
                    event_validado = processor.process_event(event_in_data)
                    data_validada = event_validado.model_dump(
                        mode="json", exclude_none=True
                    )

                    self.service_bus_client.send_message_to_queue(
                        data_validada, str(event_validado.id), self.queue_name
                    )
                except ValidationError as e:
                    logging.error("error in %s, excepcion\n%s", event_in_data, e)

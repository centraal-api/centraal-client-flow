"""Módulo para recibir eventos desde una fuente externa y procesarlos a través de Azure Functions."""

import logging

from azure.functions import Blueprint, TimerRequest
from pydantic import ValidationError

from centraal_client_flow.connections.service_bus import IServiceBusClient
from centraal_client_flow.events import PullProcessor


class TimerFunctionBuilder:
    """
    Clase para construir y registrar funciones de Azure programadas.

    Esta clase permite construir dinámicamente funciones de Azure que se desencadenan
    por un temporizador, procesan eventos y los envían a un Service Bus.
    """

    def __init__(
        self,
        function_name: str,
        schedule: str,
        event_source: str,
        queue_name: str,
        service_bus_client: IServiceBusClient,
        processor: PullProcessor,
    ):
        """
        Inicializa un constructor de funciones programadas con los parámetros especificados.

        Args:
            function_name: Nombre único de la función que se va a registrar.
            schedule: Cadena que define el horario del temporizador (CRON).
            event_source: Nombre de la fuente del evento.
            queue_name: Nombre de la cola de Service Bus donde se enviarán los mensajes.
            service_bus_client: Cliente de Service Bus para enviar mensajes.
            processor: Procesador de eventos que hereda de PullProcessor.
        """
        self.function_name = function_name
        self.schedule = schedule
        self.event_source = event_source
        self.queue_name = queue_name
        self.service_bus_client = service_bus_client
        self.processor = processor

    def build_function(self):
        """
        Construye la función de Azure programada para ejecutar tareas periódicamente.

        Returns:
            Una función que se ejecuta en base a un temporizador, procesa datos y los envía a una cola de Service Bus.
        """

        def timer_function(mytimer: TimerRequest):
            if mytimer.past_due:
                logging.info("The timer is past due!")

            event_data = self.processor.get_data()

            for event_in_data in event_data:
                try:
                    event_validado = self.processor.process_event(event_in_data)
                    data_validada = event_validado.model_dump(
                        mode="json", exclude_none=True
                    )

                    self.service_bus_client.send_message_to_queue(
                        data_validada, str(event_validado.id), self.queue_name
                    )
                except ValidationError as e:
                    logging.error("Error en %s, excepción:\n%s", event_in_data, e)

        return timer_function

    def register_function(self, bp: Blueprint):
        """
        Registra la función construida en el Blueprint proporcionado.

        Args:
            bp: Blueprint de Azure Functions donde se registrará la función.

        Returns:
            El Blueprint actualizado con la función registrada.
        """
        timer_function = self.build_function()

        bp.function_name(name=self.function_name)(
            bp.schedule(
                schedule=self.schedule, arg_name="mytimer", run_on_startup=False
            )(timer_function)
        )
        return bp


class Pull:
    """
    Clase para manejar la ejecución de tareas programadas y el envío de datos a Service Bus.

    Esta clase define y registra reglas de procesamiento de tareas utilizando un temporizador,
    un procesador de eventos y un cliente de Service Bus.
    """

    def __init__(
        self,
        schedule: str,
        event_source: str,
        queue_name: str,
        service_bus_client: IServiceBusClient,
    ):
        """
        Inicializa una instancia de Pull.

        Args:
            schedule: Cadena que define el horario del temporizador (CRON).
            event_source: Nombre de la fuente del evento.
            queue_name: Nombre de la cola de Service Bus donde se enviarán los mensajes.
            service_bus_client: Cliente de Service Bus para enviar mensajes.
        """
        self.function_name = f"{event_source.lower()}_scheduled_event"
        self.schedule = schedule
        self.event_source = event_source
        self.queue_name = queue_name
        self.service_bus_client = service_bus_client

    def register_function(
        self,
        bp: Blueprint,
        processor: PullProcessor,
    ) -> None:
        """
        Crea y registra una función programada para ejecutar tareas periódicamente en el Blueprint proporcionado.

        Args:
            bp: Blueprint de Azure Functions donde se registrará la función.
            processor: Instancia de una clase que hereda de PullProcessor.

        Returns:
            El Blueprint actualizado con la función programada registrada.
        """
        builder = TimerFunctionBuilder(
            function_name=self.function_name,
            schedule=self.schedule,
            event_source=self.event_source,
            queue_name=self.queue_name,
            service_bus_client=self.service_bus_client,
            processor=processor,
        )
        builder.register_function(bp)

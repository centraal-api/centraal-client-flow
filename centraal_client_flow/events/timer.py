from typing import Callable

from azure.functions import Blueprint, TimerRequest

from centraal_client_flow.connections.service_bus import ServiceBusClientSingleton


class TimerBase:
    def __init__(self, schedule: str, queue_name: str, connection_str: str):
        self.schedule = schedule
        self.queue_name = queue_name
        self.connection_str = connection_str
        self.service_bus_client = ServiceBusClientSingleton(
            connection_str
        )  # Inicializar Singleton

    def create_blueprint(self, extract_data: Callable, determine_session_id: Callable):
        bp = Blueprint()

        @bp.function_name("timer_function")
        @bp.schedule(schedule=self.schedule)
        def timer_function(timer: TimerRequest):
            event_data = extract_data()
            session_id = determine_session_id(event_data)

            # Enviar mensaje a Service Bus utilizando el Singleton
            self.service_bus_client.send_message_to_queue(
                event_data, session_id, self.queue_name
            )

        return bp

    def close(self):
        # Método para cerrar la conexión del cliente Service Bus cuando ya no se necesite
        self.service_bus_client.close()

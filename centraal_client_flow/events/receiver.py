from typing import Callable
from azure.functions import Blueprint, HttpRequest, HttpResponse
from centraal_client_flow.connections.service_bus import ServiceBusClientSingleton


class ReceiverBase:
    def __init__(self, event_source: str, queue_name: str, connection_str: str):
        self.event_source = event_source
        self.queue_name = queue_name
        self.connection_str = connection_str
        self.service_bus_client = ServiceBusClientSingleton(connection_str)

    def create_blueprint(
        self,
        process_event: Callable,
        validate_event: Callable = None,
        log_event: Callable = None,
    ):
        bp = Blueprint()

        @bp.route("/receive-event", methods=["POST"])
        def receive_event(req: HttpRequest) -> HttpResponse:
            if validate_event:
                validation_response = validate_event(req)
                if validation_response:
                    return validation_response

            if log_event:
                log_event(req)

            session_id = req.params.get("session_id")
            event_data = req.get_json()

            # Espacio para lógica personalizada
            process_event(event_data)

            # Enviar mensaje a Service Bus utilizando el Singleton
            self.service_bus_client.send_message_to_queue(
                event_data, session_id, self.queue_name
            )

            return HttpResponse(
                f"Event from {self.event_source} processed", status_code=200
            )

        return bp

    def close(self):
        # Método para cerrar la conexión del cliente Service Bus cuando ya no se necesite
        self.service_bus_client.close()

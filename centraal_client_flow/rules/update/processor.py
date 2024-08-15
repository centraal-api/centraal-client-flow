from typing import Callable, List

from azure.functions import Blueprint, ServiceBusMessage
from azure.servicebus import ServiceBusClient
from azure.servicebus import ServiceBusMessage as SBMessage

from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton


class ProcessorBase:
    def __init__(
        self,
        queue_name: str,
        connection_str: str,
        topic_names: List[str],
        cosmos_container_name: str,
    ):
        self.queue_name = queue_name
        self.connection_str = connection_str
        self.topic_names = topic_names
        self.cosmos_container_name = cosmos_container_name
        self.service_bus_client = ServiceBusClient.from_connection_string(
            connection_str
        )
        self.cosmos_client = CosmosDBSingleton()  # Inicializar Singleton de CosmosDB

    def create_blueprint(
        self,
        process_message: Callable,
        prepare_output: Callable = None,
        post_process: Callable = None,
    ):
        bp = Blueprint()

        @bp.service_bus_queue_trigger(
            arg_name="msg", queue_name=self.queue_name, connection=self.connection_str
        )
        def process_function(msg: ServiceBusMessage):
            data = msg.get_body().decode("utf-8")
            processed_data = process_message(data)

            # Guardar en Cosmos DB utilizando el Singleton
            self.save_to_cosmos_db(processed_data)

            # Preparar el mensaje para la salida (si es necesario)
            if prepare_output:
                processed_data = prepare_output(processed_data)

            # Publicar manualmente en múltiples topics
            self.publish_to_topics(processed_data)

            # Lógica adicional después del procesamiento
            if post_process:
                post_process(processed_data)

        return bp

    def save_to_cosmos_db(self, data):
        """Guarda los datos en Cosmos DB."""
        container = self.cosmos_client.get_container_client(self.cosmos_container_name)
        container.upsert_item(data)

    def publish_to_topics(self, processed_data):
        client = self.service_bus_client
        for topic_name in self.topic_names:
            with client.get_topic_sender(topic_name=topic_name) as sender:
                message = SBMessage(processed_data)
                sender.send_messages(message)

    def close(self):
        # Método para cerrar la conexión del cliente Service Bus y Cosmos DB cuando ya no se necesite
        self.service_bus_client.close()
        self.cosmos_client.client.close()

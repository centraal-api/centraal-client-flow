from azure.servicebus import ServiceBusClient, ServiceBusMessage


class ServiceBusClientSingleton:
    _instance = None

    def __new__(cls, connection_str: str):
        if cls._instance is None:
            cls._instance = super(ServiceBusClientSingleton, cls).__new__(cls)
            cls._instance.connection_str = connection_str
            cls._instance.client = ServiceBusClient.from_connection_string(
                connection_str
            )
        return cls._instance

    def send_message_to_queue(self, message: dict, session_id: str, queue_name: str):
        sender = self.client.get_queue_sender(queue_name)
        msg = ServiceBusMessage(body=str(message))
        msg.session_id = session_id

        with sender:
            sender.send_messages(msg)

    def close(self):
        if self.client:
            self.client.close()
            ServiceBusClientSingleton._instance = None  # Reset the singleton instance

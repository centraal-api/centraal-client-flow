from azure.functions import Blueprint, ServiceBusMessage
from .strategy import IntegrationStrategy
from typing import Callable


class IntegrationBase:
    def __init__(self, topic_name: str, connection_str: str, subscription_name: str):
        self.topic_name = topic_name
        self.connection_str = connection_str
        self.subscription_name = subscription_name

    def create_blueprint(
        self,
        integration_strategy: IntegrationStrategy,
        post_integration: Callable = None,
    ):
        bp = Blueprint()

        @bp.service_bus_topic_trigger(
            arg_name="message",
            topic_name=self.topic_name,
            connection=self.connection_str,
            subscription_name=self.subscription_name,
        )
        def integrate_function(message: ServiceBusMessage):
            message_body = message.get_body().decode("utf-8")

            integration_strategy.integrate(message_body)

            if post_integration:
                post_integration(message_body)

        return bp

"""Reglas de integración."""

import json

from azure.functions import Blueprint, ServiceBusMessage

from centraal_client_flow.models.schemas import EntradaEsquemaUnificado
from centraal_client_flow.rules.integration.strategy import IntegrationStrategy


class IntegrationRule:
    def __init__(
        self,
        topic_name: str,
        connection_str: str,
        subscription_name: str,
        integration_strategy: IntegrationStrategy,
        model_unficado: type[EntradaEsquemaUnificado],
    ):
        self.topic_name = topic_name
        self.connection_str = connection_str
        self.subscription_name = subscription_name
        self.integration_strategy = integration_strategy
        self.model_unficado = model_unficado

    def register_function(
        self,
        bp: Blueprint,
    ):

        function_name = f"{self.integration_strategy.name}-{self.topic_name}-intrule"

        @bp.function_name(name=function_name)
        @bp.service_bus_topic_trigger(
            arg_name="message",
            topic_name=self.topic_name,
            connection=self.connection_str,
            subscription_name=self.subscription_name,
        )
        def integrate_function(message: ServiceBusMessage):
            message_body = json.loads(message.get_body().decode("utf-8"))

            message_esquema = self.model_unficado.model_validate(message_body)

            output_model = self.integration_strategy.modelo_unificado_mapping(
                message_esquema
            )
            self.integration_strategy.integrate(output_model)

        return bp

"""Reglas de integración."""

import json
import logging

from azure.functions import Blueprint, ServiceBusMessage
from pydantic import ValidationError

from centraal_client_flow.models.schemas import EntradaEsquemaUnificado
from centraal_client_flow.rules.integration.strategy import IntegrationStrategy


class FunctionBuilder:
    """
    Clase para construir y registrar funciones de Azure basadas en la configuración proporcionada.

    Esta clase permite construir dinámicamente funciones de Azure que se desencadenan
    por mensajes de un topic de Service Bus, utilizando una estrategia de integración específica
    y un modelo de esquema de entrada unificado.
    """

    def __init__(
        self,
        function_name: str,
        topic_name: str,
        connection_str: str,
        subscription_name: str,
        integration_strategy: IntegrationStrategy,
        model_unficado: type[EntradaEsquemaUnificado],
    ):
        """
        Inicializa un constructor de funciones con los parámetros especificados.

        Args:
            function_name: Nombre único de la función que se va a registrar.
            topic_name: Nombre del topic de Service Bus desde donde se recibirán los mensajes.
            connection_str: Cadena de conexión para el Service Bus.
            subscription_name: Nombre de la suscripción en el topic de Service Bus.
            integration_strategy: Estrategia de integración que se aplicará al procesar el mensaje.
            model_unficado: Modelo de esquema unificado para validar y mapear los mensajes recibidos.
        """
        self.function_name = function_name
        self.topic_name = topic_name
        self.connection_str = connection_str
        self.subscription_name = subscription_name
        self.integration_strategy = integration_strategy
        self.model_unficado = model_unficado

    def build_function(self):
        """
        Construye la función de integración de Azure que procesa mensajes del topic de Service Bus.

        Returns:
            Una función que procesa mensajes, valida el esquema de entrada, aplica la estrategia de integración
            y realiza la integración.
        """

        def integrate_function(message: ServiceBusMessage):
            message_body = json.loads(message.get_body().decode("utf-8"))
            message_esquema = self.model_unficado.model_validate(message_body)
            output_model = self.integration_strategy.modelo_unificado_mapping(
                message_esquema
            )
            self.integration_strategy.integrate(output_model)

        return integrate_function

    def register_function(self, bp: Blueprint):
        """
        Registra la función construida en el Blueprint proporcionado.

        Args:
            bp: Blueprint de Azure Functions donde se registrará la función.

        Returns:
            El Blueprint actualizado con la función registrada.
        """
        integrate_function = self.build_function()

        bp.function_name(name=self.function_name)(
            bp.service_bus_topic_trigger(
                arg_name="message",
                topic_name=self.topic_name,
                connection=self.connection_str,
                subscription_name=self.subscription_name,
            )(integrate_function)
        )
        return bp


class IntegrationRule:
    """
    Clase para definir y registrar reglas de integración basadas en topics de Service Bus.

    Esta clase encapsula la lógica para definir una regla de integración utilizando un topic,
    una suscripción y una estrategia de integración específica.
    """

    def __init__(
        self,
        topic_name: str,
        connection_str: str,
        subscription_name: str,
        integration_strategy: IntegrationStrategy,
        model_unficado: type[EntradaEsquemaUnificado],
    ):
        """
        Inicializa una regla de integración con los parámetros especificados.

        Args:
            topic_name: Nombre del topic de Service Bus que se utilizará para la integración.
            connection_str: Cadena de conexión para el Service Bus.
            subscription_name: Nombre de la suscripción en el topic de Service Bus.
            integration_strategy: Estrategia de integración a aplicar en los mensajes procesados.
            model_unficado: Modelo de esquema unificado para validar y mapear los mensajes recibidos.
        """
        if integration_strategy.name is not None:
            self.function_name = (
                f"{integration_strategy.name.lower()}_{topic_name}_intrule"
            )
        else:
            self.function_name = f"{topic_name}_intrule"

        self.topic_name = topic_name
        self.connection_str = connection_str
        self.subscription_name = subscription_name
        self.integration_strategy = integration_strategy
        self.model_unficado = model_unficado

    def run(self, message: dict, logger: logging.Logger):
        """Ejecutra la regla de integración."""
        try:
            message_esquema = self.model_unficado.model_validate(message)
            output_model = self.integration_strategy.modelo_unificado_mapping(
                message_esquema
            )
        except ValidationError as e:
            logger.error(
                "Error antes de integración en validación %s", e.errors(), exc_info=True
            )
            raise e
        self.integration_strategy.integrate(output_model)

    def register_function(self, bp: Blueprint):
        """
        Crea y registra una función de integración en el Blueprint proporcionado.
        TODO: esto debe ser validado si es posible, actualmente no funciona!!

        Args:
            bp: Blueprint de Azure Functions donde se registrará la función de integración.

        Returns:
            El Blueprint actualizado con la función de integración registrada.
        """
        builder = FunctionBuilder(
            function_name=self.function_name,
            topic_name=self.topic_name,
            connection_str=self.connection_str,
            subscription_name=self.subscription_name,
            integration_strategy=self.integration_strategy,
            model_unficado=self.model_unficado,
        )
        return builder.register_function(bp)

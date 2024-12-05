"""Reglas de integración."""

import json
import logging
from typing import Optional

from azure.functions import ServiceBusMessage
from pydantic import ValidationError

from centraal_client_flow.models.schemas import (
    EntradaEsquemaUnificado,
    AuditoriaEntryIntegracion,
    IDModel,
)
from centraal_client_flow.rules.integration.strategy import (
    IntegrationStrategy,
    StrategyResult,
)
from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton
from centraal_client_flow.helpers.pydantic import serialize_validation_errors


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
        self.id_esquema: Optional[IDModel] = None

    def run(
        self, message: ServiceBusMessage | dict, logger: logging.Logger
    ) -> Optional[StrategyResult]:
        """Ejecuta la regla de integración."""
        if isinstance(message, ServiceBusMessage):
            message = json.loads(message.message)

        try:
            message_esquema = self.model_unficado.model_validate(message)
            self.id_esquema = message_esquema.id
            output_model = self.integration_strategy.modelo_unificado_mapping(
                message_esquema
            )
        except ValidationError as e:

            error_val_cosmos_friendly = serialize_validation_errors(e.errors())

            logger.error(
                "Error antes de integración en validación %s",
                error_val_cosmos_friendly,
                exc_info=True,
            )
            return StrategyResult(
                success=False,
                response={"error_validacion": error_val_cosmos_friendly},
                bodysent={"error_validacion": True},
            )

        return self.integration_strategy.integrate(output_model)

    def register_log(
        self,
        result: StrategyResult,
        cosmos_client: CosmosDBSingleton,
        container_name: str,
    ):
        container = cosmos_client.get_container_client(container_name)
        if self.id_esquema is not None:
            entry = AuditoriaEntryIntegracion(
                id=self.id_esquema,
                regla=self.function_name,
                contenido=result.bodysent,
                sucess=result.success,
                response=result.response,
            )
            item_written = container.upsert_item(
                entry.model_dump(mode="json", exclude_none=True),
            )
            return item_written

        raise ValueError("No es posible usar registro del log.")

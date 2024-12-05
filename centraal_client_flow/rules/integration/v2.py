"""Implementación de la regla de integración v2."""

import logging
import json
import time

from abc import ABC, abstractmethod
from typing import Optional, Union
from dataclasses import dataclass

from azure.functions import ServiceBusMessage
from pydantic import ValidationError

from centraal_client_flow.models.schemas import (
    EntradaEsquemaUnificado,
    AuditoriaEntryIntegracion,
)
from centraal_client_flow.helpers.pydantic import (
    serialize_validation_errors,
    built_valid_json_str_with_aditional_info,
)
from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton


@dataclass
class IntegrationResult:
    """Resultado de integración."""

    success: bool
    response: dict
    bodysent: dict

    def __post_init__(self):
        """Valida que bodysent no sea un diccionario vacío."""
        if not self.bodysent:
            raise ValueError("bodysent no puede ser un diccionario vacío")

        if not self.response:
            raise ValueError("response no puede ser un diccionario vacío")


class IntegrationRule(ABC):
    """Implementación de la regla de integración v2.
    Esta implementación es una regla tiene el objetivo de simplicar la implementación,
    se observa que en los casos de uso la estrategias de integración no son valiosas y dan
    muy poca flexibilidad. Adicional en general las reglas de integración son un concpeto mas directo y
    claro para representar la logica de transformación del modelo unficaido a lo que necesita el sistema
    destino, esto ayudara a que el usuario implemente directamente la transformación y operaciones
    necesarias sin necesidad de definirla en un objeto diferente.

    La reglas integración se implementa como una clase abstracta con metodos compartidos, el usuario solo debera
    implementar el metodo abstracto `integrate`, que debe recibir el mensaje del topic, codificarlo mediante el modelo unificado
    y hacer la implemetación que requiera (inlcuido mapping o logicas adicionales para realizar la integración),
    y el set de body_sent que se enviara a la auditoria de cosmos, par asaber que se envio al sistema destino.
    con el unico requisito de devolver un IntegrationResult, que indicara el resultado
    de la transformación.

    la clase abstracta tendra la implementación de metodos concretos:
    run: se encarga de ejecutar `integrate` y realizar el logging a la auditoria de cosmos.
    register_log: se encarga de realizar el logging de la auditoria de cosmos.
    """

    def __init__(
        self,
        name: str,
        model_unficado: type[EntradaEsquemaUnificado],
        logger: logging.Logger,
        container_name_aud: str,
    ):
        """
        Inicializa una regla de integración.

        Args:
            name: Nombre del topic de Service Bus que se utilizará para la integración.
            model_unficado: Modelo de esquema unificado para validar y mapear los mensajes recibidos.
            container_name_aud: Nombre del contenedor de la auditoria de cosmos.
        """

        self.name = name
        self.model_unficado = model_unficado
        self.logger = logger
        self.id_esquema = None
        self.container_name_aud = container_name_aud
        self.body_sent = {}

    @abstractmethod
    def integrate(
        self, entrada_esquema_unificado: EntradaEsquemaUnificado
    ) -> Optional[IntegrationResult]:
        pass

    def _validate_modelo_unificado(
        self, message: dict
    ) -> Union[IntegrationResult, EntradaEsquemaUnificado]:
        try:
            message_esquema = self.model_unficado.model_validate(message)
            self.id_esquema = message_esquema.id
            return message_esquema

        except ValidationError as e:
            error_val_cosmos_friendly = serialize_validation_errors(e.errors())
            response = built_valid_json_str_with_aditional_info(
                error_val_cosmos_friendly,
                f"Mensaje no cumple con el esquema {self.model_unficado.__name__}",
            )
            self.logger.error(
                "Error en validación del modelo unificado %s",
                error_val_cosmos_friendly,
                exc_info=True,
            )
            return IntegrationResult(
                success=False,
                response=response,
                bodysent={"error_validacion": True},
            )

    def run(
        self,
        message: Union[ServiceBusMessage, dict],
        cosmos_client: CosmosDBSingleton,
    ):
        """Ejecuta la regla de integración."""
        if isinstance(message, ServiceBusMessage):
            message = json.loads(message.get_body().decode("utf-8"))

        message_esquema = self._validate_modelo_unificado(message)

        if isinstance(message_esquema, IntegrationResult):
            raise ValueError(
                f"Error en validación del modelo unificado. Se recibe un mensaje no valido {message_esquema}"
            )

        try:
            self.id_esquema = message_esquema.id
            result = self._retry_with_exponential_backoff(
                self.integrate, message_esquema
            )
            if self.body_sent is None:
                raise ValueError(
                    "No se ha definido el body_sent. Integrate debe setear el atributo body_sent."
                )
        except ValidationError as e:

            error_val_cosmos_friendly = serialize_validation_errors(e.errors())

            self.logger.error(
                "Error de validación en integración %s",
                error_val_cosmos_friendly,
                exc_info=True,
            )
            result = IntegrationResult(
                success=False,
                response={"error_validacion": error_val_cosmos_friendly},
                bodysent={"error_validacion": True},
            )
        except Exception as e:
            self.logger.error(
                "Error en integración %s",
                e,
                exc_info=True,
            )
            raise e

        self.register_log(result, cosmos_client)
        return result

    def register_log(
        self,
        result: IntegrationResult,
        cosmos_client: CosmosDBSingleton,
    ):
        container = cosmos_client.get_container_client(self.container_name_aud)
        if self.id_esquema is not None:
            entry = AuditoriaEntryIntegracion(
                id=self.id_esquema,
                regla=self.name,
                contenido=result.bodysent,
                sucess=result.success,
                response=result.response,
            )
            item_written = container.upsert_item(
                entry.model_dump(mode="json", exclude_none=True),
            )
            return item_written

        raise ValueError("No es posible usar registro del log.")

    def _retry_with_exponential_backoff(
        self, func, *args, max_retries=3, base_delay=1, **kwargs
    ):
        """Retries a function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    self.logger.warning(
                        "Retrying due to error: %s. Attempt %d/%d. Retrying in %d seconds...",
                        e,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        "Max retries reached. Last error: %s", e, exc_info=True
                    )
                    raise e

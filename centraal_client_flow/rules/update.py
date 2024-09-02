"""Módulo para las reglas de actualización."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional, Set, Tuple, Type

from azure.functions import Blueprint, ServiceBusMessage
from azure.servicebus import ServiceBusMessage as SBMessage
from pydantic import BaseModel, ValidationError

from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton
from centraal_client_flow.connections.service_bus import IServiceBusClient
from centraal_client_flow.helpers.logger import LoggerMixin
from centraal_client_flow.models.schemas import (
    AuditoriaEntry,
    EntradaEsquemaUnificado,
    EventoBase,
    IDModel,
)
from centraal_client_flow.rules import NoHayReglas


class UpdateProcessor(LoggerMixin, ABC):
    """Clase base abstracta para procesadores de eventos."""

    @abstractmethod
    def process_message(
        self, event: EventoBase, current_registro: Optional[EntradaEsquemaUnificado]
    ) -> EntradaEsquemaUnificado:
        """
        Procesa el evento recibido y retorna un modelo actualizado de EntradaEsquemaUnificado.

        Parameters:
            event: El evento que contiene la información del cambio, basado en un modelo Pydantic.
            current_registro: El registro actual que será actualizado.

        Returns:
            EntradaEsquemaUnificado: El registro actualizado después de aplicar el evento.
        """


@dataclass
class Rule:
    """
    Representa una regla de procesamiento que asocia un modelo Pydantic con un procesador
        y los tópicos relevantes.

    Attributes:
        model: El tipo de modelo Pydantic que la regla procesa.
        processor: El procesador que manejará la lógica de actualización.
        topics: Los tópicos a los que la regla está asociada.
    """

    model: Type[EventoBase]
    processor: UpdateProcessor
    topics: Set[str]

    def process_rule(
        self, data: Type[EventoBase], current: EntradaEsquemaUnificado
    ) -> EntradaEsquemaUnificado:
        """
        Procesa una entrada de datos usando la regla definida.

        Parameters:
            data: El evento que se procesará.
            current: El registro actual a ser actualizado.

        Returns:
            EntradaEsquemaUnificado: El registro actualizado.
        """
        return self.processor.process_message(data, current)


class RuleSelector:
    """Clase encargada de seleccionar y aplicar reglas de procesamiento sobre los eventos."""

    def __init__(self, modelo_unificado: EntradaEsquemaUnificado):
        self.rules: List[Rule] = []
        self.modelo_unificado = modelo_unificado

    def register_rule(self, rule: Rule):
        """
        Registra una nueva regla para su uso futuro en el procesamiento de eventos.

        Parameters:
            rule: La regla que se va a registrar.
        """
        self._validate_rule(rule)
        self.rules.append(rule)

    def _validate_rule(self, rule: Rule):
        """
        Valida que los tópicos de la regla coincidan con los subesquemas en el modelo unificado.

        Parameters:
            rule: La regla a validar.

        Raises:
            ValueError: Si algún tópico de la regla no corresponde a un subesquema válido.
        """
        model_fields = set(self.modelo_unificado.model_fields)
        for t in rule.topics:
            if t == "root":
                pass
            elif t not in model_fields:
                raise ValueError(
                    f"El tópico {t} debe corresponder a un subesquema {model_fields}"
                )

    def select_rule(self, data: dict) -> Tuple[EventoBase, Rule]:
        """
        Selecciona la regla adecuada para los datos proporcionados.

        Parameters:
            data: Un diccionario con los datos a validar y procesar.

        Returns:
            Tuple[EventoBase, Rule]: Los datos validados y la regla seleccionada.

        Raises:
            NoHayReglas: Si no se encuentra una regla válida para los datos proporcionados.
        """
        for rule in self.rules:
            try:
                validated_data = rule.model.model_validate(data)
                return validated_data, rule
            except ValidationError:
                continue
        raise NoHayReglas(f"No se encontró una regla válida para {data}.")

    def get_topics_by_changes(
        self,
        rule_topics: Set[str],
        changes: List[AuditoriaEntry],
        include_root: bool = False,
    ) -> List[str]:
        """
        Selecciona los tópicos relevantes basados en los cambios detectados.

        Parameters:
            rule_topics: Conjunto de tópicos definidos en la regla.
            changes: Lista de entradas de auditoría con los cambios detectados.

        Returns:
            List[str]: Lista de tópicos que necesitan ser notificados.
        """
        topics_to_notify = set()

        for change in changes:
            if change.subesquema in rule_topics:
                if include_root:
                    topics_to_notify.add(change.subesquema)
                elif change.subesquema != "root":
                    topics_to_notify.add(change.subesquema)

        return list(topics_to_notify)


class RuleProcessor:
    """Clase que orquesta el procesamiento de reglas y la interacción con Service Bus y Cosmos DB."""

    def __init__(
        self,
        queue_name: str,
        unified_container_name: str,
        auditoria_container_name: str,
        service_bus_client: IServiceBusClient,
        cosmos_client: CosmosDBSingleton,
        rule_selector: RuleSelector,
    ):
        self.queue_name = queue_name
        self.unified_container_name = unified_container_name
        self.auditoria_container_name = auditoria_container_name
        self.service_bus_client = service_bus_client
        self.cosmos_client = cosmos_client
        self.rule_selector = rule_selector

    def register_function(self, bp: Blueprint, bus_connection_name: str):
        """
        Registra una función para procesar mensajes desde una cola de Service Bus.

        Parameters:
            bp: El Blueprint que maneja las funciones de Azure.
            bus_connection_name: nombre del app setting con la conecion del bus

        Returns:
            Blueprint: El Blueprint con la función registrada.
        """
        function_name = f"{self.queue_name}-rule-processor"

        @bp.function_name(name=function_name)
        @bp.service_bus_queue_trigger(
            arg_name="msg",
            queue_name=self.queue_name,
            connection=bus_connection_name,
            is_sessions_enabled=True,
        )
        def process_function(msg: ServiceBusMessage):
            data = json.loads(msg.get_body().decode("utf-8"))
            event_model, rule = self.rule_selector.select_rule(data)
            current_data = self.get_current_entrada(
                event_model.id, self.rule_selector.modelo_unificado
            )
            processed_data = rule.process_rule(event_model, current_data)
            changes = self.detect_changes(current_data, processed_data, event_model.id)

            if len(changes) == 1 and changes[0].subesquema == "No Changes":
                self.record_auditoria(changes)
                return

            self.save_unified_model(processed_data)
            self.record_auditoria(changes)
            topics_to_notify = self.rule_selector.get_topics_by_changes(
                rule.topics, changes
            )
            self.publish_to_topics(processed_data, topics_to_notify)
            return

        return bp

    def save_unified_model(
        self,
        new_data: EntradaEsquemaUnificado,
    ) -> EntradaEsquemaUnificado:
        """
        Guarda el modelo de EntradaEsquemaUnificado actualizado en Cosmos DB.

        Parameters:
            new_data: El modelo actualizado de EntradaEsquemaUnificado.

        Returns:
            EntradaEsquemaUnificado: El modelo almacenado en la base de datos.
        """
        container = self.cosmos_client.get_container_client(self.unified_container_name)
        item_written = container.upsert_item(
            new_data.model_dump(mode="json", exclude_none=True)
        )
        return item_written

    def record_auditoria(self, changes: List[AuditoriaEntry]):
        """
        Registra los cambios detectados en el contenedor de auditoría de Cosmos DB.

        Parameters:
            changes: Lista de entradas de auditoría que contienen los cambios detectados.
        """
        container = self.cosmos_client.get_container_client(
            self.auditoria_container_name
        )
        for change in changes:
            container.create_item(
                change.model_dump(mode="json", exclude_none=True),
                enable_automatic_id_generation=True,
            )

    def get_current_entrada(
        self, id_entrada: IDModel, model_unificado: type[EntradaEsquemaUnificado]
    ) -> Optional[EntradaEsquemaUnificado]:
        """
        Recupera el registro actual desde Cosmos DB basado en el ID proporcionado.

        Parameters:
            id_entrada: El ID del registro que se desea recuperar.

        Returns:
            Optional[EntradaEsquemaUnificado]: El registro actual, si existe.
        """
        container = self.cosmos_client.get_container_client(self.unified_container_name)
        query = f"SELECT * FROM c WHERE c.id = '{id_entrada.model_dump()}'"
        current_items = list(
            container.query_items(query, enable_cross_partition_query=True)
        )

        if current_items:
            return model_unificado.model_validate(current_items[0])
        return None

    def detect_changes(
        self,
        current_data: Optional[EntradaEsquemaUnificado],
        updated_data: EntradaEsquemaUnificado,
        id_model: IDModel,
    ) -> List[AuditoriaEntry]:
        """
        Detecta cambios entre los datos actuales y los actualizados en el modelo EntradaEsquemaUnificado.

        Parameters:
            current_data: Los datos actuales en la base de datos.
            updated_data: Los datos actualizados a comparar.
            id_model: El ID del modelo que se está procesando.

        Returns:
            List[AuditoriaEntry]: Lista de entradas de auditoría que reflejan los cambios detectados.
        """
        changes = []

        def _log_changes(
            subesquema_name: str, old_value: Any, new_value: Any, field_name: str
        ):
            """Función auxiliar para registrar cambios detectados."""
            changes.append(
                AuditoriaEntry(
                    id_entrada=id_model,
                    subesquema=subesquema_name,
                    campo=field_name,
                    new_value=new_value,
                    old_value=old_value,
                )
            )

        if current_data is None:
            # No hay datos actuales, se registran todos los campos como cambios
            for field_name in updated_data.model_fields_set:
                new_value = getattr(updated_data, field_name)
                if isinstance(new_value, BaseModel) and not (
                    isinstance(new_value, IDModel)
                ):
                    # Es un modelo Pydantic anidado (subesquema)
                    for sub_field_name in new_value.model_fields_set:
                        sub_field_value = getattr(new_value, sub_field_name)
                        _log_changes(field_name, None, sub_field_value, sub_field_name)

                else:
                    # Si es principal es "root"
                    _log_changes("root", None, new_value, field_name)
        else:
            for field_name in updated_data.model_fields_set:
                old_value = getattr(current_data, field_name)
                new_value = getattr(updated_data, field_name)
                if isinstance(new_value, BaseModel):
                    # Es un modelo Pydantic anidado (subesquema)
                    for sub_field_name in new_value.model_fields_set:
                        sub_old_value = (
                            getattr(old_value, sub_field_name, None)
                            if old_value
                            else None
                        )
                        sub_new_value = getattr(new_value, sub_field_name, None)
                        if sub_old_value != sub_new_value:
                            _log_changes(
                                field_name, sub_old_value, sub_new_value, sub_field_name
                            )
                else:
                    if old_value != new_value:
                        _log_changes("root", old_value, new_value, field_name)

        if not changes:
            changes.append(
                AuditoriaEntry(
                    id_entrada=id_model,
                    subesquema="No Changes",
                    campo="Ninguno",
                    new_value="No cambios",
                    old_value="No cambios",
                )
            )

        return changes

    def publish_to_topics(
        self,
        processed_data: EntradaEsquemaUnificado,
        topic_names: List[str],
    ):
        """
        Publica los datos procesados a los tópicos de Service Bus relevantes.

        Parameters:
            processed_data: Los datos procesados que se enviarán.
            topic_names: Lista de tópicos a los que se enviarán los datos.
        """
        client = self.service_bus_client.client
        for topic_name in topic_names:
            body = processed_data.model_dump(mode="json", exclude_none=True)
            with client.get_topic_sender(topic_name=topic_name) as sender:
                message = SBMessage(body=json.dumps(body))
                sender.send_messages(message)

"""Module de reglas de actualizacion."""

import json
from typing import Type, List, Tuple, Optional, Any
from abc import ABC, abstractmethod

from azure.functions import Blueprint, ServiceBusMessage
from azure.servicebus import ServiceBusMessage as SBMessage
from pydantic import BaseModel, ValidationError

from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton
from centraal_client_flow.connections.service_bus import IServiceBusClient
from centraal_client_flow.models.schemas import (
    EntradaEsquemaUnificado,
    IDModel,
    EventoBase,
    AuditoriaEntry,
)
from . import NoHayReglas


class UpdateProcessor(ABC):
    """Clase base abstracta para procesadores de eventos."""

    @abstractmethod
    def process_message(self, event: EventoBase) -> EntradaEsquemaUnificado:
        """
        Procesa el evento recibido. y retorna el modelo de EntradaEsquemaUnificado

        Parameters:
            event: Objeto que corresponde a modelo pydantic.
        """


class Rule(BaseModel):
    model: Type[BaseModel]
    processor: UpdateProcessor
    topics: List[str]


class RuleSelector:
    def __init__(self):
        self.rules: List[Rule] = []

    def register_rule(self, rule: Rule):
        """
        Register a rule with its corresponding Pydantic model, processor, and topics.
        """
        self.rules.append(rule)

    def select_rule(self, data: dict) -> Tuple[EntradaEsquemaUnificado, List[str]]:
        """
        Validate data against registered models, process it using the appropriate rule,
        and return the processed data along with the topics to update.
        """
        for rule in self.rules:
            try:
                validated_data = rule.model.model_validate(data)
                processed_data = rule.processor.process_message(validated_data)
                return processed_data, rule.topics
            except ValidationError:
                continue
        raise NoHayReglas(f"No valid rule found for {data}.")


class RuleProcessor:
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

    def register_function(
        self,
        bp: Blueprint,
    ):

        function_name = f"{self.queue_name}-rule-processor"

        @bp.function_name(name=function_name)
        @bp.service_bus_queue_trigger(
            arg_name="msg",
            queue_name=self.queue_name,
            connection=self.cosmos_client.connection_string,
        )
        def process_function(msg: ServiceBusMessage):
            data = json.loads(msg.get_body().decode("utf-8"))
            processed_data, topic_names = self.rule_selector.select_rule(data)

            current_data = self.get_current_entrada(processed_data.id)
            changes = self.detect_changes(current_data, processed_data)

            if current_data is None:
                self.save_unified_model(processed_data)
                self.record_auditoria(changes)
                self.publish_to_topics(processed_data, topic_names)
                return

            if len(changes) == 1 and changes[0].subesquema == "No Changes":
                self.record_auditoria(changes)
                return

        return bp

    def save_unified_model(
        self,
        new_data: EntradaEsquemaUnificado,
    ) -> EntradaEsquemaUnificado:
        """
        Save the updated EntradaEsquemaUnificado model in Cosmos DB.
        """
        container = self.cosmos_client.get_container_client(self.unified_container_name)
        container.upsert_item(new_data.dict())
        return new_data

    def record_auditoria(self, changes: List[AuditoriaEntry]):
        container = self.cosmos_client.get_container_client(
            self.auditoria_container_name
        )
        for change in changes:
            container.create_item(change.model_dump(mode="json", exclude_none=True))

    def get_current_entrada(
        self,
        id_entrada: IDModel,
    ) -> Optional[EntradaEsquemaUnificado]:
        """
        Retrieves the current entry from Cosmos DB and parses it as EntradaEsquemaUnificado.
        """
        container = self.cosmos_client.get_container_client(self.unified_container_name)
        query = f"SELECT * FROM c WHERE c.id = '{str(id_entrada)}'"
        current_items = list(
            container.query_items(query, enable_cross_partition_query=True)
        )

        if current_items:
            return EntradaEsquemaUnificado.model_validate(current_items[0])
        return None

    def detect_changes(
        self,
        current_data: Optional[EntradaEsquemaUnificado],
        updated_data: EntradaEsquemaUnificado,
    ) -> List[AuditoriaEntry]:
        """
        Detects changes between the current and updated EntradaEsquemaUnificado instances.
        If current_data is None, it assumes all fields are new.
        """
        changes = []

        def _log_changes(
            subesquema_name: str, old_value: Any, new_value: Any, field_name: str
        ):
            """Helper function to log changes."""
            changes.append(
                AuditoriaEntry(
                    subesquema=subesquema_name,
                    campo=field_name,
                    new_value=new_value,
                    old_value=old_value,
                )
            )

        if current_data is None:
            # No current data exists, log all fields as changes
            for field_name in updated_data.model_fields_set:
                new_value = getattr(updated_data, field_name)
                if isinstance(new_value, BaseModel) and not (
                    isinstance(new_value, IDModel)
                ):
                    # It's a nested Pydantic model (subesquema)
                    for sub_field_name in new_value.model_fields_set:
                        sub_field_value = getattr(new_value, sub_field_name)
                        _log_changes(field_name, None, sub_field_value, sub_field_name)

                else:
                    _log_changes(field_name, None, new_value, field_name)
        else:
            # Compare each field between current and updated data
            for field_name in updated_data.model_fields_set:
                old_value = getattr(current_data, field_name)
                new_value = getattr(updated_data, field_name)
                if isinstance(new_value, BaseModel):
                    # It's a nested Pydantic model (subesquema)
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
                        _log_changes(field_name, old_value, new_value, field_name)

        if not changes:
            changes.append(
                AuditoriaEntry(
                    subesquema="No Changes",
                    campo="No changes detected between current and updated data.",
                    valor=None,
                )
            )

        return changes

    def publish_to_topics(
        self,
        processed_data,
        topic_names: List[str],
    ):
        client = self.service_bus_client
        for topic_name in topic_names:
            with client.get_topic_sender(topic_name=topic_name) as sender:
                message = SBMessage(processed_data)
                sender.send_messages(message)

    def close(self):
        # Método para cerrar la conexión del cliente Service Bus y Cosmos DB cuando ya no se necesite
        self.service_bus_client.close()
        self.cosmos_client.client.close()

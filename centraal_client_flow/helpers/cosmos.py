"""Helpers para interactuar con cosmos."""

from typing import Type

from azure.cosmos.container import ContainerProxy
from pydantic import BaseModel

from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton


def write_model_to_cosmos(
    container_client: ContainerProxy, model_instance: Type[BaseModel]
) -> dict:
    """Writes a Pydantic model instance to the specified Cosmos DB container."""
    return container_client.upsert_item(
        body=model_instance.model_dump(mode="json", exclude_none=True)
    )


def save_model_to_cosmos(
    cosmos_db: CosmosDBSingleton, container_name: str, model_instance: Type[BaseModel]
) -> dict:
    """Saves a Pydantic model instance to the specified Cosmos DB container."""
    container_client = cosmos_db.get_container_client(container_name)
    item_written = write_model_to_cosmos(container_client, model_instance)
    return item_written

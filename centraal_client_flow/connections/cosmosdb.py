"""Modulo de conexión a cosmos."""

import os
from threading import Lock
from typing import Optional

from azure.cosmos.container import ContainerProxy
from azure.cosmos.cosmos_client import CosmosClient


class CosmosDBSingleton:
    """Singleton class for Cosmos DB client."""

    _instance: Optional["CosmosDBSingleton"] = None
    _lock: Lock = Lock()

    def __new__(
        cls,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> "CosmosDBSingleton":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = False
            self.client: Optional[CosmosClient] = None
            self.database: Optional[CosmosClient] = None
            self.connection_string = connection_string or os.getenv(
                "COSMOS_CONNECTION_STRING"
            )
            self.database_name = database_name or os.getenv("DATABASE_NAME")

    def _initialize(self) -> None:
        """Initialize the Cosmos DB client and database."""
        if self.client is None or self.database is None:
            if not self.connection_string or not self.database_name:
                raise ValueError("Connection string and database name must be provided")

            self.client = CosmosClient.from_connection_string(self.connection_string)
            self.database = self.client.get_database_client(self.database_name)
            self._initialized = True

    def get_container_client(self, container_name: str) -> ContainerProxy:
        """Get a container client."""
        self._initialize()
        return self.database.get_container_client(container_name)

    def set_mock_client(
        self, mock_client: CosmosClient, mock_database: CosmosClient
    ) -> None:
        """Set a mock client and database for testing purposes."""
        self.client = mock_client
        self.database = mock_database

"""Test para cosmos."""

# pylint: disable=C0116
from unittest.mock import MagicMock, patch

import pytest
from azure.cosmos import CosmosClient
from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton


@pytest.fixture(autouse=True)
def reset_singleton():
    CosmosDBSingleton._instance = None


@pytest.fixture(name="mock_cosmos_client")
def mock_cosmos_client_fix():
    with patch("centraal_client_flow.connections.cosmosdb.CosmosClient") as mock:
        yield mock


@pytest.fixture(name="cosmosdb_singleton")
def cosmosdb_singleton_fix():
    return CosmosDBSingleton("mock_connection_string", "mock_database_name")


def test_singleton_behavior(cosmosdb_singleton):
    instance1 = cosmosdb_singleton
    instance2 = CosmosDBSingleton("mock_connection_string", "mock_database_name")
    assert instance1 is instance2


def test_initialization(cosmosdb_singleton, mock_cosmos_client):
    mock_database_client = MagicMock()
    mock_cosmos_client.from_connection_string.return_value.get_database_client.return_value = (
        mock_database_client
    )

    cosmosdb_singleton._initialize()

    mock_cosmos_client.from_connection_string.assert_called_once_with(
        "mock_connection_string"
    )
    mock_cosmos_client.from_connection_string.return_value.get_database_client.assert_called_once_with(
        "mock_database_name"
    )
    assert (
        cosmosdb_singleton.client
        == mock_cosmos_client.from_connection_string.return_value
    )
    assert cosmosdb_singleton.database == mock_database_client


def test_get_container_client(cosmosdb_singleton, mock_cosmos_client):

    mock_container_client = MagicMock()
    mock_database_client = MagicMock()
    mock_database_client.get_container_client.return_value = mock_container_client

    mock_cosmos_client.from_connection_string.return_value.get_database_client.return_value = (
        mock_database_client
    )

    # Act: Retrieve a container client
    cosmosdb_singleton._initialize()
    container_client = cosmosdb_singleton.get_container_client("mock_container_name")

    # Assert: Ensure the methods were called with expected arguments
    mock_database_client.get_container_client.assert_called_once_with(
        "mock_container_name"
    )
    assert container_client == mock_container_client


def test_set_mock_client(cosmosdb_singleton):
    # Arrange: Create mock client and database objects
    mock_client = MagicMock(spec=CosmosClient)
    mock_database = MagicMock()

    # Act: Set the mock client and database
    cosmosdb_singleton.set_mock_client(mock_client, mock_database)

    # Assert: Ensure the instance's client and database were set correctly
    assert cosmosdb_singleton.client == mock_client
    assert cosmosdb_singleton.database == mock_database

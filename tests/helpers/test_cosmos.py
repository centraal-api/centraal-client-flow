""""Test para helpers."""

from unittest.mock import MagicMock, patch
from typing import Optional

import pytest
from pydantic import BaseModel

from centraal_client_flow.helpers.cosmos import (
    write_model_to_cosmos,
    save_model_to_cosmos,
)


class SampleModel(BaseModel):
    """A sample Pydantic model for testing."""

    id: str
    name: str
    description: Optional[str] = None


@pytest.fixture(name="mock_container_client")
def mock_container_client_fix():
    """Fixture to provide a mocked ContainerProxy client."""
    return MagicMock()


@pytest.fixture(name="mock_cosmos_db")
def mock_cosmos_db_fix():
    """Fixture to provide a mocked CosmosDBSingleton instance."""
    mock_cosmos = MagicMock()
    return mock_cosmos


def test_write_model_to_cosmos(mock_container_client):
    """Test the write_model_to_cosmos function with a mock container client."""
    model_instance = SampleModel(id="1", name="Test Model")

    mock_container_client.upsert_item.return_value = {"id": "1", "name": "Test Model"}

    result = write_model_to_cosmos(mock_container_client, model_instance)

    mock_container_client.upsert_item.assert_called_once()
    assert result == {"id": "1", "name": "Test Model"}


def test_save_model_to_cosmos(mock_cosmos_db, mock_container_client):
    """Test the save_model_to_cosmos function with mocked CosmosDB and container client."""
    container_name = "test_container"
    model_instance = SampleModel(id="1", name="Test Model")

    mock_cosmos_db.get_container_client.return_value = mock_container_client

    mock_container_client.upsert_item.return_value = {"id": "1", "name": "Test Model"}

    with patch(
        "centraal_client_flow.helpers.cosmos.write_model_to_cosmos",
        return_value={"id": "1", "name": "Test Model"},
    ) as mock_write:
        result = save_model_to_cosmos(mock_cosmos_db, container_name, model_instance)

        mock_cosmos_db.get_container_client.assert_called_once_with(container_name)
        mock_write.assert_called_once_with(mock_container_client, model_instance)
        assert result == {"id": "1", "name": "Test Model"}

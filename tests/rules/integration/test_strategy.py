"""Suite de test para integration."""

from unittest.mock import MagicMock, patch
import pytest

from pydantic import BaseModel
import requests

from centraal_client_flow.models.schemas import EntradaEsquemaUnificado, IDModel
from centraal_client_flow.rules.integration.strategy import (
    RESTIntegration,
    OAuthConfigPassFlow,
    OAuthTokenPass,
)


class MockOutputModel(BaseModel):
    """Mock model for testing output."""

    field1: str
    field2: int


class IDExample(IDModel):
    doc: int
    tipo: int


@pytest.fixture(name="mock_oauth_config")
def fixture_mock_oauth_config():
    """Fixture for mock OAuth configuration."""
    return OAuthConfigPassFlow(
        client_id="test_client_id",
        client_secret="test_client_secret",
        username="test_username",
        password="test_password",
        token_resource="test_token_resource",
        api_url="https://example.com/api",
    )


@pytest.fixture(name="mock_token_response")
def fixture_mock_token_response():
    """Fixture for mock OAuth token response."""
    return {
        "access_token": "test_access_token",
        "instance_url": "https://example.com",
        "id": "test_id",
        "token_type": "Bearer",
        "issued_at": 1234567890,
        "signature": "test_signature",
    }


@pytest.fixture(name="mock_integration_strategy")
def fixture_mock_integration_strategy(mock_oauth_config):
    """Fixture for mock RESTIntegration instance."""
    return RESTIntegration(
        oauth_config=mock_oauth_config,
        method="POST",
        resource="test_resource",
        mapping_function=lambda x: MockOutputModel(
            field1=str(x.id.doc), field2=x.id.tipo
        ),
    )


def test_authenticate_success(mock_integration_strategy, mock_token_response):
    """Test successful authentication and token retrieval."""
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_token_response

        token = mock_integration_strategy._authenticate()

        assert isinstance(token, OAuthTokenPass)
        assert token.access_token == "test_access_token"


def test_authenticate_failure(mock_integration_strategy):
    """Test authentication failure raises HTTPError."""
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 401
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError

        with pytest.raises(requests.HTTPError):
            mock_integration_strategy._authenticate()


def test_modelo_unificado_mapping(mock_integration_strategy):
    """Test modelo_unificado_mapping method."""
    message = EntradaEsquemaUnificado(id=IDExample(doc=1, tipo=2))
    result = mock_integration_strategy.modelo_unificado_mapping(message)

    assert isinstance(result, MockOutputModel)
    assert result.field1 == "1"
    assert result.field2 == 2


def test_modelo_unificado_mapping_invalid_message(mock_integration_strategy):
    """Test that modelo_unificado_mapping raises TypeError with invalid input."""
    with pytest.raises(TypeError):
        mock_integration_strategy.modelo_unificado_mapping("invalid input")


def test_integrate_success(mock_integration_strategy, mock_token_response):
    """Test successful integration and response handling."""
    output_model = MockOutputModel(field1="Test", field2=1)

    with patch("requests.request") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"success": True}
        mock_post.return_value.raise_for_status = MagicMock()

        with patch.object(
            mock_integration_strategy, "_get_token", return_value="test_access_token"
        ):
            response = mock_integration_strategy.integrate(output_model)

            assert response == {"success": True}


def test_integrate_failure(mock_integration_strategy):
    """Test integration failure raises HTTPError."""
    output_model = MockOutputModel(field1="Test", field2=1)

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError

        with patch.object(
            mock_integration_strategy, "_get_token", return_value="test_access_token"
        ):
            with pytest.raises(requests.HTTPError):
                mock_integration_strategy.integrate(output_model)

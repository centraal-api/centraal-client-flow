# test_integration_rule.py

from typing_extensions import Self
from unittest.mock import MagicMock


import pytest
import json

from azure.functions import ServiceBusMessage
from pydantic import BaseModel, model_validator

from centraal_client_flow.rules.integration.v2 import IntegrationRule, IntegrationResult
from centraal_client_flow.models.schemas import EntradaEsquemaUnificado, IDModel
from centraal_client_flow.connections.cosmosdb import CosmosDBSingleton


class MockIntegrationRule(IntegrationRule):
    def integrate(
        self, entrada_esquema_unificado: EntradaEsquemaUnificado
    ) -> IntegrationResult:
        return IntegrationResult(
            success=True,
            response={"status": "success", "code": 200},
            bodysent={"status": "success", "code": 200},
        )


class MockModelRaiseError(BaseModel):
    id: str

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        raise ValueError("Error en validación del modelo unificado")


class MockIntegrationRuleModelValidator(IntegrationRule):
    def integrate(
        self, entrada_esquema_unificado: EntradaEsquemaUnificado
    ) -> IntegrationResult:

        MockModelRaiseError(id="123")
        return IntegrationResult(
            success=True,
            response={"status": "success", "code": 200},
            bodysent={"status": "success", "code": 200},
        )


class MockData(BaseModel):
    data: str


class MockIDModel(IDModel):
    id: str = "testid"


class MockEntradaEsquemaUnificado(EntradaEsquemaUnificado):
    id: MockIDModel
    data: MockData


@pytest.fixture
def mock_entrada_esquema():
    return MockEntradaEsquemaUnificado()


@pytest.fixture
def setup_integration_rule() -> tuple[IntegrationRule, MagicMock]:
    logger = MagicMock()
    cosmos_client = MagicMock(spec=CosmosDBSingleton)
    rule = MockIntegrationRule(
        name="test_topic",
        model_unficado=MockEntradaEsquemaUnificado,
        logger=logger,
        container_name_aud="test_container",
    )
    return rule, cosmos_client


def test_run_success(setup_integration_rule: tuple[IntegrationRule, MagicMock]):
    rule, cosmos_client = setup_integration_rule
    message = {"id": "123", "data": {"data": "test"}}
    result = rule.run(message, cosmos_client)
    assert result.success is True


def test_run_success_with_service_bus_message(
    setup_integration_rule: tuple[IntegrationRule, MagicMock]
):
    rule, cosmos_client = setup_integration_rule
    message_content = {"id": "123", "data": {"data": "test"}}
    message = ServiceBusMessage(body=json.dumps(message_content))
    result = rule.run(message, cosmos_client)
    assert result.success is True


def test_register_log(setup_integration_rule):
    rule, cosmos_client = setup_integration_rule
    result = IntegrationResult(
        success=True,
        response={"status": "success", "code": 200},
        bodysent={"id": "test"},
    )
    rule.id_esquema = MockIDModel(id="123")
    rule.register_log(result, cosmos_client)
    cosmos_client.get_container_client.assert_called_with("test_container")


def test_run_validation_error(setup_integration_rule):
    rule, cosmos_client = setup_integration_rule
    message = {"id": "123", "data": {"datas": "test"}}

    with pytest.raises(ValueError) as exc_info:
        rule.run(message, cosmos_client)

    assert "Error en validación del modelo unificado" in str(exc_info.value)


def test_retry_with_exponential_backoff(setup_integration_rule):
    rule, _ = setup_integration_rule
    func = MagicMock(side_effect=[Exception("fail"), "success"])
    result = rule._retry_with_exponential_backoff(func)
    assert result == "success"
    assert func.call_count == 2


@pytest.fixture
def setup_integration_rule_model_validator() -> tuple[IntegrationRule, MagicMock]:
    logger = MagicMock()
    cosmos_client = MagicMock(spec=CosmosDBSingleton)
    rule = MockIntegrationRuleModelValidator(
        name="test_topic",
        model_unficado=MockEntradaEsquemaUnificado,
        logger=logger,
        container_name_aud="test_container",
    )
    return rule, cosmos_client


def test_run_success_model_validator(
    setup_integration_rule_model_validator: tuple[IntegrationRule, MagicMock]
):
    rule, cosmos_client = setup_integration_rule_model_validator
    message = {"id": "123", "data": {"data": "test"}}
    result = rule.run(message, cosmos_client)
    assert result.success is False

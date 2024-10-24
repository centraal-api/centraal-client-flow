"""Tests for the ServiceBusClientSingleton class."""

# pylint: disable=C0116
from unittest.mock import patch, MagicMock

import pytest
from azure.servicebus import ServiceBusMessage

from centraal_client_flow.connections.service_bus import ServiceBusClientSingleton


@pytest.fixture(name="connection_str")
def connection_str_fix() -> str:
    return "Endpoint=sb://t.servicebus.windows.net/;SharedAccessKeyName=key;SharedAccessKey=key"


@pytest.fixture(name="mock_service_bus_client")
def mock_service_bus_client_fix():
    mock_sender = MagicMock()
    with patch("centraal_client_flow.connections.service_bus.ServiceBusClient") as mock:
        mock.from_connection_string.return_value.get_queue_sender.return_value = (
            mock_sender
        )
        yield mock


@pytest.fixture(name="service_bus_client_singleton")
def service_bus_client_singleton_fix(mock_service_bus_client, connection_str: str):
    return ServiceBusClientSingleton(connection_str)


def test_singleton_instance(mock_service_bus_client, connection_str: str):
    instance1 = ServiceBusClientSingleton(connection_str)
    instance2 = ServiceBusClientSingleton(connection_str)
    assert instance1 is instance2


def test_send_message_to_queue(service_bus_client_singleton):

    message = {"key": "value"}
    session_id = "session123"
    queue_name = "test-queue"

    service_bus_client_singleton.send_message_to_queue(message, session_id, queue_name)
    mock_sender = service_bus_client_singleton.senders[queue_name]

    assert mock_sender.send_messages.call_count == 1
    sent_message = mock_sender.send_messages.call_args[0][0]
    assert isinstance(sent_message, ServiceBusMessage)
    assert sent_message.session_id == session_id
    # probar el cierre
    service_bus_client_singleton.close()
    mock_sender.close.assert_called_once()

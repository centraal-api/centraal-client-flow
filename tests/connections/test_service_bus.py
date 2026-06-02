"""Tests for the ServiceBusClientSingleton class."""

# pylint: disable=C0116
import json
import threading
from unittest.mock import patch, MagicMock

import pytest
from azure.servicebus import ServiceBusMessage
from azure.servicebus.exceptions import MessageSizeExceededError

from centraal_client_flow.connections.service_bus import ServiceBusClientSingleton


@pytest.fixture(autouse=True)
def reset_service_bus_singleton_between_tests():
    """El singleton es proceso-global; sin reset los tests comparten mock/client viejos."""
    ServiceBusClientSingleton._instance = None
    yield
    ServiceBusClientSingleton._instance = None


@pytest.fixture(name="connection_str")
def connection_str_fix() -> str:
    return "Endpoint=sb://t.servicebus.windows.net/;SharedAccessKeyName=key;SharedAccessKey=key"


@pytest.fixture(name="mock_service_bus_client")
def mock_service_bus_client_fix():
    mock_sender = MagicMock()
    # get_queue_sender retorna un context manager (with ... as sender)
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_sender
    mock_cm.__exit__.return_value = False
    with patch("centraal_client_flow.connections.service_bus.ServiceBusClient") as mock:
        mock.from_connection_string.return_value.get_queue_sender.return_value = mock_cm
        yield mock


@pytest.fixture(name="service_bus_client_singleton")
def service_bus_client_singleton_fix(mock_service_bus_client, connection_str: str):
    return ServiceBusClientSingleton(connection_str)


def test_singleton_instance(mock_service_bus_client, connection_str: str):
    instance1 = ServiceBusClientSingleton(connection_str)
    instance2 = ServiceBusClientSingleton(connection_str)
    assert instance1 is instance2


def test_get_sender_returns_new_sender_each_time(service_bus_client_singleton, mock_service_bus_client):
    """get_sender no cachea: cada llamada devuelve un sender nuevo (get_queue_sender)."""
    queue_name = "test-queue"
    client = mock_service_bus_client.from_connection_string.return_value

    with service_bus_client_singleton.get_sender(queue_name) as sender:
        sender.send_messages(MagicMock())

    with service_bus_client_singleton.get_sender(queue_name) as sender2:
        sender2.send_messages(MagicMock())

    assert client.get_queue_sender.call_count == 2
    client.get_queue_sender.assert_called_with(queue_name)


def test_send_message_to_queue(service_bus_client_singleton, mock_service_bus_client):

    message = {"key": "value"}
    session_id = "session123"
    queue_name = "test-queue"

    service_bus_client_singleton.send_message_to_queue(message, session_id, queue_name)

    client = mock_service_bus_client.from_connection_string.return_value
    client.get_queue_sender.assert_called_once_with(queue_name)
    mock_sender = client.get_queue_sender.return_value.__enter__.return_value
    assert mock_sender.send_messages.call_count == 1
    sent_message = mock_sender.send_messages.call_args[0][0]
    assert isinstance(sent_message, ServiceBusMessage)
    assert sent_message.session_id == session_id

    service_bus_client_singleton.close()
    client.close.assert_called_once()


def test_concurrent_send_message_to_queue(service_bus_client_singleton, mock_service_bus_client):
    """Varios hilos enviando no deben fallar ni quedar bloqueados (regresión de carrera AMQP)."""
    errors = []

    def worker():
        try:
            service_bus_client_singleton.send_message_to_queue({"k": "v"}, "sess", "test-queue")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors
    assert all(not t.is_alive() for t in threads)


def test_send_messages_batch_to_queue(service_bus_client_singleton, mock_service_bus_client):
    mock_batch = MagicMock()
    mock_batch.__len__.return_value = 3

    client = mock_service_bus_client.from_connection_string.return_value
    mock_sender = client.get_queue_sender.return_value.__enter__.return_value
    mock_sender.create_message_batch.return_value = mock_batch

    items = [
        ({"key": "a"}, "sess-a"),
        ({"key": "b"}, "sess-b"),
        ({"key": "c"}, "sess-c"),
    ]
    queue_name = "test-queue"

    sent = service_bus_client_singleton.send_messages_batch_to_queue(items, queue_name)

    assert sent == 3
    client.get_queue_sender.assert_called_once_with(queue_name)
    mock_sender.create_message_batch.assert_called_once()
    assert mock_batch.add_message.call_count == 3
    mock_sender.send_messages.assert_called_once_with(mock_batch)

    added_messages = [call.args[0] for call in mock_batch.add_message.call_args_list]
    assert all(isinstance(message, ServiceBusMessage) for message in added_messages)
    assert added_messages[0].session_id == "sess-a"
    assert json.loads(str(added_messages[0])) == {"key": "a"}


def test_send_messages_batch_size_exceeded(service_bus_client_singleton, mock_service_bus_client):
    mock_batch_1 = MagicMock()
    mock_batch_1.__len__.return_value = 2
    mock_batch_2 = MagicMock()
    mock_batch_2.__len__.return_value = 1
    add_count = {"n": 0}

    def add_side_effect(_msg):
        add_count["n"] += 1
        if add_count["n"] == 3:
            raise MessageSizeExceededError()

    mock_batch_1.add_message.side_effect = add_side_effect

    client = mock_service_bus_client.from_connection_string.return_value
    mock_sender = client.get_queue_sender.return_value.__enter__.return_value
    mock_sender.create_message_batch.side_effect = [mock_batch_1, mock_batch_2]

    items = [
        ({"key": "a"}, "sess-a"),
        ({"key": "b"}, "sess-b"),
        ({"key": "c"}, "sess-c"),
    ]

    sent = service_bus_client_singleton.send_messages_batch_to_queue(items, "test-queue")

    assert sent == 3
    assert mock_sender.create_message_batch.call_count == 2
    assert mock_sender.send_messages.call_count == 2
    mock_sender.send_messages.assert_any_call(mock_batch_1)
    mock_sender.send_messages.assert_any_call(mock_batch_2)
    mock_batch_2.add_message.assert_called_once()


def test_send_messages_batch_empty(service_bus_client_singleton, mock_service_bus_client):
    sent = service_bus_client_singleton.send_messages_batch_to_queue([], "test-queue")

    assert sent == 0
    client = mock_service_bus_client.from_connection_string.return_value
    client.get_queue_sender.assert_not_called()


def test_send_messages_batch_normalizes_session_id(
    service_bus_client_singleton, mock_service_bus_client
):
    mock_batch = MagicMock()
    mock_batch.__len__.return_value = 1

    client = mock_service_bus_client.from_connection_string.return_value
    mock_sender = client.get_queue_sender.return_value.__enter__.return_value
    mock_sender.create_message_batch.return_value = mock_batch

    service_bus_client_singleton.send_messages_batch_to_queue(
        [({"key": "value"}, 12345)],
        "test-queue",
    )

    added_message = mock_batch.add_message.call_args[0][0]
    assert added_message.session_id == "12345"


def test_concurrent_send_messages_batch_to_queue(
    service_bus_client_singleton, mock_service_bus_client
):
    """Varios hilos enviando batches no deben fallar ni quedar bloqueados."""
    mock_batch = MagicMock()
    mock_batch.__len__.return_value = 1

    client = mock_service_bus_client.from_connection_string.return_value
    mock_sender = client.get_queue_sender.return_value.__enter__.return_value
    mock_sender.create_message_batch.return_value = mock_batch

    errors = []

    def worker(index):
        try:
            service_bus_client_singleton.send_messages_batch_to_queue(
                [({"k": index}, f"sess-{index}")],
                "test-queue",
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)

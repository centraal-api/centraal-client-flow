"""Test para Rule class."""

# pylint: disable=missing-docstring
from unittest.mock import Mock
from typing import Optional, Set

import pytest
from pydantic import BaseModel

from centraal_client_flow.models.schemas import (
    EventoBase,
    EntradaEsquemaUnificado,
    IDModel,
)
from centraal_client_flow.rules.update import Rule, UpdateProcessor


class TestIDModel(IDModel):
    """Test ID model."""

    cliente_id: str
    producto_id: str


class TestEventoBase(EventoBase):
    """Test evento model."""

    id: TestIDModel
    data: str


class Maestra(BaseModel):
    """Test maestra model."""
    info: str


class TestEntradaEsquemaUnificado(EntradaEsquemaUnificado):
    """Test entrada esquema unificado model."""

    id: TestIDModel
    maestra: Maestra


class MockUpdateProcessor(UpdateProcessor):
    """Mock update processor for testing."""

    def process_message(
        self, event: EventoBase, current_registro: Optional[EntradaEsquemaUnificado]
    ) -> EntradaEsquemaUnificado:
        """Mock implementation that returns updated registro."""
        # Simple implementation for testing
        if current_registro is None:
            # Create new entrada when current is None
            current_registro = TestEntradaEsquemaUnificado(
                id=event.id,
                maestra=Maestra(info=f"new_processed_{event.data}")
            )
        else:
            # Update existing entrada
            current_registro.maestra.info = f"processed_{event.data}"
        return current_registro


@pytest.fixture(name="mock_processor")
def mock_processor_fixture():
    """Fixture for mock processor."""
    return MockUpdateProcessor()


@pytest.fixture(name="test_topics")
def test_topics_fixture():
    """Fixture for test topics."""
    return {"topic1", "topic2", "root"}


@pytest.fixture(name="sample_event")
def sample_event_fixture():
    """Fixture for sample event."""
    test_id = TestIDModel(cliente_id="CLI001", producto_id="PROD001")
    return TestEventoBase(id=test_id, data="test_data")


@pytest.fixture(name="sample_entrada")
def sample_entrada_fixture():
    """Fixture for sample entrada esquema unificado."""
    test_id = TestIDModel(cliente_id="CLI001", producto_id="PROD001")
    return TestEntradaEsquemaUnificado(id=test_id, maestra=Maestra(info="original_info"))


@pytest.fixture(name="rule")
def rule_fixture(mock_processor, test_topics):
    """Fixture for Rule instance."""
    return Rule(
        model=TestEventoBase,
        processor=mock_processor,
        topics=test_topics
    )


class TestRule:
    """Test cases for Rule class."""

    def test_rule_initialization(self, mock_processor, test_topics):
        """Test Rule initialization with all required parameters."""
        rule = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics=test_topics
        )

        assert rule.model == TestEventoBase
        assert rule.processor == mock_processor
        assert rule.topics == test_topics
        assert rule.name == "TestEventoBase"

    def test_post_init_sets_name_from_model(self, mock_processor, test_topics):
        """Test that __post_init__ sets name from model class name."""
        rule = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics=test_topics
        )

        assert rule.name == "TestEventoBase"

    def test_process_rule_calls_processor(self, rule, sample_event, sample_entrada):
        """Test that process_rule calls processor.process_message correctly."""
        result = rule.process_rule(sample_event, sample_entrada)

        assert isinstance(result, TestEntradaEsquemaUnificado)
        assert result.maestra.info == "processed_test_data"
        assert result.id == sample_event.id

    def test_process_rule_with_none_current(self, sample_event):
        """Test process_rule behavior when current is None."""
        # Use our MockUpdateProcessor that handles None properly
        mock_processor = MockUpdateProcessor()

        rule_with_mock = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics={"topic1"}
        )

        result = rule_with_mock.process_rule(sample_event, None)

        # Verify result is created properly when current is None
        assert isinstance(result, TestEntradaEsquemaUnificado)
        assert result.maestra.info == "new_processed_test_data"
        assert result.id == sample_event.id

    def test_process_rule_with_mock_processor(self, sample_event):
        """Test process_rule with a mocked processor to verify deep copies."""
        test_id = TestIDModel(cliente_id="CLI001", producto_id="PROD001")
        new_entrada = TestEntradaEsquemaUnificado(id=test_id, maestra=Maestra(info="new_info"))

        # Mock the processor to handle None current
        mock_processor = Mock(spec=UpdateProcessor)
        mock_processor.process_message.return_value = new_entrada

        rule_with_mock = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics={"topic1"}
        )

        result = rule_with_mock.process_rule(sample_event, None)

        # Verify processor was called with deep copies
        mock_processor.process_message.assert_called_once()
        call_args = mock_processor.process_message.call_args[0]

        # Verify the event was passed (should be a deep copy)
        assert isinstance(call_args[0], TestEventoBase)
        assert call_args[0].data == sample_event.data
        assert call_args[0] is not sample_event  # Should be different instance

        # Verify None was passed for current
        assert call_args[1] is None

        assert result == new_entrada

    def test_process_rule_creates_deep_copies(self, sample_event, sample_entrada):
        """Test that process_rule creates deep copies of inputs."""
        mock_processor = Mock(spec=UpdateProcessor)
        mock_processor.process_message.return_value = sample_entrada

        rule = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics={"topic1"}
        )

        original_event_data = sample_event.data
        original_entrada_info = sample_entrada.maestra.info

        rule.process_rule(sample_event, sample_entrada)

        # Verify original objects weren't modified
        assert sample_event.data == original_event_data
        assert sample_entrada.maestra.info == original_entrada_info

        # Verify processor was called with copies
        mock_processor.process_message.assert_called_once()
        call_args = mock_processor.process_message.call_args[0]

        # The objects passed should be different instances (deep copies)
        assert call_args[0] is not sample_event
        assert call_args[1] is not sample_entrada

    def test_topics_reference_behavior(self, mock_processor):
        """Test that topics set behavior - Rule stores reference to the original set."""
        original_topics = {"topic1", "topic2"}
        rule = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics=original_topics
        )

        # Topics should be the same set reference
        assert rule.topics == original_topics
        assert rule.topics is original_topics

        # Modifying original topics will affect rule topics (since it's the same object)
        original_topics.add("topic3")
        assert "topic3" in rule.topics
        assert rule.topics == {"topic1", "topic2", "topic3"}

    def test_topics_independent_sets(self, mock_processor):
        """Test behavior when using independent sets for topics."""
        topics1 = {"topic1", "topic2"}
        topics2 = {"topic1", "topic2"}  # Same content, different set object

        rule1 = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics=topics1
        )

        rule2 = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics=topics2
        )

        # Both rules should have same topics content
        assert rule1.topics == rule2.topics

        # But different set objects
        assert rule1.topics is not rule2.topics

        # Modifying one shouldn't affect the other
        topics1.add("topic3")
        assert "topic3" in rule1.topics
        assert "topic3" not in rule2.topics

    def test_rule_with_different_event_types(self, mock_processor, test_topics):
        """Test Rule with different EventoBase subclasses."""
        class AnotherEventoBase(EventoBase):
            id: TestIDModel
            different_field: int

        rule = Rule(
            model=AnotherEventoBase,
            processor=mock_processor,
            topics=test_topics
        )

        assert rule.model == AnotherEventoBase
        assert rule.name == "AnotherEventoBase"

    def test_rule_string_representation(self, rule):
        """Test that Rule has reasonable string representation."""
        rule_str = str(rule)
        assert "Rule" in rule_str
        assert "TestEventoBase" in rule_str or rule.name in rule_str


class TestRuleIntegration:
    """Integration tests for Rule class."""

    def test_full_processing_workflow(self):
        """Test complete workflow from event to processed result."""
        # Setup
        test_id = TestIDModel(cliente_id="CLI001", producto_id="PROD001")
        event = TestEventoBase(id=test_id, data="integration_test")
        current = TestEntradaEsquemaUnificado(id=test_id, maestra=Maestra(info="original"))

        processor = MockUpdateProcessor()
        topics = {"integration_topic"}

        rule = Rule(
            model=TestEventoBase,
            processor=processor,
            topics=topics
        )

        # Execute
        result = rule.process_rule(event, current)

        # Verify
        assert isinstance(result, TestEntradaEsquemaUnificado)
        assert result.maestra.info == "processed_integration_test"
        assert result.id == test_id
        assert rule.name == "TestEventoBase"

    def test_rule_equality_and_comparison(self, mock_processor, test_topics):
        """Test Rule equality and comparison behavior."""
        rule1 = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics=test_topics
        )

        rule2 = Rule(
            model=TestEventoBase,
            processor=mock_processor,
            topics=test_topics
        )

        # Different processor instance, should not be equal
        another_processor = MockUpdateProcessor()
        rule3 = Rule(
            model=TestEventoBase,
            processor=another_processor,
            topics=test_topics
        )

        # Rules with same processor instance should be equal
        assert rule1 == rule2
        # Rules with different processor instances should not be equal
        assert rule1 != rule3

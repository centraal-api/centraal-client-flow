"""Tests para el modulo helpers/pydantic.py."""

import json
from typing import List

import pytest

from pydantic_core import ErrorDetails
from centraal_client_flow.helpers.pydantic import (
    serialize_validation_errors,
    built_valid_json_str_with_aditional_info,
)


@pytest.fixture(name="errors")
def errors_fixture() -> List[ErrorDetails]:
    return [
        ErrorDetails(
            type="value_error.missing",
            loc=("body", "username"),
            msg="field required",
            input=None,
            ctx={"error": ValueError("Error modelo unificado")},
        ),
        ErrorDetails(
            type="type_error.integer",
            loc=("body", "age"),
            msg="value is not a valid integer",
            input=None,
            ctx={},
        ),
    ]


@pytest.fixture(name="expected_json")
def expected_json_fixture() -> str:
    return (
        '[{"type": "value_error.missing", "loc": ["body", "username"], "msg": "field required", "input": null, '
        '"ctx": {"error": {"error_type": "ValueError", "error_message": "Error modelo unificado"}}}, '
        '{"type": "type_error.integer", "loc": ["body", "age"], "msg": "value is not a valid integer", "input": null, "ctx": {}}]'
    )


def test_serialize_validation_errors(errors: List[ErrorDetails], expected_json: str):

    assert serialize_validation_errors(errors) == expected_json


def test_serialize_validation_errors_empty():
    errors = []
    expected_json = "[]"
    assert serialize_validation_errors(errors) == expected_json


def test_serialize_validation_errors_unicode():
    errors = [
        ErrorDetails(
            type="value_error.missing",
            loc=("body", "mensaje"),
            msg="campo requerido",
            input=None,
            ctx={},
        )
    ]

    expected_json = '[{"type": "value_error.missing", "loc": ["body", "mensaje"], "msg": "campo requerido", "input": null, "ctx": {}}]'
    assert serialize_validation_errors(errors) == expected_json


def test_built_valid_json_str_with_aditional_info(errors: List[ErrorDetails]):
    error_message = serialize_validation_errors(errors)
    additional_info = "Detalle del error"
    result = built_valid_json_str_with_aditional_info(error_message, additional_info)
    expected_json_additional_info = {
        "error_validacion": error_message,
        "error_validacion_detalle": additional_info,
    }
    assert result == json.dumps(expected_json_additional_info)

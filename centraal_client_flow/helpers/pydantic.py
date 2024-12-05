"""Helpers relacionados con pydantic."""

import json

from pydantic_core import ErrorDetails


def serialize_validation_errors(errors: list[ErrorDetails]) -> str:
    """
    Serializa los errores de validación en una cadena JSON adecuada para Cosmos DB.

    Args:
        errors: Lista de diccionarios que describen los errores de validación.

    Returns:
        Cadena JSON que representa los errores de validación.
    """
    return json.dumps(errors, ensure_ascii=False)


def built_valid_json_str_with_aditional_info(
    error_message: str, additional_info: str
) -> str:
    """
    Construye una cadena JSON válida con información adicional.
    """

    valid_dict = {"error_validacion": error_message}
    if additional_info:
        valid_dict["error_validacion_detalle"] = additional_info

    return json.dumps(valid_dict, ensure_ascii=False)

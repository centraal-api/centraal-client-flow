"""Helpers relacionados con pydantic."""

import json

from pydantic_core import ErrorDetails


def _custom_serializer(obj):
    """
    Custom serializer for objects not serializable by default json code.

    Args:
        obj: The object to serialize.

    Returns:
        A serializable representation of the object.
    """
    if isinstance(obj, Exception):
        return {
            "error_type": type(obj).__name__,
            "error_message": str(obj),
        }
    # Add more custom serialization rules if needed
    return str(obj)  # Fallback to string representation


def serialize_validation_errors(errors: list[ErrorDetails]) -> str:
    """
    Serializa los errores de validación en una cadena JSON adecuada para Cosmos DB.

    Args:
        errors: Lista de diccionarios que describen los errores de validación.

    Returns:
        Cadena JSON que representa los errores de validación.
    """
    return json.dumps(errors, default=_custom_serializer, ensure_ascii=False)


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

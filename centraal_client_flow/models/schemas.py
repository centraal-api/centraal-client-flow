"""Modelos de pydantic comunes."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class IDModel(BaseModel):
    """Base model for IDs"""

    separator: str = "-"

    @model_validator(mode="after")
    def check_id(self) -> Self:
        if self.model_fields_set == {"separator"}:
            raise ValueError("No se definieron suficientes campos para el Modelo")
        return self


class EntradaEsquemaUnificado(BaseModel):
    """Entrada Esquema unificado"""

    id: IDModel

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, field_type in cls.__annotations__.items():
            if name == "id" and not issubclass(field_type, IDModel):
                raise TypeError(
                    f"Field 'id' in '{cls.__name__}' must be a subclass of BaseIDModel"
                )
            if not issubclass(field_type, BaseModel) and name not in [
                "id",
                "auditoria",
            ]:
                raise TypeError(
                    f"Field '{name}' in '{cls.__name__}' must be a subclass of Pydantic BaseModel"
                )


class EventoBase(BaseModel):
    """Entrada Esquema unificado"""

    id: IDModel
    fecha_evento: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditoriaEntry(BaseModel):
    """Entrada para auditoria."""

    id_entrada: IDModel
    subesquema: str
    campo: str
    new_value: Any
    old_value: Any
    fecha_evento: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

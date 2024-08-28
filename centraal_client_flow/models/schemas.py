"""Modelos de pydantic comunes."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, model_serializer, model_validator
from typing_extensions import Self


class IDModel(BaseModel):
    """Base model for IDs. Puede aceptar ID como atributo."""

    separator: str = "-"

    @model_validator(mode="after")
    def check_id(self) -> Self:
        """Verificar la asignacion."""
        if self.model_fields_set == {"separator"}:
            raise ValueError("No se definieron suficientes campos para el Modelo")
        return self

    @model_serializer
    def serialize_as_str(self) -> str:
        """Serializa a string."""
        fields = [
            str(getattr(self, field_name))
            for field_name, f in self.model_fields.items()
            if field_name != "separator"
        ]
        return self.separator.join(fields)

    @model_validator(mode="before")
    @classmethod
    def parse_serialized_id(cls, data: Any) -> Any:
        """Deserializa un id para lograr operacion contraria a serialize_as_str."""
        if isinstance(data, str):
            sep = cls.model_json_schema()["properties"]["separator"]["default"]
            field_names = cls.model_fields
            if "separator" in field_names:
                field_names.pop("separator")
            field_names = field_names.keys()
            values = data.split(sep)
            if len(values) != len(field_names):
                raise ValueError(
                    f"Formato de ID no válido, se esperaban {len(field_names)} partes."
                )
            data = dict(zip(field_names, values))
        return data


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
    new_value: Optional[Any]
    old_value: Optional[Any]
    fecha_evento: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

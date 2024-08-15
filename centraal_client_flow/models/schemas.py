"""Modelos de pydantic comunes."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EntradaEsquemaUnificado(BaseModel):
    """Entrada Esquema unificado"""

    id: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, field_type in cls.__annotations__.items():
            if not issubclass(field_type, BaseModel) and name not in [
                "id",
                "auditoria",
            ]:
                raise TypeError(
                    f"Field '{name}' in '{cls.__name__}' must be a subclass of Pydantic BaseModel"
                )


class AuditoriaEntry(BaseModel):
    """Entrada para auditoria."""

    subesquema: str
    campo: str
    fecha_evento: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

"""Modelos pydantic de auditoria."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AuditoriaEntry(BaseModel):
    """Entrada para auditoria."""

    subesquema: str
    campo: str
    fecha_evento: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

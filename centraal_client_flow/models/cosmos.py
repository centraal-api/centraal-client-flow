"""Modelos de pydantic comunes."""

from typing import List

from pydantic import BaseModel

from centraal_client_flow.models.auditoria import AuditoriaEntry


class EntradaEsquemaUnificado(BaseModel):
    """Entrada Esquema unificado"""

    id: str
    auditoria: List[AuditoriaEntry]

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

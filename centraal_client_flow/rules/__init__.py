"""Comun para rules."""


class NoHayReglas(Exception):
    """Excepción personalizada cuando no existen reglas."""

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje

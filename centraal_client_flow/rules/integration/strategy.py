"""Estrategias. """

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlencode

import requests
from pydantic import BaseModel

from centraal_client_flow.models.schemas import EntradaEsquemaUnificado


class IntegrationStrategy(ABC):
    """Clase Abstracta para definir estrategias de integracion."""

    name: Optional[str] = None
    logger: logging.Logger

    def __init__(
        self, logger: Optional[logging.Logger] = None, name: Optional[str] = None
    ):
        """
        Inicializa la estrategia de integración con un logger opcional.

        Parameters:
            logger: Instancia opcional de logging.Logger.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.name = name

    @abstractmethod
    def modelo_unificado_mapping(
        self, message: EntradaEsquemaUnificado
    ) -> Optional[BaseModel]:
        """Mapea el mensaje de entrada a un modelo unificado de salida.

        Args:
            message: El mensaje de entrada a ser mapeado.

        Returns:
            Un modelo Pydantic que representa la salida mapeada.
        """

    @abstractmethod
    def integrate(self, output_model: Optional[BaseModel]) -> Optional[dict]:
        """Realiza la integración utilizando el modelo de salida.

        Args:
            output_model: El modelo de datos ya mapeado que se enviará a la integración.

        Returns:
            La respuesta de la integración, generalmente en formato JSON.
        """


@dataclass
class OAuthConfigPassFlow:
    """Configuración necesaria para la autenticación OAuth 2.0 con grant_type=password."""

    client_id: str
    client_secret: str
    username: str
    password: str
    token_resource: str
    api_url: str
    use_url_params_for_auth: bool = True


@dataclass
class OAuthTokenPass:
    """Representa el token OAuth obtenido tras la autenticación."""

    access_token: str
    instance_url: str
    id: str
    token_type: str
    issued_at: int
    signature: str


class RESTIntegration(IntegrationStrategy):
    """Estrategia de integracion basada en REST."""

    def __init__(
        self,
        oauth_config: OAuthConfigPassFlow,
        method: str = "POST",
        resource: str = "",
        mapping_function: Optional[
            Callable[[EntradaEsquemaUnificado], Optional[BaseModel]]
        ] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Inicializa una instancia de RESTIntegration con la configuración de OAuth y
            los parámetros REST.

        Args:
            oauth_config: Configuración necesaria para autenticarse con OAuth 2.0.
            method: El método HTTP que se utilizará para la integración
                (por ejemplo, 'POST', 'PATCH').
            resource: El recurso específico de la API con el cual se interactuará.
            mapping_function: Una función opcional que define cómo mapear un
                `EntradaEsquemaUnificado` a un modelo Pydantic.
        """
        if mapping_function is not None:
            super().__init__(
                logger=logger, name=f"{method}_{mapping_function.__name__}"
            )
        self.oauth_config = oauth_config
        self.method = method
        self.resource = resource
        self.mapping_function = mapping_function
        self.response_processor = lambda r, m: r.json()
        self._token: Optional[OAuthTokenPass] = None

    def _authenticate(self) -> OAuthTokenPass:
        """Autentica usando OAuth 2.0 con grant_type=password y obtiene un token de acceso.

        Returns:
            Un objeto `OAuthTokenPass` que contiene el token de acceso y otra información relevante.
        """
        auth_data = {
            "grant_type": "password",
            "client_id": self.oauth_config.client_id,
            "client_secret": self.oauth_config.client_secret,
            "username": self.oauth_config.username,
            "password": self.oauth_config.password,
        }

        if self.oauth_config.use_url_params_for_auth:
            token_url = f"{self.oauth_config.api_url}/{self.oauth_config.token_resource}?{urlencode(auth_data)}"
            response = requests.post(token_url, headers={}, timeout=30)
        else:
            token_url = (
                f"{self.oauth_config.api_url}/{self.oauth_config.token_resource}"
            )
            response = requests.post(token_url, data=auth_data, headers={}, timeout=30)

        response.raise_for_status()
        token_data = response.json()
        self._token = OAuthTokenPass(**token_data)
        return self._token

    def _get_token(self) -> Optional[str]:
        """Obtiene el token actual o lo renueva si ha expirado.

        Returns:
            El token de acceso en formato de cadena.
        """
        if self._token is None:
            self._authenticate()

        if self._token is not None:
            return self._token.access_token

    def modelo_unificado_mapping(
        self, message: EntradaEsquemaUnificado
    ) -> Optional[BaseModel]:
        """Mapea el mensaje de entrada a un modelo unificado de salida utilizando la
            función de mapeo proporcionada.

        Args:
            message: El mensaje de entrada que será mapeado.

        Returns:
            Un modelo Pydantic que representa la salida mapeada.

        Raises:
            TypeError: Si el mensaje no es una instancia de `EntradaEsquemaUnificado`.
            NotImplementedError: Si no se ha proporcionado una función de mapeo personalizada.
        """
        if self.mapping_function:
            if not isinstance(message, EntradaEsquemaUnificado):
                raise TypeError(
                    "El mensaje debe ser una instancia de EntradaEsquemaUnificado"
                )
            return self.mapping_function(message)
        else:
            raise NotImplementedError(
                "No se ha proporcionado una función de mapeo personalizada."
            )

    def integrate(self, output_model: Optional[BaseModel]) -> Optional[dict]:
        """Realiza la integración utilizando el modelo de salida mapeado.

        Args:
            output_model: El modelo de datos ya mapeado que se enviará a la integración.

        Returns:
            La respuesta de la integración en formato JSON.

        Raises:
            HTTPError: Si la solicitud HTTP a la API falla.
        """
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.oauth_config.api_url}/{self.resource}"

        if output_model is not None:

            response = requests.request(
                self.method,
                url,
                json=output_model.model_dump(mode="json", exclude_none=True),
                headers=headers,
                timeout=300,
            )
            response.raise_for_status()
            return self.response_processor(response, output_model)
        self.logger.info("Evento es ignorado.")
        return None

    def set_response_processor(
        self, processor: Callable[[requests.Response, BaseModel], Any]
    ):
        """Configura un procesamiento de la respuesta."""
        self.response_processor = processor

from abc import ABC, abstractmethod


class IntegrationStrategy(ABC):
    @abstractmethod
    def integrate(self, message: dict):
        pass


class RESTIntegration(IntegrationStrategy):
    def integrate(self, message: dict):
        # Lógica para integrar con una API REST
        print("Integrating with REST API")

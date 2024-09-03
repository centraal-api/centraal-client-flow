# centraal-client-flow

<a href="https://pypi.python.org/pypi/centraal_client_flow">
    <img src="https://img.shields.io/pypi/v/centraal_client_flow.svg"
        alt = "Release Status">
</a>

<a href="https://github.com/centraal-api/centraal-client-flow/actions">
    <img src="https://github.com/centraal-api/centraal-client-flow/actions/workflows/dev.yml/badge.svg?branch=release" alt="CI Status">
</a>

<a href="https://centraal-api.github.io/centraal-client-flow/">
    <img src="https://img.shields.io/website/https/centraal-api.github.io/centraal-client-flow/index.html.svg?label=docs&down_message=unavailable&up_message=available" alt="Documentation Status">
</a>


`centraal-client-flow` es una librería de Python diseñada para facilitar la implementación de una una solución basada en eventos para la sincronización y consistencia de datos entre sistemas distribuidos de clientes utilizando Azure. Esta librería proporciona herramientas para manejar eventos, aplicar reglas de procesamiento, integrar con sistemas externos y mantener un esquema unificado de clientes.

## **Introducción**

`Centraal-Cliente-Flow` facilita la implementación de arquitecturas de sincronización de datos en Azure, proporcionando una base sólida para manejar eventos en tiempo real, reglas de negocio, integración con APIs externas y mantenimiento de un log de auditoría.

## **Arquitectura**

La arquitectura está diseñada para unificar la información de los clientes alrededor de un identificador único, asegurando la consistencia de los datos a través de los siguientes componentes clave:

- **Eventos**: Gestionados por Azure Functions para manejar eventos entrantes en tiempo real y operaciones periódicas de extracción de datos.
- **Reglas**: Implementan la lógica de procesamiento de eventos para actualizar un esquema unificado de clientes.
- **Reglas de Integración**: Sincronizan las actualizaciones del esquema unificado con sistemas externos a través de APIs REST.
- **Esquema Unificado**: Modelo de datos centralizado que asegura consistencia y escalabilidad en la información de los clientes.
- **Log de Auditoría**: Registra todas las actualizaciones del esquema unificado para asegurar trazabilidad.
- **Uso de Pydantic**: La libreria hace uso extensivo e incentiva que cada intercambio de datos este mediado por modelos [Pydantic](https://docs.pydantic.dev/latest/), ya de esta manera se asegura calidad y reglas de negocio.

```
                Evento
                  ^
                  |
                  v
+------------------------------+
|   Receiver/Timer Function     |
|  (Valida y envía a la cola    |
|   usando Pydantic)            |
+------------------------------+
            |
            |
         [P]-EventoBase(IdModel)
            |
            v
+------------------------------+
|   Azure Service Bus Queue     |
|  (Ordena eventos por          |
|   Session ID)                 |
+------------------------------+
            |
            v
+---------------------------------------+
|  Processor Function                   |
|  Reglas de Actualización              |
|  (Actualiza esquema y log de          |
|   auditoría usando Pydantic,          |
|   Publica actualizaciones)            |
+---------------------------------------+
            |                   |
            |                   |
         [P]-EntradaEsquemaUnificado
    [P] - AuditoriaEntry        |
            |                   |
            v                   v
+-----------------------+   +-------------------------+
|     Cosmos DB         |   |  Azure Service Bus      |
| (Esquema Unificado y  |   |         Topic           |
|  Log de Auditoría)    |   |                         |
+-----------------------+   +-------------------------+
            |                           |
            |                           |
      [P]-AuditoriaEntry                |
            |                           |
            v                           v
+-----------------------+   +-------------------------+
| Log de Auditoría en   |   | Integration Function    |
| Cosmos DB             |   | Reglas  y Estrategias   |
| (Registra cambios)    |   | de Integración          |
+-----------------------+   |                         |
                            |                         |
                            +-------------------------+
                                       |
                                 [P]-BaseModel
                                       |
                                       v
                            +-------------------------+
                            |    Sistemas Externos    |
                            | (Reciben actualizaciones|
                            |  a través de APIs REST) |
                            +-------------------------+

```

## **Componentes Clave**

### 1. **Eventos**

- **Receiver Functions**: Manejan eventos entrantes en tiempo real. Implementadas en el módulo `receiver.py` utilizando clases como `EventFunctionBuilder`.
- **Timer Functions**: Ejecutan tareas periódicas para extraer información de sistemas externos, definidas en `timer.py` usando `TimerFunctionBuilder`.

### 2. **Reglas de Procesamiento**

Las reglas para actualizar el esquema unificado de clientes se implementan usando `UpdateProcessor` y `RuleProcessor`, que permiten procesar y aplicar reglas específicas a los eventos entrantes.

### 3. **Reglas de Integración**

Se implementan en `strategy.py` usando la clase `RESTIntegration`, que permite la sincronización de datos con APIs REST externas.

### 4. **Esquema Unificado**

Definido en `schemas.py`, utiliza modelos Pydantic para asegurar la validación y consistencia de datos. Los modelos incluyen `IDModel`, `EntradaEsquemaUnificado`, y otros sub-esquemas específicos.

### 5. **Log de Auditoría**

Para asegurar la trazabilidad de las actualizaciones, todos los cambios en los sub-esquemas se registran en una colección de auditoría en Cosmos DB.

## **Uso de la Librería**

### 1. **Configuración Inicial**

Asegúrate de tener configuradas las variables de entorno necesarias para las conexiones a Cosmos DB y Azure Service Bus.

```python
import os

os.environ["COSMOS_CONN"] = "<tu_cosmos_db_connection_string>"
os.environ["DATABASE"] = "<tu_database_name>"
os.environ["BUS_CONN"] = "<tu_service_bus_connection_string>"
```

### 2. **Registrar Funciones de Azure**

#### Eventos

Utiliza el siguiente ejemplo para registrar funciones receptoras y de temporización.

```python
from azure.functions import FunctionApp
from centraal_client_flow.receiver import Recieve
from centraal_client_flow.timer import Pull

app = FunctionApp()

# Registrar función receptora
receiver = Recieve(event_source="source_name", queue_name="queue_name", service_bus_client=service_bus_client_instance)
receiver.register_function(app, processor=event_processor_instance, event_model=event_model_instance)

# Registrar función de temporización
pull = Pull(schedule="0 */5 * * * *", event_source="source_name", queue_name="queue_name", service_bus_client=service_bus_client_instance)
pull.register_function(app, processor=pull_processor_instance)
```

#### Reglas de Actualización

```python
from azure.functions import FunctionApp
from update_rules import bp_update_rules

app = FunctionApp()
app.register_functions(bp_update_rules)
```

#### Reglas de Integración

```python
from azure.functions import FunctionApp
from integration_rules import bp_int_rules

app = FunctionApp()
app.register_functions(bp_int_rules)
```

### 3. **Definir Modelos y Procesadores**

Define los modelos de datos utilizando Pydantic para asegurar la validación de datos entrantes.

```python
from pydantic import BaseModel, EmailStr

class EventoEjemplo(BaseModel):
    id: int
    nombre: str
    email: EmailStr
```

Implementa procesadores para manejar la lógica de actualización de acuerdo con las reglas de negocio.

```python
from centraal_client_flow.rules.update import UpdateProcessor
from modelos import EventoEjemplo

class EjemploProcessor(UpdateProcessor):
    def process_message(self, event: EventoEjemplo, current_registro=None):
        # Lógica de procesamiento de eventos
        pass
```

### 4. **Ejecutar la Aplicación**

Asegúrate de que todas las dependencias estén instaladas y ejecuta la aplicación utilizando un servidor de funciones de Azure.

```bash
func start
```

## **Contribuciones**

Las [contribuciones](./CONTRIBUTING.md) son bienvenidas. Por favor, abre un issue o un pull request en el repositorio para discutir cualquier cambio.

* Free software: Apache-2.0
* Documentation: <https://centraal-api.github.io/centraal_client_flow/>


## Credits

This package was created with the [ppw](https://zillionare.github.io/python-project-wizard) tool. For more information, please visit the [project page](https://zillionare.github.io/python-project-wizard/).



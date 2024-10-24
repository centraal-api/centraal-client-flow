# History

## 0.1.12 (2024-10-24)

## Added
- `ServiceBusClientSingleton` no crear senders y los trata de reusar.


## 0.1.11 (2024-09-16)

## Fixed
- `RESTIntegration` soportar que no es entero.


## 0.1.10 (2024-09-16)

## Fixed
- `RESTIntegration` manejar renovación del token.


## 0.1.9 (2024-09-12)

## Fixed
- `AuditoriaEntryIntegracion` Dejar el ID para trazar a nivel de ID y regla.


## 0.1.8 (2024-09-12)

## Fixed
- `IntegrationRule` Cuando existe un error de validación se devuelve un resultado no exitoso.


## 0.1.7 (2024-09-12)

## Added
- `RESTIntegration` se incluye nuevo objeto de resultado de integracion que sirve para auditoria de integración.


## 0.1.6 (2024-09-10)

## Added
- `RESTIntegration` se adiciona la capacidad de ignorar el evento.


## 0.1.5 (2024-09-03)

## Added
- `IntegrationRule` se adiciona un metodo que ejecuta la regla de integración.


## 0.1.4 (2024-09-03)

## Fixed
- RESTIntegration ahora tambien soporte procesar con el modelo enviado.


## 0.1.3 (2024-09-02)

## Fixed
- Debe ser un string representando en Json cuando se envia hacia el topic.



## 0.1.2 (2024-09-02)

## Fixed
- Evitar cambiar a str el sjon cuando se informa a los topics.


## 0.1.0 (2024-08-13)

* First release on PyPI.

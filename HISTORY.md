# History

## 0.1.16 (2025-05-19)

### Fixed
- `ServiceBusClientSingleton`: configurar nivel de logging.


## 0.1.15 (2025-05-19)

### Fixed
- `ServiceBusClientSingleton`: Mejoras para eviatar errores.


## 0.1.14 (2024-12-14)

### Fixed
- `serialize_validation_errors`: Fix the serialization problem of exceptions.



## 0.1.13 (2024-12-05)

### Fixed
- `IntegrationRule`: Fixed message decoding for ServiceBusMessage handling.

### Added
- `EventProcessor`: Added helper functions for Pydantic validation error serialization.
- `IntegrationRule`: Enhanced error handling and logging capabilities.
- `IntegrationRuleV2`: Created new version with simplified integration logic.


## 0.1.12 (2024-10-24)

### Added
- `ServiceBusClientSingleton`: Optimized to reuse existing senders instead of creating new ones.

## 0.1.11 (2024-09-16)

### Fixed
- `RESTIntegration`: Added support for non-integer values.

## 0.1.10 (2024-09-16)

### Fixed
- `RESTIntegration`: Improved token renewal handling.

## 0.1.9 (2024-09-12)

### Fixed
- `AuditoriaEntryIntegracion`: Preserved ID for tracing at ID and rule level.

## 0.1.8 (2024-09-12)

### Fixed
- `IntegrationRule`: Returns unsuccessful result when validation error occurs.

## 0.1.7 (2024-09-12)

### Added
- `RESTIntegration`: Added new integration result object for integration auditing.

## 0.1.6 (2024-09-10)

### Added
- `RESTIntegration`: Added capability to ignore events.

## 0.1.5 (2024-09-03)

### Added
- `IntegrationRule`: Added method to execute integration rule.

## 0.1.4 (2024-09-03)

### Fixed
- `RESTIntegration`: Added support for processing with provided model.

## 0.1.3 (2024-09-02)

### Fixed
- Improved JSON string handling when sending to topics.

## 0.1.2 (2024-09-02)

### Fixed
- Prevented unnecessary JSON string conversion when informing topics.

## 0.1.0 (2024-08-13)

- First release on PyPI.

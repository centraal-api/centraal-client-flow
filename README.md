# centraal-client-flow

<p align="center">
<a href="https://pypi.python.org/pypi/centraal_client_flow">
    <img src="https://img.shields.io/pypi/v/centraal_client_flow.svg"
        alt = "Release Status">
</a>

<a href="https://github.com/centraal-api/centraal_client_flow/actions">
    <img src="https://github.com/centraal-api/centraal_client_flow/actions/workflows/main.yml/badge.svg?branch=release" alt="CI Status">
</a>

<a href="https://centraal-api.github.io/centraal_client_flow/">
    <img src="https://img.shields.io/website/https/centraal-api.github.io/centraal_client_flow/index.html.svg?label=docs&down_message=unavailable&up_message=available" alt="Documentation Status">
</a>

</p>


centraal-client-flow es una librería diseñada para facilitar la sincronización, unificación y auditoría de datos de clientes provenientes de múltiples fuentes. Esta librería encapsula patrones de arquitectura comúnmente utilizados en plataformas dgestión de datos, permitiéndote integrar datos de clientes de manera eficiente.


* Free software: Apache-2.0
* Documentation: <https://centraal-api.github.io/centraal_client_flow/>


## Features

* TODO

## Credits

This package was created with the [ppw](https://zillionare.github.io/python-project-wizard) tool. For more information, please visit the [project page](https://zillionare.github.io/python-project-wizard/).


## Configuraciones importantes

**en dev.yml**
-  remover python 3.8.
- ajustar la publicación

```yaml
- name: publish to Test PyPI
uses: pypa/gh-action-pypi-publish@release/v1
with:
    repository-url: https://test.pypi.org/legacy/
    skip-existing: true
```
- remover todo lo relacionado con la notificación

**en release.yml**
- remover el trigger en main
-  ajustar las versiones python-versions: ['3.9', '3.10', '3.11']
- ajustar la publicacion a pypi

```yaml
- name: publish to PYPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          skip-existing: true
```

- remover todo lo relacionado con la notificación

**pyrightconfig.json**
- version python 3.11
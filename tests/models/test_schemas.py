"""Test de schemas."""

# pylint: disable=missing-docstring
import pytest

from centraal_client_flow.models.schemas import IDModel


@pytest.fixture(name="class_2_atrs")
def class_2_atrs_fix():
    class Clase2Atrs(IDModel):
        """test."""

        producto_id: str
        lote: int

    return Clase2Atrs


@pytest.fixture(name="class_3_atrs_no_default_sep")
def class_3_atrs_no_default_sep_fix():
    class Clase3Atrs(IDModel):
        """test."""

        numero_pedido: str
        fecha_pedido: str
        add_info: int
        separator: str = "|"

    return Clase3Atrs


@pytest.fixture(name="class_3_atrs")
def class_3_atrs_fix():
    class Clase3Atrs(IDModel):
        """test."""

        numero_pedido: str
        fecha_pedido: str
        add_info: int

    return Clase3Atrs


def test_serialization_id_model_should_return_id(class_2_atrs, class_3_atrs):
    obj_2_atrs = class_2_atrs(producto_id="XYZ123", lote=45)
    assert obj_2_atrs.model_dump(mode="json") == "XYZ123-45"
    obj_3_atrs = class_3_atrs(add_info=123, numero_pedido="abc", fecha_pedido="zxc")
    assert obj_3_atrs.model_dump(mode="json") == "abc-zxc-123"
    obj_3_atrs_second_case = class_3_atrs(
        fecha_pedido="zxc",
        add_info=123,
        numero_pedido="abc",
    )
    assert obj_3_atrs_second_case.model_dump(mode="json") == "abc-zxc-123"


def test_deserialization_id_model_should_support_id(class_2_atrs, class_3_atrs):
    obj_2_atrs = class_2_atrs.model_validate("XYZ123-45")
    assert obj_2_atrs.producto_id == "XYZ123"
    assert obj_2_atrs.lote == 45
    obj_3_atrs = class_3_atrs.model_validate("abc-zxc-123")
    assert obj_3_atrs.numero_pedido == "abc"
    assert obj_3_atrs.fecha_pedido == "zxc"
    assert obj_3_atrs.add_info == 123


def test_invalid_serialization_format(class_2_atrs):
    with pytest.raises(ValueError) as excinfo:
        class_2_atrs.model_validate("XYZ123")
    assert "Formato de ID no válido" in str(excinfo.value)


def test_separator_inherited_correctly(class_3_atrs, class_3_atrs_no_default_sep):
    pedido_id = class_3_atrs(
        numero_pedido="ORD6789", fecha_pedido="2024-08-21", add_info=10, separator="|"
    )
    serialized = pedido_id.model_dump()
    assert serialized == "ORD6789|2024-08-21|10"

    # el seperador no fue definido en el objeto
    with pytest.raises(ValueError):
        class_3_atrs.model_validate(serialized)

    obj_class_3 = class_3_atrs_no_default_sep.model_validate(serialized)
    assert obj_class_3.numero_pedido == "ORD6789"
    assert obj_class_3.fecha_pedido == "2024-08-21"
    assert obj_class_3.add_info == 10

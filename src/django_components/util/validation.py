from typing import Any


from django.utils.safestring import SafeString
from pydantic_core import core_schema
from pydantic import TypeAdapter, ValidationError


def validate_type(value: Any, type: Any, msg: str) -> None:
    print("VALUE: ", value)
    print("TYPE: ", type)
    try:
        # See https://docs.pydantic.dev/2.3/usage/type_adapter/
        TypeAdapter(type).validate_python(value)
    except ValidationError as err:
        raise TypeError(msg) from err


def _patch_safestring_validation() -> None:
    """Modify Django's SafeString to be validated as a string by Pydantic."""

    # Tell Pydantic to handle SafeString as regular string
    def safestring_core_schema(*args: Any, **kwargs: Any) -> Any:
        return core_schema.str_schema()

    SafeString.__get_pydantic_core_schema__ = safestring_core_schema

from __future__ import annotations

from copy import deepcopy
from typing import Any


class _UnsetType:
    pass


UNSET = _UnsetType()

_default_pagination: Any = UNSET
_default_relay_id_codec: Any = UNSET


def configure(
    *,
    default_pagination: Any = UNSET,
    default_relay_id_codec: Any = UNSET,
) -> None:
    global _default_pagination, _default_relay_id_codec

    if default_pagination is not UNSET:
        _default_pagination = default_pagination
    if default_relay_id_codec is not UNSET:
        _default_relay_id_codec = default_relay_id_codec


def reset_config() -> None:
    global _default_pagination, _default_relay_id_codec

    _default_pagination = UNSET
    _default_relay_id_codec = UNSET


def get_default_pagination() -> Any:
    if _default_pagination is UNSET:
        from strawberry_chemist.pagination import CursorPagination

        return CursorPagination()
    return deepcopy(_default_pagination)


def get_default_relay_id_codec() -> Any:
    if _default_relay_id_codec is UNSET:
        from strawberry_chemist.relay.codecs import DEFAULT_ID_CODEC

        return DEFAULT_ID_CODEC
    return _default_relay_id_codec

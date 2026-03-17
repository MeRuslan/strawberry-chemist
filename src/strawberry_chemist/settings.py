from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Final, TypeAlias, cast

from strawberry_chemist.pagination.base import (
    FlatPaginationPolicy,
    NestedPaginationPolicy,
)

if TYPE_CHECKING:
    from strawberry_chemist.relay.definitions import RelayIdCodec


PaginationDefault: TypeAlias = (
    FlatPaginationPolicy[Any, Any, Any] | NestedPaginationPolicy[Any, Any, Any]
)


class _UnsetType:
    pass


UNSET: Final = _UnsetType()

_default_pagination: PaginationDefault | _UnsetType = UNSET
_default_relay_id_codec: RelayIdCodec | _UnsetType = UNSET


def configure(
    *,
    default_pagination: PaginationDefault | _UnsetType = UNSET,
    default_relay_id_codec: RelayIdCodec | _UnsetType = UNSET,
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


def get_default_pagination() -> PaginationDefault:
    pagination = _default_pagination
    if pagination is UNSET:
        from strawberry_chemist.pagination import CursorPagination

        return CursorPagination()
    return deepcopy(cast(PaginationDefault, pagination))


def get_default_relay_id_codec() -> RelayIdCodec:
    codec = _default_relay_id_codec
    if codec is UNSET:
        from strawberry_chemist.relay.codecs import DEFAULT_ID_CODEC

        return DEFAULT_ID_CODEC
    return cast("RelayIdCodec", codec)

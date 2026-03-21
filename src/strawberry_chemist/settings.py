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
_default_use_single_loader_session: bool | _UnsetType = UNSET


def configure(
    *,
    default_pagination: PaginationDefault | _UnsetType = UNSET,
    default_relay_id_codec: RelayIdCodec | _UnsetType = UNSET,
    use_single_loader_session: bool | _UnsetType = UNSET,
) -> None:
    global _default_pagination, _default_relay_id_codec
    global _default_use_single_loader_session

    if default_pagination is not UNSET:
        _default_pagination = default_pagination
    if default_relay_id_codec is not UNSET:
        _default_relay_id_codec = default_relay_id_codec
    if use_single_loader_session is not UNSET:
        _default_use_single_loader_session = use_single_loader_session


def reset_config() -> None:
    global _default_pagination, _default_relay_id_codec
    global _default_use_single_loader_session

    _default_pagination = UNSET
    _default_relay_id_codec = UNSET
    _default_use_single_loader_session = UNSET


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


def get_use_single_loader_session() -> bool:
    use_single_loader_session = _default_use_single_loader_session
    if use_single_loader_session is UNSET:
        return False
    return cast(bool, use_single_loader_session)

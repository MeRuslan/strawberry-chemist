from __future__ import annotations

from typing import Optional, Sequence
from urllib.parse import quote, unquote

from .definitions import RelayIdCodec


class ReadableIdCodec:
    def encode(self, node_name: str, values: tuple[str, ...]) -> str:
        payload = ",".join(quote(value, safe="") for value in values)
        return f"{node_name}_{payload}"

    def decode(
        self,
        token: str,
        *,
        node_names: Optional[Sequence[str]] = None,
    ) -> tuple[str, tuple[str, ...]]:
        if node_names:
            for node_name in sorted(node_names, key=len, reverse=True):
                prefix = f"{node_name}_"
                if token.startswith(prefix):
                    payload = token[len(prefix) :]
                    values = tuple(
                        unquote(item) for item in payload.split(",") if item != ""
                    )
                    return node_name, values
            raise ValueError(f"Unknown node token: {token}")

        node_name, _, payload = token.partition("_")
        if not node_name or not _:
            raise ValueError(f"Unknown node token: {token}")
        values = tuple(unquote(item) for item in payload.split(",") if item != "")
        return node_name, values

    def register(self, *, model: type, node_name: str) -> None:
        return None


class IntRegistryCodec:
    def __init__(self, registry: dict[type, int]):
        self.registry = registry
        self._node_name_to_int: dict[str, int] = {}
        self._int_to_node_name: dict[int, str] = {}

    def register(self, *, model: type, node_name: str) -> None:
        if model not in self.registry:
            return
        code = self.registry[model]
        self._node_name_to_int[node_name] = code
        self._int_to_node_name[code] = node_name

    def encode(self, node_name: str, values: tuple[str, ...]) -> str:
        if node_name not in self._node_name_to_int:
            raise ValueError(f"Node '{node_name}' is not registered with this codec")
        payload = ",".join(quote(value, safe="") for value in values)
        return f"{self._node_name_to_int[node_name]}:{payload}"

    def decode(
        self,
        token: str,
        *,
        node_names: Optional[Sequence[str]] = None,
    ) -> tuple[str, tuple[str, ...]]:
        code_str, _, payload = token.partition(":")
        if not code_str or not _:
            raise ValueError(f"Unknown node token: {token}")
        code = int(code_str)
        if code not in self._int_to_node_name:
            raise ValueError(f"Unknown node token: {token}")
        node_name = self._int_to_node_name[code]
        if node_names is not None and node_name not in node_names:
            raise ValueError(f"Unknown node token: {token}")
        values = tuple(unquote(item) for item in payload.split(",") if item != "")
        return node_name, values


DEFAULT_ID_CODEC: RelayIdCodec = ReadableIdCodec()

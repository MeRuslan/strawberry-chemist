#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from strawberry.asgi import GraphQL

from strawberry_chemist.relay.public import clear_node_registry


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = ROOT / "examples"


class ExampleGraphQL(GraphQL):
    def __init__(self, schema: Any, *, context_factory: Any) -> None:
        super().__init__(schema)
        self._context_factory = context_factory

    async def get_context(self, request: Any, response: Any) -> Any:
        return await self._context_factory(request=request, response=response)


def resolve_example_dir(example_arg: str) -> Path:
    local_example_dir = EXAMPLES_ROOT / example_arg
    if local_example_dir.is_dir():
        return local_example_dir

    provided_path = (ROOT / example_arg).resolve()
    if provided_path.is_dir():
        return provided_path

    raise SystemExit(f"example project not found: {example_arg}")


def load_example_app(example_arg: str) -> tuple[ModuleType, Path]:
    clear_node_registry()
    example_dir = resolve_example_dir(example_arg)
    module_name = f"scripts._example_{example_dir.name}"
    module_path = example_dir / "app.py"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise SystemExit(f"failed to load example module: {module_path}")
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, example_dir


def build_context(
    module: ModuleType,
    session_factory: Any,
    *,
    request_id: str,
    current_user_id: int | None,
) -> Any:
    context_parameters = inspect.signature(module.AppContext).parameters
    kwargs: dict[str, Any] = {}
    if "request_id" in context_parameters:
        kwargs["request_id"] = request_id
    if "current_user_id" in context_parameters:
        kwargs["current_user_id"] = current_user_id
    return module.AppContext(session_factory, **kwargs)


async def prepare_seeded_example(module: ModuleType) -> tuple[Any, Any]:
    engine, session_factory = module.create_engine_and_sessionmaker()
    await module.prepare_database(engine)
    await module.seed_data(session_factory)
    return engine, session_factory


def print_schema(example_arg: str) -> None:
    module, _example_dir = load_example_app(example_arg)
    print(module.build_schema().as_str())


def serve_schema(
    example_arg: str,
    *,
    host: str,
    port: int,
    request_id: str,
    current_user_id: int | None,
) -> None:
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "uvicorn is required; run `uv sync --group dev` first"
        ) from exc

    module, example_dir = load_example_app(example_arg)
    engine, session_factory = asyncio.run(prepare_seeded_example(module))
    schema = module.build_schema()

    async def context_getter(*_args: Any, **_kwargs: Any) -> Any:
        return build_context(
            module,
            session_factory,
            request_id=request_id,
            current_user_id=current_user_id,
        )

    print(f"Serving {example_dir.name} at http://{host}:{port}")
    try:
        uvicorn.run(
            ExampleGraphQL(schema, context_factory=context_getter),
            host=host,
            port=port,
        )
    finally:
        asyncio.run(engine.dispose())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print or serve a seeded example schema.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    print_parser = subparsers.add_parser("print", help="Print an example schema as SDL")
    print_parser.add_argument("example", help="Example name or path")

    serve_parser = subparsers.add_parser(
        "serve",
        help="Serve a seeded example schema over GraphQL",
    )
    serve_parser.add_argument("example", help="Example name or path")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--request-id", default="dev-request")
    serve_parser.add_argument("--current-user-id", type=int, default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "print":
        print_schema(args.example)
        return

    if args.command == "serve":
        serve_schema(
            args.example,
            host=args.host,
            port=args.port,
            request_id=args.request_id,
            current_user_id=args.current_user_id,
        )
        return

    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from strawberry.asgi import GraphQL

EXAMPLE_ROOT = Path(__file__).resolve().parent
if str(EXAMPLE_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_ROOT))

from db import create_engine_and_sessionmaker, prepare_database, seed_data
from schema import (
    AppContext,
    Book,
    DEFAULT_CODEC,
    LEGACY_CODEC,
    LegacyBookmark,
    Membership,
    Shelf,
    build_context,
    build_schema,
)


class ExampleGraphQL(GraphQL):
    def __init__(self, schema: strawberry.Schema, *, context_factory: Any) -> None:
        super().__init__(schema)
        self._context_factory = context_factory

    async def get_context(self, request: Any, response: Any) -> Any:
        return await self._context_factory(request=request, response=response)


async def prepare_seeded_runtime() -> tuple[Any, Any]:
    engine, session_factory = create_engine_and_sessionmaker()
    await prepare_database(engine)
    await seed_data(session_factory)
    return engine, session_factory


def print_schema() -> None:
    print(build_schema().as_str())


def serve_schema(
    *,
    host: str,
    port: int,
    request_id: str,
    current_user_id: int | None,
) -> None:
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise SystemExit("uvicorn is required; run `uv sync` first") from exc

    engine, session_factory = asyncio.run(prepare_seeded_runtime())
    schema = build_schema()

    async def context_getter(*_args: Any, **_kwargs: Any) -> AppContext:
        return build_context(
            session_factory,
            request_id=request_id,
            current_user_id=current_user_id,
        )

    print(f"Serving on http://{host}:{port}")
    try:
        uvicorn.run(
            ExampleGraphQL(schema, context_factory=context_getter),
            host=host,
            port=port,
        )
    finally:
        asyncio.run(engine.dispose())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run this example project.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("print-schema", help="Print the example schema as SDL")

    serve_parser = subparsers.add_parser(
        "serve",
        help="Serve the seeded example over GraphQL",
    )
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--request-id", default="dev-request")
    serve_parser.add_argument("--current-user-id", type=int, default=None)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "print-schema":
        print_schema()
        return

    if args.command == "serve":
        serve_schema(
            host=args.host,
            port=args.port,
            request_id=args.request_id,
            current_user_id=args.current_user_id,
        )
        return

    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()

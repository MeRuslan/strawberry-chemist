# uv smoke project

This is a standalone `uv` consumer project for `strawberry-chemist`.

It is useful in two modes:

1. local-latest testing against the current checkout
2. published-style testing against the pinned package version

## Local checkout check

From the repository root:

```bash
uv sync --project examples/uv_smoke_project
uv run --project examples/uv_smoke_project \
  python examples/uv_smoke_project/smoke_test.py
```

This uses the example project's `tool.uv.sources` override, so
`strawberry-chemist` is installed from the current repository checkout.

## Pre-publish isolated check

From the repository root:

```bash
uv run python -m build --outdir /tmp/strawberry-chemist-dist
uv sync --project examples/uv_smoke_project \
  --no-sources \
  --find-links /tmp/strawberry-chemist-dist
uv run --project examples/uv_smoke_project python smoke_test.py
```

This installs `strawberry-chemist` into the example project's own environment
from the built distribution artifacts, not from the parent repo source tree.

## Published package check

From the repository root:
```bash
uv sync --project examples/uv_smoke_project \
  --no-sources
uv run --project examples/uv_smoke_project python examples/uv_smoke_project/smoke_test.py
```

Expected output:

```python
{'book': {'title': 'The Hobbit'}}
```

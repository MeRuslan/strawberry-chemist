# uv smoke project

This is a standalone `uv` consumer project for `strawberry-chemist`.

It is useful in two modes:

1. pre-publish isolated smoke testing against a locally built wheel
2. post-publish testing against TestPyPI

## Pre-publish isolated check

From the repository root:

```bash
uv run python -m build --outdir /tmp/strawberry-chemist-dist
uv sync --project examples/uv_smoke_project --find-links /tmp/strawberry-chemist-dist
uv run --project examples/uv_smoke_project python smoke_test.py
```

This installs `strawberry-chemist` into the example project's own environment
from the built distribution artifacts, not from the parent repo source tree.

## TestPyPI check

After publishing `0.1.0` to TestPyPI.

From the repository root:
```bash
uv sync --project examples/uv_smoke_project
uv run --project examples/uv_smoke_project python examples/uv_smoke_project/smoke_test.py
```

Expected output:

```python
{'book': {'title': 'The Hobbit'}}
```

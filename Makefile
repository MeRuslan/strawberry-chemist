.DEFAULT_GOAL := help

EXAMPLE ?= 01_types_and_fields
HOST ?= 127.0.0.1
PORT ?= 8000
REQUEST_ID ?= dev-request
CURRENT_USER_ID ?=
EXAMPLES := $(shell find examples -mindepth 1 -maxdepth 1 -type d -name '[0-9][0-9]_*' -exec basename {} \; | sort)

.PHONY: help test mypy check \
	example-test example-test-published examples-test examples-test-published \
	example-schema example-serve \
	sample-test sample-test-published samples-test samples-test-published \
	sample-schema sample-serve

help:
	@echo "make test"
	@echo "make mypy"
	@echo "make check"
	@echo "make example-test EXAMPLE=03_connections_filters_and_ordering"
	@echo "make example-test-published EXAMPLE=03_connections_filters_and_ordering"
	@echo "make examples-test"
	@echo "make examples-test-published"
	@echo "make example-schema EXAMPLE=03_connections_filters_and_ordering"
	@echo "make example-serve EXAMPLE=03_connections_filters_and_ordering PORT=8000"

test:
	uv run pytest

mypy:
	uv run mypy

check: test mypy

example-test:
	scripts/run-example-local "$(EXAMPLE)"

example-test-published:
	scripts/run-example-published "$(EXAMPLE)"

examples-test:
	@set -e; for example in $(EXAMPLES); do \
		echo "==> $$example"; \
		scripts/run-example-local "$$example"; \
	done

examples-test-published:
	@set -e; for example in $(EXAMPLES); do \
		echo "==> $$example"; \
		scripts/run-example-published "$$example"; \
	done

example-schema:
	uv run python scripts/example_schema.py print "$(EXAMPLE)"

example-serve:
	uv run python scripts/example_schema.py serve "$(EXAMPLE)" \
		--host "$(HOST)" \
		--port "$(PORT)" \
		--request-id "$(REQUEST_ID)" $(if $(strip $(CURRENT_USER_ID)),--current-user-id "$(CURRENT_USER_ID)")

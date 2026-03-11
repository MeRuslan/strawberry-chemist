.DEFAULT_GOAL := help

EXAMPLE ?= 01_types_and_fields
HOST ?= 127.0.0.1
PORT ?= 8000
REQUEST_ID ?= dev-request
CURRENT_USER_ID ?=
EXAMPLES := $(shell find examples/v0_2_api -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)

.PHONY: help test mypy check sample-test sample-test-published samples-test \
	samples-test-published sample-schema sample-serve

help:
	@echo "make test"
	@echo "make mypy"
	@echo "make check"
	@echo "make sample-test EXAMPLE=03_connections_filters_and_ordering"
	@echo "make sample-test-published EXAMPLE=03_connections_filters_and_ordering"
	@echo "make samples-test"
	@echo "make samples-test-published"
	@echo "make sample-schema EXAMPLE=03_connections_filters_and_ordering"
	@echo "make sample-serve EXAMPLE=03_connections_filters_and_ordering PORT=8000"

test:
	uv run pytest

mypy:
	uv run mypy

check: test mypy

sample-test:
	scripts/run-example-local "$(EXAMPLE)"

sample-test-published:
	scripts/run-example-published "$(EXAMPLE)"

samples-test:
	@set -e; for example in $(EXAMPLES); do \
		echo "==> $$example"; \
		scripts/run-example-local "$$example"; \
	done

samples-test-published:
	@set -e; for example in $(EXAMPLES); do \
		echo "==> $$example"; \
		scripts/run-example-published "$$example"; \
	done

sample-schema:
	uv run python scripts/example_schema.py print "$(EXAMPLE)"

sample-serve:
	uv run python scripts/example_schema.py serve "$(EXAMPLE)" \
		--host "$(HOST)" \
		--port "$(PORT)" \
		--request-id "$(REQUEST_ID)" $(if $(strip $(CURRENT_USER_ID)),--current-user-id "$(CURRENT_USER_ID)")

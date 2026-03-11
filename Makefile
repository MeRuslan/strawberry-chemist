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
	$(MAKE) -C "examples/$(EXAMPLE)" test-local

example-test-published:
	$(MAKE) -C "examples/$(EXAMPLE)" test-published

examples-test:
	@set -e; for example in $(EXAMPLES); do \
		echo "==> $$example"; \
		$(MAKE) -C "examples/$$example" test-local; \
	done

examples-test-published:
	@set -e; for example in $(EXAMPLES); do \
		echo "==> $$example"; \
		$(MAKE) -C "examples/$$example" test-published; \
	done

example-schema:
	$(MAKE) -C "examples/$(EXAMPLE)" schema-local

example-serve:
	$(MAKE) -C "examples/$(EXAMPLE)" serve-local \
		HOST="$(HOST)" \
		PORT="$(PORT)" \
		REQUEST_ID="$(REQUEST_ID)" \
		CURRENT_USER_ID="$(CURRENT_USER_ID)"

.DEFAULT_GOAL := help

HOST ?= 127.0.0.1
PORT ?= 8000
REQUEST_ID ?= dev-request
CURRENT_USER_ID ?=
PUBLISHED_SYNC_ARGS := --no-sources
ifneq ($(strip $(STRAWBERRY_CHEMIST_FIND_LINKS)),)
PUBLISHED_SYNC_ARGS += --find-links "$(STRAWBERRY_CHEMIST_FIND_LINKS)"
endif

.PHONY: help \
	test test-local test-published \
	schema schema-local schema-published \
	serve serve-local serve-published

help:
	@echo "make test"
	@echo "make test-local"
	@echo "make test-published"
	@echo "make schema"
	@echo "make schema-local"
	@echo "make schema-published"
	@echo "make serve"
	@echo "make serve-local"
	@echo "make serve-published"

test: test-published

test-local:
	uv sync
	uv run python -m pytest test_contract.py

test-published:
	uv sync $(PUBLISHED_SYNC_ARGS)
	uv run python -m pytest test_contract.py

schema: schema-published

schema-local:
	uv sync
	uv run python app.py print-schema

schema-published:
	uv sync $(PUBLISHED_SYNC_ARGS)
	uv run python app.py print-schema

serve: serve-published

serve-local:
	uv sync
	uv run python app.py serve \
		--host "$(HOST)" \
		--port "$(PORT)" \
		--request-id "$(REQUEST_ID)" $(if $(strip $(CURRENT_USER_ID)),--current-user-id "$(CURRENT_USER_ID)")

serve-published:
	uv sync $(PUBLISHED_SYNC_ARGS)
	uv run python app.py serve \
		--host "$(HOST)" \
		--port "$(PORT)" \
		--request-id "$(REQUEST_ID)" $(if $(strip $(CURRENT_USER_ID)),--current-user-id "$(CURRENT_USER_ID)")

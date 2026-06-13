# PhoneWala Gyan — root Makefile
# Phase 0 targets prove the acceptance criteria without requiring the Supabase CLI.
# DB runs as a pgvector Postgres container; migrations are applied with psql-in-container.

SHELL := /bin/bash
COMPOSE := docker compose --env-file .env -f infra/docker-compose.yml
DB_SVC := db
DB_USER := postgres
DB_NAME := phonewala
MIGRATIONS := packages/db/supabase/migrations

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.PHONY: up
up: ## Start db + worker containers
	$(COMPOSE) up -d $(DB_SVC) worker

.PHONY: down
down: ## Stop all containers
	$(COMPOSE) down

.PHONY: db-up
db-up: ## Start only the database and wait until healthy
	$(COMPOSE) up -d $(DB_SVC)
	@echo "Waiting for Postgres to accept connections..."
	@until $(COMPOSE) exec -T $(DB_SVC) pg_isready -U $(DB_USER) -d $(DB_NAME) >/dev/null 2>&1; do sleep 1; done
	@echo "Postgres is ready."

.PHONY: db-reset
db-reset: db-up ## Drop + recreate schema and apply all migrations in order (clean migration test)
	@echo "Resetting public schema..."
	@$(COMPOSE) exec -T $(DB_SVC) psql -v ON_ERROR_STOP=1 -U $(DB_USER) -d $(DB_NAME) \
		-c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $(DB_USER);" >/dev/null
	@for f in $$(ls $(MIGRATIONS)/*.sql | sort); do \
		echo "  applying $$f"; \
		$(COMPOSE) exec -T $(DB_SVC) psql -v ON_ERROR_STOP=1 -U $(DB_USER) -d $(DB_NAME) < $$f >/dev/null || exit 1; \
	done
	@echo "Migrations applied cleanly."

.PHONY: db-verify
db-verify: ## Assert tables + indexes + extensions exist
	@scripts/db-verify.sh

.PHONY: typecheck
typecheck: ## Typecheck TS workspaces (requires pnpm; via corepack if not installed)
	@command -v pnpm >/dev/null 2>&1 && pnpm -r --if-present run typecheck || \
		COREPACK_HOME=$$HOME/.cache/corepack corepack pnpm@9.12.0 -r --if-present run typecheck

.PHONY: test
test: ## Run all tests (TS + Python)
	@$(MAKE) test-ts
	@$(MAKE) test-py

.PHONY: test-ts
test-ts: ## Run TS unit tests
	@command -v pnpm >/dev/null 2>&1 && pnpm -r --if-present run test || \
		COREPACK_HOME=$$HOME/.cache/corepack corepack pnpm@9.12.0 -r --if-present run test

.PHONY: test-py
test-py: ## Run Python worker tests
	@cd apps/worker && uv run pytest -q

.PHONY: demo-phase-0
demo-phase-0: ## Acceptance: clean migration + table/index check + worker /health green
	@scripts/demo-phase-0.sh

.PHONY: demo-phase-1
demo-phase-1: db-reset ## Acceptance: research -> >=30 deduped scored topics w/ rationale (mock providers)
	@echo ">> Phase 1 demo (mock LLM + mock embeddings, no API keys)"
	@cd apps/worker && \
		DATABASE_URL=postgresql://$(DB_USER):postgres@localhost:$${DB_PORT:-54322}/$(DB_NAME) \
		USE_MOCK_PROVIDERS=true EMBEDDINGS_BACKEND=mock \
		uv run python -m app.demo_phase1

.PHONY: demo-phase-2
demo-phase-2: db-reset ## Acceptance: greenlit topic -> QA-passed Hinglish script, 0 unverified claims
	@echo ">> Phase 2 demo (prompt-routing mock LLM, no API keys)"
	@cd apps/worker && \
		DATABASE_URL=postgresql://$(DB_USER):postgres@localhost:$${DB_PORT:-54322}/$(DB_NAME) \
		USE_MOCK_PROVIDERS=true EMBEDDINGS_BACKEND=mock \
		uv run python -m app.demo_phase2

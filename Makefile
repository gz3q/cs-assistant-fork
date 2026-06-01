.PHONY: setup cli migrate ingest test lint format

setup:
	uv sync

cli:
	uv run python -m src.apps.dev_cli

migrate:
	uv run alembic -c src/infrastructure/db/alembic.ini upgrade head

ingest:
	uv run python -m scripts.ingest

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run black .

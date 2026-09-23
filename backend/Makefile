.PHONY: test lint fmt schema

schema:
	uv run python -m app.export_schema

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy app

fmt:
	uv run ruff format .
	uv run ruff check --fix .

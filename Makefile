.PHONY: run test test-quick lint format typecheck clean build build-clean

run:
	uv run python -m src.main

test:
	uv run pytest

test-quick:
	uv run pytest -m "not slow"

lint:
	uv run ruff check src tests

format:
	uv run black src tests
	uv run ruff check --fix src tests

typecheck:
	uv run mypy src

clean:
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage

build:
	uv run pyinstaller lumen.spec

build-clean:
	rm -rf build/ dist/
	uv run pyinstaller lumen.spec

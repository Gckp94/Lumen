# 7. Development Workflow

## Environment Setup

```bash
# Clone repository
git clone <repo-url>
cd Lumen

# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Verify installation
uv run python -c "import PyQt6; print('PyQt6 OK')"
uv run python -c "import pyqtgraph; print('PyQtGraph OK')"
```

## pyproject.toml

```toml
[project]
name = "lumen"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "PyQt6>=6.6.0",
    "pyqtgraph>=0.13.0",
    "pandas>=2.1.0",
    "pyarrow>=14.0.0",
    "openpyxl>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-qt>=4.3.0",
    "pytest-cov>=4.1.0",
    "black>=24.4.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "pandas-stubs",
    "PyQt6-stubs",
    "pre-commit>=3.7.0",
    "pyinstaller>=6.0.0",
]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 100

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["numpy.typing.mypy_plugin"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "widget: marks tests requiring Qt event loop",
]
```

## Makefile

```makefile
.PHONY: run test test-quick test-perf lint format typecheck coverage build clean

# Run application
run:
	uv run python -m src.main

# Run all tests
test:
	uv run pytest

# Quick tests (skip slow)
test-quick:
	uv run pytest -m "not slow"

# Performance tests only
test-perf:
	uv run pytest -m slow --timeout=60 -v

# Lint code
lint:
	uv run ruff check src tests

# Format code
format:
	uv run black src tests
	uv run ruff check --fix src tests

# Type check
typecheck:
	uv run mypy src

# Coverage report
coverage:
	uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Build executable
build:
	uv run pyinstaller lumen.spec --clean --noconfirm

# Clean build artifacts
clean:
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ htmlcov/ .coverage
```

## VS Code Configuration

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.typeCheckingMode": "strict",
    "editor.formatOnSave": true,
    "editor.rulers": [100],
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

## Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pandas-stubs, PyQt6-stubs]
        args: [--strict]
```

## GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Lint
        run: uv run ruff check src tests

      - name: Type check
        run: uv run mypy src

      - name: Test
        run: uv run pytest -m "not slow" --tb=short

  build:
    runs-on: windows-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v2

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Build executable
        run: uv run pyinstaller lumen.spec --clean --noconfirm

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: Lumen-Windows
          path: dist/Lumen.exe
```

---

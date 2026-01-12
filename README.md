# Lumen

Trading Analytics Application built with PyQt6.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd Lumen

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

## Running the Application

### From Terminal

```bash
# Using make
make run

# Or directly
uv run python -m src.main
```

### As Standalone Executable

See [Building Executable](#building-executable) below.

## Development

### Install Dev Dependencies

```bash
uv sync --all-extras
# Or
pip install -e ".[dev]"
```

### Available Commands

| Command | Description |
|---------|-------------|
| `make run` | Run the application |
| `make test` | Run all tests |
| `make test-quick` | Run tests (excluding slow tests) |
| `make lint` | Run linter (ruff) |
| `make format` | Format code (black + ruff) |
| `make typecheck` | Run type checker (mypy) |
| `make clean` | Clean build artifacts |
| `make build` | Build standalone executable |
| `make build-clean` | Clean and rebuild executable |

## Building Executable

Build a standalone `.exe` file that can run without Python installed.

### Prerequisites

Ensure dev dependencies are installed:

```bash
uv sync --all-extras
# Or
pip install -e ".[dev]"
```

### Build Command

```bash
make build
```

Or directly:

```bash
pyinstaller lumen.spec
```

### Output

The executable will be created at:

```
dist/Lumen.exe
```

Double-click `Lumen.exe` to launch the application.

### Troubleshooting

- **First build is slow**: PyInstaller analyzes all dependencies on first run. Subsequent builds are faster.
- **Antivirus warnings**: Some antivirus software may flag PyInstaller executables. This is a false positive common with PyInstaller.
- **Missing modules**: If the app crashes on startup, check for missing hidden imports in `lumen.spec`.

## Project Structure

```
Lumen/
├── src/
│   ├── core/          # Business logic
│   ├── tabs/          # Tab widgets
│   └── ui/            # UI components
├── tests/             # Test files
├── assets/            # Fonts and resources
├── docs/              # Documentation
├── lumen.spec         # PyInstaller configuration
└── pyproject.toml     # Project configuration
```

## License

[Add license information]

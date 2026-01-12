# 3. Tech Stack

## Technology Table

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Runtime** | Python | 3.11+ | Core language |
| **UI Framework** | PyQt6 | 6.6+ | Desktop UI |
| **Charting** | PyQtGraph | 0.13+ | GPU-accelerated charts, 83k+ points |
| **Data Processing** | Pandas | 2.1+ | DataFrame operations |
| **File I/O** | PyArrow | 14.0+ | Parquet read/write |
| **Excel Reading** | openpyxl | 3.1+ | .xlsx file support |
| **Package Manager** | uv | Latest | Fast dependency management |
| **Formatter** | Black | 24.4+ | Code formatting |
| **Linter** | Ruff | 0.4+ | Fast linting |
| **Type Checker** | mypy | 1.10+ | Static type analysis |
| **Testing** | pytest | 8.0+ | Test framework |
| **Qt Testing** | pytest-qt | 4.3+ | Widget testing |
| **Build** | PyInstaller | 6.0+ | Executable packaging |

## Rationale for Key Choices

| Choice | Rationale |
|--------|-----------|
| PyQt6 over Tkinter | Professional widgets, native look, better documentation |
| PyQtGraph over Matplotlib | GPU acceleration, handles 83k+ points at 60fps |
| Pandas over Polars | More mature, better documentation, sufficient for single-user |
| Parquet over SQLite | 10-20x faster for analytical workloads, columnar storage |
| uv over pip | 10-100x faster installs, reliable lockfiles |

---

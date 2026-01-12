# 4. Technical Assumptions

## Repository Structure

**Structure: Monorepo**

```
Lumen/
├── src/                    # Application source code
│   ├── __init__.py
│   ├── main.py             # Entry point
│   ├── core/               # Shared utilities, data models, metrics engine
│   ├── ui/                 # Common UI components, themes
│   ├── data_input/         # Tab 1: File loading, column config, first trigger
│   ├── feature_explorer/   # Tab 2: Filtering, charting
│   ├── pnl_stats/          # Tab 3: Metrics display, comparison, charts
│   └── monte_carlo/        # Tab 4: Placeholder (Phase 3)
├── tests/                  # Unit and integration tests
├── assets/
│   └── fonts/              # Space Grotesk, IBM Plex Sans, JetBrains Mono
├── docs/                   # Documentation (PRD, architecture)
├── .lumen_cache/           # Parquet cache, column mappings
├── pyproject.toml          # Project configuration
└── uv.lock                 # Dependency lock file
```

## Service Architecture

**Architecture: Monolithic Desktop Application**

- Single-process application with in-memory data storage
- Tab-based UI with shared DataFrame context
- Event-driven architecture for UI updates (Qt signals/slots)
- No microservices, no backend server, no API layer
- All processing happens locally on user's machine

## Testing Requirements

**Level: Unit + Integration Testing**

| Test Type | Scope | Tools |
|-----------|-------|-------|
| Unit Tests | Metrics calculations, first trigger logic, filters | pytest |
| Integration Tests | Tab workflows, data flow between components | pytest + pytest-qt |
| Manual Testing | UI interactions, visual verification | Developer testing |

## Additional Technical Assumptions

- **Python 3.10+** — Required for modern type hints and performance
- **uv for dependency management** — Fast Rust-based package manager
- **pyproject.toml for project config** — Modern Python project standard
- **Pandas for data processing** — Chosen for reliability and documentation
- **Parquet for storage** — 10-20x faster than CSV; automatic conversion on load
- **PyQt6 for UI** — Native desktop look, professional widgets
- **PyQtGraph for charting** — GPU-accelerated, handles 83k+ points smoothly
- **PyArrow for Parquet I/O** — Standard library for Parquet read/write
- **openpyxl for Excel reading** — Handles .xlsx files
- **No external APIs** — Fully offline operation
- **No database** — In-memory DataFrame is sufficient for single-file analysis
- **No authentication** — Single-user desktop application
- **qdarkstyle or custom QSS** — For dark mode theming

---

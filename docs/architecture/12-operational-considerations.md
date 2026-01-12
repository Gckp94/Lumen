# 12. Operational Considerations

## Logging Configuration

```python
# src/logging_config.py
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(debug: bool = False) -> None:
    log_dir = Path.home() / ".lumen" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / "lumen.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    root_logger.addHandler(file_handler)

    # Reduce third-party noise
    logging.getLogger("PyQt6").setLevel(logging.WARNING)
    logging.getLogger("pyqtgraph").setLevel(logging.WARNING)
```

## Crash Reporting

```python
# src/crash_reporter.py
import traceback
from datetime import datetime
from pathlib import Path

def save_crash_report(exc_type, exc_value, exc_traceback) -> Path:
    crash_dir = Path.home() / ".lumen" / "crashes"
    crash_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    crash_file = crash_dir / f"crash_{timestamp}.txt"

    with open(crash_file, "w") as f:
        f.write(f"Lumen Crash Report\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Version: {__version__}\n\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)

    return crash_file
```

## User Data Locations

```
~/.lumen/                      # User data directory
├── logs/
│   └── lumen.log              # Application log (rotated)
└── crashes/
    └── crash_*.txt            # Crash reports

.lumen_cache/                  # Project-local cache
├── {file_hash}.parquet        # Cached data files
├── {file_hash}_mappings.json  # Column mappings
└── window_state.json          # Window position/size
```

## Performance Monitoring (Development)

```python
# src/utils/profiling.py
from functools import wraps
from time import perf_counter

def timed(func):
    """Decorator to log function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        logger.debug("%s completed in %.3fs", func.__name__, elapsed)
        return result
    return wrapper
```

---

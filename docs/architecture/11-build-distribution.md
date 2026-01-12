# 11. Build & Distribution

## PyInstaller Configuration

```python
# lumen.spec
block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/fonts/*.ttf', 'assets/fonts'),
        ('assets/fonts/*.otf', 'assets/fonts'),
    ],
    hiddenimports=[
        'PyQt6.QtSvg',
        'pyqtgraph.opengl',
    ],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Lumen',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
)
```

## Build Commands

```makefile
# Production build
build:
	uv run pyinstaller lumen.spec --clean --noconfirm

# Development build (with console)
build-dev:
	uv run pyinstaller src/main.py --name Lumen-Dev --onedir --console --add-data "assets/fonts:assets/fonts"
```

## Version Management

```python
# src/__version__.py
__version__ = "1.0.0"

# src/main.py
from src.__version__ import __version__

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Lumen v{__version__}")
```

## Distribution Checklist

| Item | Requirement |
|------|-------------|
| Single .exe file | PyInstaller --onefile |
| No installer needed | Portable executable |
| Fonts bundled | Azeret Mono, Geist |
| Icon embedded | assets/icon.ico |
| Version in title | "Lumen v1.0.0" |
| Windows 10/11 | Target platform |
| No admin required | User-space execution |

---

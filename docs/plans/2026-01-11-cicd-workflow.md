# CI/CD Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement GitHub Actions CI/CD pipeline for automated testing, linting, and Windows executable builds.

**Architecture:** Two-job workflow: (1) `test` job runs lint, typecheck, and pytest on every push/PR; (2) `build` job creates Windows executable via PyInstaller, only runs after tests pass. Uses `uv` for fast dependency management and `windows-latest` runner for native builds.

**Tech Stack:** GitHub Actions, uv, ruff, mypy, pytest, PyInstaller

---

## Task 1: Create GitHub Actions Directory Structure

**Files:**
- Create: `.github/workflows/` (directory)

**Step 1: Create the directory structure**

```bash
mkdir -p .github/workflows
```

**Step 2: Verify directory exists**

Run: `ls -la .github/workflows/`
Expected: Empty directory exists

**Step 3: Commit**

```bash
git add .github/
git commit -m "chore: create GitHub Actions workflow directory"
```

---

## Task 2: Create CI Workflow File

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create the CI workflow file**

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

**Step 2: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: No errors (requires pyyaml, or use online YAML validator)

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for testing and builds"
```

---

## Task 3: Create PyInstaller Spec File

**Files:**
- Create: `lumen.spec`

**Step 1: Create the PyInstaller spec file**

```python
# -*- mode: python ; coding: utf-8 -*-
# lumen.spec - PyInstaller configuration for Lumen

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
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',  # Uncomment when icon is available
)
```

**Step 2: Verify spec file syntax**

Run: `python -c "exec(open('lumen.spec').read())"`
Expected: No syntax errors

**Step 3: Commit**

```bash
git add lumen.spec
git commit -m "build: add PyInstaller spec file for Windows executable"
```

---

## Task 4: Test Local Build (Optional Verification)

**Files:**
- None (verification only)

**Step 1: Run local build to verify spec works**

Run: `uv run pyinstaller lumen.spec --clean --noconfirm`
Expected: Build completes, `dist/Lumen.exe` created

**Step 2: Verify executable exists**

Run: `ls -la dist/Lumen.exe`
Expected: File exists with reasonable size (50-100+ MB)

**Step 3: Clean up build artifacts**

Run: `rm -rf build/ dist/`
Expected: Directories removed

---

## Task 5: Update .gitignore for Build Artifacts

**Files:**
- Modify: `.gitignore`

**Step 1: Verify build artifacts are already ignored**

Check `.gitignore` for these patterns:
- `build/`
- `dist/`
- `*.spec` should NOT be ignored (we want to track lumen.spec)

**Step 2: Add any missing patterns if needed**

If `build/` or `dist/` are missing, add them:

```gitignore
# PyInstaller
build/
dist/
```

**Step 3: Commit if changes made**

```bash
git add .gitignore
git commit -m "chore: ensure build artifacts are gitignored"
```

---

## Task 6: Create Workflow Documentation

**Files:**
- Modify: `docs/architecture/7-development-workflow.md` (if needed)

**Step 1: Verify architecture docs are accurate**

The architecture document already contains the CI/CD specification. No changes needed unless implementation differs.

**Step 2: Final commit with all changes**

```bash
git status
git log --oneline -5
```

Expected: See commits for workflow directory, ci.yml, and lumen.spec

---

## Summary

| Task | Files | Action |
|------|-------|--------|
| 1 | `.github/workflows/` | Create directory |
| 2 | `.github/workflows/ci.yml` | Create CI workflow |
| 3 | `lumen.spec` | Create PyInstaller spec |
| 4 | (verification) | Test local build |
| 5 | `.gitignore` | Verify/update patterns |
| 6 | (documentation) | Verify accuracy |

## Post-Implementation

After pushing to `main` or creating a PR:
1. GitHub Actions should trigger automatically
2. `test` job should run lint, typecheck, and pytest
3. `build` job should create and upload `Lumen-Windows` artifact
4. Download artifact from Actions tab to verify executable

## Known Limitations

1. **No icon.ico**: The spec file has the icon line commented out. Create `assets/icon.ico` when branding is finalized.
2. **Windows-only**: CI runs on `windows-latest`. Cross-platform builds would require matrix strategy.
3. **No releases**: This workflow builds on every push. Add release workflow later for versioned releases.

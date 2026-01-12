# -*- mode: python ; coding: utf-8 -*-
# lumen.spec - PyInstaller configuration for Lumen

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Font files will be included when available
        # ('assets/fonts/*.ttf', 'assets/fonts'),
        # ('assets/fonts/*.otf', 'assets/fonts'),
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

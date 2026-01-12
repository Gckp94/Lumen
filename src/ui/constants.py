"""UI constants for the Lumen application.

Contains theme colors, fonts, spacing, and animation timing values.
"""


class Colors:
    """Observatory Palette - semantic colors are inviolable."""

    # Backgrounds
    BG_BASE = "#0C0C12"  # Main window background (void-black)
    BG_SURFACE = "#141420"  # Tab content areas (space-dark)
    BG_ELEVATED = "#1E1E2C"  # Elevated surfaces
    BG_BORDER = "#2A2A3A"  # Borders

    # Signal Colors (semantic - never change meaning)
    SIGNAL_CYAN = "#00FFD4"  # ALWAYS positive (plasma-cyan)
    SIGNAL_CORAL = "#FF4757"  # ALWAYS negative (solar-coral)
    SIGNAL_AMBER = "#FFAA00"  # ALWAYS attention
    SIGNAL_BLUE = "#4A9EFF"  # ALWAYS reference (stellar-blue)

    # Text
    TEXT_PRIMARY = "#F4F4F8"  # Primary text (star-white)
    TEXT_SECONDARY = "#9898A8"  # Secondary text (nebula-gray)
    TEXT_DISABLED = "#5C5C6C"  # Disabled/dimmed text


class Fonts:
    """Font family definitions."""

    DATA = "Azeret Mono"  # For numbers and data display
    UI = "Geist"  # For UI text


class FontSizes:
    """Font size constants in pixels."""

    KPI_HERO = 48
    KPI_LARGE = 32
    H1 = 24
    H2 = 18
    BODY = 13


class Spacing:
    """Spacing constants in pixels."""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Animation:
    """Animation timing constants in milliseconds."""

    NUMBER_TICKER = 150
    DELTA_FLASH = 200
    TAB_SWITCH = 150
    DEBOUNCE_INPUT = 150
    DEBOUNCE_METRICS = 300
    LOADING_MIN_DURATION = 400


class Limits:
    """Application limits."""

    MAX_FILTERS = 10
    MIN_WINDOW_WIDTH = 1280
    MIN_WINDOW_HEIGHT = 720
    MAX_RECENT_FILES = 10
    CACHE_MAX_AGE_DAYS = 30

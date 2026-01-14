"""Theme management for the Lumen application.

Provides font loading and QSS stylesheet generation.
"""

import logging
from pathlib import Path

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from src.ui.constants import Colors, Fonts, Spacing

logger = logging.getLogger(__name__)


def load_fonts(app: QApplication) -> bool:
    """Load custom fonts from assets/fonts/.

    Args:
        app: The QApplication instance (unused but kept for API consistency).

    Returns:
        True if at least one font was loaded successfully, False otherwise.
    """
    font_dir = Path(__file__).parent.parent.parent / "assets" / "fonts"

    if not font_dir.exists():
        logger.info(
            "Custom fonts directory not found at %s - using system fonts. "
            "This is normal if no custom fonts have been configured.",
            font_dir
        )
        return False

    fonts_loaded = 0
    for font_file in font_dir.glob("*.[to]tf"):  # .ttf and .otf
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id >= 0:
            fonts_loaded += 1
            logger.debug("Loaded font: %s", font_file.name)
        else:
            logger.warning("Failed to load font: %s", font_file.name)

    if fonts_loaded > 0:
        logger.info("Loaded %d custom fonts", fonts_loaded)
    else:
        logger.info("No custom fonts found in %s - using system fonts", font_dir)

    return fonts_loaded > 0


def get_stylesheet() -> str:
    """Generate the complete QSS stylesheet for the application.

    Returns:
        A string containing the complete QSS stylesheet.
    """
    return f"""
/* ========================================
   Lumen Observatory Theme
   ======================================== */

/* Main Window */
QMainWindow {{
    background-color: {Colors.BG_BASE};
}}

/* Tab Widget Pane (content area) */
QTabWidget::pane {{
    background-color: {Colors.BG_SURFACE};
    border: 1px solid {Colors.BG_BORDER};
    border-top: none;
}}

/* Tab Bar */
QTabBar {{
    background-color: transparent;
}}

QTabBar::tab {{
    background-color: {Colors.TEXT_SECONDARY};
    color: {Colors.TEXT_PRIMARY};
    padding: {Spacing.SM}px {Spacing.LG}px;
    border: none;
    min-width: 120px;
    font-family: "{Fonts.UI}";
    font-size: 13px;
}}

QTabBar::tab:selected {{
    background-color: {Colors.BG_SURFACE};
    border-bottom: 2px solid {Colors.SIGNAL_CYAN};
}}

QTabBar::tab:hover:!selected {{
    background-color: {Colors.BG_ELEVATED};
}}

/* ========================================
   PyQtAds Dock Widget Styling
   ======================================== */

/* Dock Area Widget (container for tabbed docks) */
ads--CDockAreaWidget {{
    background-color: {Colors.BG_SURFACE};
    border: 1px solid {Colors.BG_BORDER};
}}

/* Dock Area Title Bar */
ads--CDockAreaTitleBar {{
    background-color: {Colors.BG_BASE};
    border-bottom: 1px solid {Colors.BG_BORDER};
    padding: 0px;
    min-height: 32px;
}}

/* Dock Area Tab Bar */
ads--CDockAreaTabBar {{
    background-color: {Colors.BG_BASE};
}}

/* Individual Dock Widget Tabs */
ads--CDockWidgetTab {{
    background-color: {Colors.TEXT_SECONDARY};
    color: {Colors.TEXT_PRIMARY};
    padding: {Spacing.SM}px {Spacing.LG}px;
    border: none;
    min-width: 120px;
    font-family: "{Fonts.UI}";
    font-size: 13px;
}}

ads--CDockWidgetTab[activeTab="true"] {{
    background-color: {Colors.BG_SURFACE};
    border-bottom: 2px solid {Colors.SIGNAL_CYAN};
}}

ads--CDockWidgetTab:hover {{
    background-color: {Colors.BG_ELEVATED};
}}

/* Dock Widget Tab Close Button - Hidden since tabs aren't closable */
ads--CDockWidgetTab > QPushButton {{
    background-color: transparent;
    border: none;
}}

/* Floating Dock Container (undocked window) */
ads--CFloatingDockContainer {{
    background-color: {Colors.BG_BASE};
    border: 1px solid {Colors.BG_BORDER};
}}

/* Dock Splitter */
ads--CDockSplitter::handle {{
    background-color: {Colors.BG_BORDER};
}}

ads--CDockSplitter::handle:hover {{
    background-color: {Colors.SIGNAL_CYAN};
}}

/* Dock Area Menu Button */
ads--CTitleBarButton {{
    background-color: transparent;
    border: none;
    padding: 4px;
}}

ads--CTitleBarButton:hover {{
    background-color: {Colors.BG_ELEVATED};
    border-radius: 4px;
}}

/* General Widget Styling */
QWidget {{
    background-color: transparent;
    color: {Colors.TEXT_PRIMARY};
    font-family: "{Fonts.UI}";
    font-size: 13px;
}}

/* Labels */
QLabel {{
    color: {Colors.TEXT_PRIMARY};
    background-color: transparent;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background-color: {Colors.BG_BASE};
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {Colors.BG_BORDER};
    min-height: 30px;
    border-radius: 6px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {Colors.TEXT_SECONDARY};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {Colors.BG_BASE};
    height: 12px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {Colors.BG_BORDER};
    min-width: 30px;
    border-radius: 6px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {Colors.TEXT_SECONDARY};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Buttons */
QPushButton {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    padding: {Spacing.SM}px {Spacing.LG}px;
    border-radius: 4px;
    font-family: "{Fonts.UI}";
}}

QPushButton:hover {{
    background-color: {Colors.BG_BORDER};
    border-color: {Colors.SIGNAL_CYAN};
}}

QPushButton:pressed {{
    background-color: {Colors.BG_BASE};
}}

QPushButton:disabled {{
    color: {Colors.TEXT_DISABLED};
    border-color: {Colors.BG_BORDER};
}}

/* Line Edits */
QLineEdit {{
    background-color: {Colors.BG_BASE};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    padding: {Spacing.SM}px;
    border-radius: 4px;
    font-family: "{Fonts.DATA}";
}}

QLineEdit:focus {{
    border-color: {Colors.SIGNAL_CYAN};
}}

/* Combo Boxes */
QComboBox {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    padding: {Spacing.SM}px;
    border-radius: 4px;
}}

QComboBox:hover {{
    border-color: {Colors.SIGNAL_CYAN};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    selection-background-color: {Colors.BG_BORDER};
    selection-color: {Colors.TEXT_PRIMARY};
}}

/* Tool Tips */
QToolTip {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    padding: {Spacing.XS}px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the complete theme to the application.

    This is the main entry point for theme application. It loads fonts
    and applies the stylesheet.

    Args:
        app: The QApplication instance to apply the theme to.
    """
    load_fonts(app)
    app.setStyleSheet(get_stylesheet())
    logger.info("Theme applied successfully")

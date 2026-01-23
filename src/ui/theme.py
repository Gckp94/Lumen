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
    padding-right: 24px;
    border-radius: 4px;
}}

QComboBox:hover {{
    border-color: {Colors.SIGNAL_CYAN};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 20px;
    border: none;
    border-left: 1px solid {Colors.BG_BORDER};
}}

QComboBox::down-arrow {{
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {Colors.TEXT_SECONDARY};
}}

QComboBox::down-arrow:hover {{
    border-top-color: {Colors.TEXT_PRIMARY};
}}

/* Dropdown styling handled by widget-level stylesheets */

/* Tool Tips */
QToolTip {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    padding: {Spacing.XS}px;
}}

/* ========================================
   Table Widgets
   ======================================== */

/* Base Table Styling */
QTableWidget, QTableView {{
    background-color: {Colors.BG_SURFACE};
    alternate-background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    gridline-color: {Colors.BG_BORDER};
    border: 1px solid {Colors.BG_BORDER};
    border-radius: 4px;
    selection-background-color: rgba(0, 255, 212, 0.15);
    selection-color: {Colors.TEXT_PRIMARY};
}}

QTableWidget::item, QTableView::item {{
    padding: 6px 8px;
    border: none;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: rgba(0, 255, 212, 0.15);
    color: {Colors.TEXT_PRIMARY};
}}

QTableWidget::item:hover, QTableView::item:hover {{
    background-color: rgba(0, 255, 212, 0.08);
}}

/* Table Header Styling */
QHeaderView {{
    background-color: transparent;
}}

QHeaderView::section {{
    background-color: {Colors.BG_BASE};
    color: {Colors.TEXT_SECONDARY};
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {Colors.BG_BORDER};
    border-right: 1px solid {Colors.BG_BORDER};
    font-family: "{Fonts.UI}";
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QHeaderView::section:last {{
    border-right: none;
}}

QHeaderView::section:hover {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
}}

/* Corner button (top-left of tables with both headers) */
QTableCornerButton::section {{
    background-color: {Colors.BG_BASE};
    border: none;
    border-bottom: 1px solid {Colors.BG_BORDER};
    border-right: 1px solid {Colors.BG_BORDER};
}}

/* ========================================
   Spin Boxes
   ======================================== */

QSpinBox, QDoubleSpinBox {{
    background-color: {Colors.BG_BASE};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    padding-right: 20px;
    font-family: "{Fonts.DATA}";
    min-height: 24px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Colors.SIGNAL_CYAN};
}}

QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {Colors.TEXT_DISABLED};
    background-color: {Colors.BG_ELEVATED};
}}

/* Spin box buttons */
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border: none;
    border-left: 1px solid {Colors.BG_BORDER};
    border-top-right-radius: 4px;
    background-color: {Colors.BG_ELEVATED};
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border: none;
    border-left: 1px solid {Colors.BG_BORDER};
    border-bottom-right-radius: 4px;
    background-color: {Colors.BG_ELEVATED};
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {Colors.BG_BORDER};
}}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background-color: {Colors.BG_BASE};
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 6px solid {Colors.TEXT_SECONDARY};
}}

QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{
    border-bottom-color: {Colors.TEXT_PRIMARY};
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {Colors.TEXT_SECONDARY};
}}

QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
    border-top-color: {Colors.TEXT_PRIMARY};
}}

/* ========================================
   Group Boxes
   ======================================== */

QGroupBox {{
    background-color: {Colors.BG_SURFACE};
    border: 1px solid {Colors.BG_BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding: 16px;
    padding-top: 24px;
    font-family: "{Fonts.UI}";
    font-weight: 500;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 4px;
    color: {Colors.TEXT_SECONDARY};
    background-color: {Colors.BG_SURFACE};
    padding: 0 8px;
}}

/* ========================================
   Dialogs
   ======================================== */

QDialog {{
    background-color: {Colors.BG_BASE};
}}

/* ========================================
   Menus
   ======================================== */

QMenu {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BG_BORDER};
    border-radius: 4px;
    padding: 4px 0;
}}

QMenu::item {{
    padding: 8px 24px;
}}

QMenu::item:selected {{
    background-color: rgba(0, 255, 212, 0.15);
}}

QMenu::separator {{
    height: 1px;
    background-color: {Colors.BG_BORDER};
    margin: 4px 8px;
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the complete theme to the application.

    This is the main entry point for theme application. It loads fonts
    and applies the stylesheet.

    Args:
        app: The QApplication instance to apply the theme to.
    """
    # Use Fusion style to bypass native Windows theming for consistent dark theme
    app.setStyle("Fusion")
    load_fonts(app)
    app.setStyleSheet(get_stylesheet())
    logger.info("Theme applied successfully")

"""Lumen - Trading Analytics Application."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from src.__version__ import __version__
from src.core.config import CHECK_FOR_UPDATES, GITHUB_OWNER, GITHUB_REPO
from src.core.update_checker import UpdateChecker
from src.ui import theme
from src.ui.dialogs.update_dialog import UpdateDialog
from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def check_for_updates() -> None:
    """Check for updates and show dialog if available."""
    if not CHECK_FOR_UPDATES:
        return

    try:
        checker = UpdateChecker(GITHUB_OWNER, GITHUB_REPO)
        update_info = checker.check_for_update(__version__)

        if update_info:
            dialog = UpdateDialog(update_info, __version__)
            dialog.exec()
    except Exception as e:
        logger.error("Update check failed: %s", e)


def main() -> int:
    """Application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Lumen %s", __version__)

    app = QApplication(sys.argv)

    # Load fonts and apply theme
    theme.load_fonts(app)
    app.setStyleSheet(theme.get_stylesheet())

    # Check for updates before showing main window
    check_for_updates()

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

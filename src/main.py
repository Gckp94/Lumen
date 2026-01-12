"""Lumen - Trading Analytics Application."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from src.ui import theme
from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> int:
    """Application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Lumen")

    app = QApplication(sys.argv)

    # Load fonts and apply theme
    theme.load_fonts(app)
    app.setStyleSheet(theme.get_stylesheet())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

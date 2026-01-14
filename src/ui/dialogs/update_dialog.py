"""Update notification dialog.

Displays information about available updates and allows user to
download or skip the update.
"""

import logging
import webbrowser

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.update_checker import UpdateInfo

logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """Dialog showing available update information.

    Displays version comparison and provides options to download
    or skip the update.
    """

    def __init__(
        self,
        update_info: UpdateInfo,
        current_version: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the update dialog.

        Args:
            update_info: Information about the available update.
            current_version: Currently installed version.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.update_info = update_info
        self.current_version = current_version

        self.setWindowTitle("Update Available")
        self.setMinimumWidth(400)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("A new version of Lumen is available!")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Version info
        self.message_label = QLabel(
            f"Current version: {self.current_version}\n"
            f"New version: {self.update_info.version}"
        )
        layout.addWidget(self.message_label)

        # Buttons
        self.button_box = QDialogButtonBox()

        update_btn = QPushButton("Download Update")
        update_btn.clicked.connect(self._on_download)
        self.button_box.addButton(update_btn, QDialogButtonBox.ButtonRole.AcceptRole)

        skip_btn = QPushButton("Skip")
        skip_btn.clicked.connect(self.reject)
        self.button_box.addButton(skip_btn, QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(self.button_box)

    def _on_download(self) -> None:
        """Handle download button click."""
        logger.info("Opening download URL: %s", self.update_info.release_url)
        webbrowser.open(self.update_info.release_url)
        self.accept()

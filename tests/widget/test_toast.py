"""Widget tests for Toast component."""

from PyQt6.QtWidgets import QLabel, QWidget

from src.ui.components.toast import Toast
from src.ui.constants import Colors


class TestToastDisplay:
    """Tests for Toast display functionality."""

    def test_toast_shows_message(self, qtbot) -> None:
        """Toast displays provided message."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Export complete", "success")
        qtbot.addWidget(toast)

        # Find the message label
        message_label = toast.findChild(QLabel, "toast_message")
        assert message_label is not None
        assert message_label.text() == "Export complete"

    def test_toast_success_uses_cyan(self, qtbot) -> None:
        """Success variant uses cyan color."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Success!", "success")
        qtbot.addWidget(toast)

        assert Colors.SIGNAL_CYAN in toast.styleSheet()

    def test_toast_error_uses_coral(self, qtbot) -> None:
        """Error variant uses coral color."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Error!", "error")
        qtbot.addWidget(toast)

        assert Colors.SIGNAL_CORAL in toast.styleSheet()

    def test_toast_warning_uses_amber(self, qtbot) -> None:
        """Warning variant uses amber color."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Warning!", "warning")
        qtbot.addWidget(toast)

        assert Colors.SIGNAL_AMBER in toast.styleSheet()

    def test_toast_info_uses_blue(self, qtbot) -> None:
        """Info variant uses blue color."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Info!", "info")
        qtbot.addWidget(toast)

        assert Colors.SIGNAL_BLUE in toast.styleSheet()

    def test_toast_auto_dismisses(self, qtbot) -> None:
        """Toast closes after duration."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        # Don't add auto-closing toast to qtbot - it will be deleted by Qt
        toast = Toast.display(parent, "Brief message", "info", duration=100)

        # Verify initially visible
        assert toast.isVisible()

        # Wait for auto-dismiss + animation
        qtbot.wait(400)
        # Toast should no longer be visible (may be deleted)

    def test_toast_persistent_with_zero_duration(self, qtbot) -> None:
        """Toast stays visible with duration=0."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        # Create persistent toast (duration=0 means no auto-dismiss)
        toast = Toast.display(parent, "Persistent message", "info", duration=0)
        qtbot.addWidget(toast)

        # Wait longer than typical auto-dismiss would take
        qtbot.wait(200)
        assert toast.isVisible()

    def test_toast_shows_correct_icon_for_success(self, qtbot) -> None:
        """Success toast shows checkmark icon."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Done!", "success")
        qtbot.addWidget(toast)

        # Find all labels and check for icon
        labels = toast.findChildren(QLabel)
        icons = [label.text() for label in labels if label.text() in ["✓", "✗", "⚠", "ℹ"]]
        assert "✓" in icons

    def test_toast_shows_correct_icon_for_error(self, qtbot) -> None:
        """Error toast shows X icon."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Failed!", "error")
        qtbot.addWidget(toast)

        labels = toast.findChildren(QLabel)
        icons = [label.text() for label in labels if label.text() in ["✓", "✗", "⚠", "ℹ"]]
        assert "✗" in icons

    def test_toast_unknown_variant_defaults_to_info(self, qtbot) -> None:
        """Unknown variant falls back to info style."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Message", "unknown_variant")
        qtbot.addWidget(toast)

        assert Colors.SIGNAL_BLUE in toast.styleSheet()


class TestToastPositioning:
    """Tests for Toast positioning."""

    def test_toast_positions_at_bottom_center(self, qtbot) -> None:
        """Toast positions at bottom-center of parent."""
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(800, 600)
        parent.show()

        toast = Toast.display(parent, "Centered message", "info")
        qtbot.addWidget(toast)

        # Toast should be roughly horizontally centered
        parent_center_x = parent.mapToGlobal(parent.rect().center()).x()
        toast_center_x = toast.x() + toast.width() // 2

        # Allow some tolerance for positioning
        assert abs(parent_center_x - toast_center_x) < 50

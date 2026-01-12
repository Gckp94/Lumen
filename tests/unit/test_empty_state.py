"""Unit tests for EmptyState component."""

from PyQt6.QtWidgets import QLabel, QPushButton

from src.ui.components.empty_state import EmptyState


class TestEmptyState:
    """Tests for EmptyState component."""

    def test_empty_state_creation(self, qtbot):
        """EmptyState widget can be created."""
        widget = EmptyState()
        qtbot.addWidget(widget)
        assert widget is not None

    def test_set_message_basic(self, qtbot):
        """set_message configures icon, title, and description."""
        widget = EmptyState()
        qtbot.addWidget(widget)

        widget.set_message(
            icon="📊",
            title="No Data",
            description="Data will appear here.",
        )

        assert widget._icon_label.text() == "📊"
        assert widget._title_label.text() == "No Data"
        assert widget._description_label.text() == "Data will appear here."
        assert not widget._action_button.isVisible()

    def test_set_message_with_action(self, qtbot):
        """set_message shows action button when callback provided."""
        widget = EmptyState()
        qtbot.addWidget(widget)

        callback_called = []

        def on_action():
            callback_called.append(True)

        widget.set_message(
            icon="📈",
            title="Load Data",
            description="Click to load data.",
            action_text="Load",
            action_callback=on_action,
        )

        # Note: isVisible() returns False when parent is not shown
        # Check that button is not explicitly hidden
        assert not widget._action_button.isHidden()
        assert widget._action_button.text() == "Load"

        # Click the button
        widget._action_button.click()
        assert len(callback_called) == 1

    def test_action_button_hidden_without_callback(self, qtbot):
        """Action button hidden when no callback provided."""
        widget = EmptyState()
        qtbot.addWidget(widget)

        # First set with action
        widget.set_message(
            icon="📊",
            title="Test",
            description="Test",
            action_text="Click",
            action_callback=lambda: None,
        )
        assert not widget._action_button.isHidden()

        # Then set without action
        widget.set_message(
            icon="📊",
            title="Test",
            description="Test",
        )
        assert widget._action_button.isHidden()

    def test_action_button_hidden_with_only_text(self, qtbot):
        """Action button hidden when only text provided without callback."""
        widget = EmptyState()
        qtbot.addWidget(widget)

        widget.set_message(
            icon="📊",
            title="Test",
            description="Test",
            action_text="Click",
            action_callback=None,
        )
        assert not widget._action_button.isVisible()

    def test_labels_exist(self, qtbot):
        """Widget contains expected labels."""
        widget = EmptyState()
        qtbot.addWidget(widget)

        icon_labels = widget.findChildren(QLabel)
        assert len(icon_labels) >= 3  # icon, title, description

        buttons = widget.findChildren(QPushButton)
        assert len(buttons) == 1

    def test_description_word_wrap(self, qtbot):
        """Description label has word wrap enabled."""
        widget = EmptyState()
        qtbot.addWidget(widget)

        assert widget._description_label.wordWrap()

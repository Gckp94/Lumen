"""Tests for FlowLayout utility."""

import pytest
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton
from PyQt6.QtCore import Qt

from src.ui.utils.flow_layout import FlowLayout


@pytest.fixture(scope="module")
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestFlowLayout:
    """Tests for FlowLayout widget."""

    def test_flow_layout_creation(self, app):
        """FlowLayout can be created and added to widget."""
        widget = QWidget()
        layout = FlowLayout()
        widget.setLayout(layout)

        assert layout.count() == 0

    def test_flow_layout_add_items(self, app):
        """FlowLayout can add widgets."""
        widget = QWidget()
        layout = FlowLayout()
        widget.setLayout(layout)

        btn1 = QPushButton("Test 1")
        btn2 = QPushButton("Test 2")

        layout.addWidget(btn1)
        layout.addWidget(btn2)

        assert layout.count() == 2

    def test_flow_layout_height_for_width(self, app):
        """FlowLayout reports correct height for given width."""
        widget = QWidget()
        layout = FlowLayout(spacing=4)
        widget.setLayout(layout)

        # Add some buttons
        for i in range(5):
            btn = QPushButton(f"Button {i}")
            btn.setFixedWidth(100)
            layout.addWidget(btn)

        # Wide enough for all items on one line
        height_wide = layout.heightForWidth(600)

        # Narrow - should need multiple lines
        height_narrow = layout.heightForWidth(200)

        assert height_narrow > height_wide

    def test_flow_layout_clear(self, app):
        """FlowLayout can clear all items."""
        widget = QWidget()
        layout = FlowLayout()
        widget.setLayout(layout)

        for i in range(3):
            layout.addWidget(QPushButton(f"Test {i}"))

        assert layout.count() == 3

        # Clear by removing all items
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        assert layout.count() == 0

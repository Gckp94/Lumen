"""Unit tests for the theme module."""

from src.ui.theme import get_stylesheet


class TestGetStylesheet:
    """Tests for the get_stylesheet function."""

    def test_get_stylesheet_returns_string(self) -> None:
        """Stylesheet function returns non-empty string."""
        stylesheet = get_stylesheet()
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0

    def test_stylesheet_contains_bg_base_color(self) -> None:
        """Stylesheet includes BG_BASE color value."""
        stylesheet = get_stylesheet()
        assert "#0C0C12" in stylesheet

    def test_stylesheet_contains_bg_surface_color(self) -> None:
        """Stylesheet includes BG_SURFACE color value."""
        stylesheet = get_stylesheet()
        assert "#141420" in stylesheet

    def test_stylesheet_contains_signal_cyan(self) -> None:
        """Stylesheet includes SIGNAL_CYAN for accent."""
        stylesheet = get_stylesheet()
        assert "#00FFD4" in stylesheet

    def test_stylesheet_contains_text_colors(self) -> None:
        """Stylesheet includes text color values."""
        stylesheet = get_stylesheet()
        assert "#F4F4F8" in stylesheet  # TEXT_PRIMARY
        assert "#9898A8" in stylesheet  # TEXT_SECONDARY

    def test_stylesheet_contains_main_window_styling(self) -> None:
        """Stylesheet includes QMainWindow styling."""
        stylesheet = get_stylesheet()
        assert "QMainWindow" in stylesheet

    def test_stylesheet_contains_tab_styling(self) -> None:
        """Stylesheet includes tab widget styling."""
        stylesheet = get_stylesheet()
        assert "QTabWidget" in stylesheet
        assert "QTabBar" in stylesheet

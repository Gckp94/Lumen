"""Tests for tab category configuration."""

from src.ui.tab_categories import (
    TAB_CATEGORIES,
    get_all_categories,
    get_category_for_tab,
    get_category_index,
    get_tabs_in_category,
)


class TestTabCategories:
    """Test tab category definitions."""

    def test_all_tabs_have_category(self) -> None:
        """Every tab should belong to exactly one category."""
        all_tabs = [
            "Data Input", "Feature Explorer", "Breakdown", "Data Binning",
            "P&L Stats", "Statistics",
            "Feature Insights", "Feature Impact", "Parameter Sensitivity",
            "Monte Carlo",
            "Portfolio Overview", "Portfolio Breakdown", "Portfolio Metrics",
            "Chart Viewer",
        ]

        for tab in all_tabs:
            category = get_category_for_tab(tab)
            assert category is not None, f"Tab '{tab}' has no category"

    def test_category_order(self) -> None:
        """Categories should be in workflow order."""
        expected_order = ["ANALYZE", "FEATURES", "MONTE CARLO", "PORTFOLIO", "CHARTS"]
        assert list(TAB_CATEGORIES.keys()) == expected_order

    def test_get_tabs_in_category(self) -> None:
        """Should return correct tabs for category."""
        analyze_tabs = get_tabs_in_category("ANALYZE")
        assert "Data Input" in analyze_tabs
        assert "Feature Explorer" in analyze_tabs

    def test_get_tabs_in_category_unknown(self) -> None:
        """Should return empty list for unknown category."""
        tabs = get_tabs_in_category("UNKNOWN")
        assert tabs == []

    def test_get_category_for_tab_unknown(self) -> None:
        """Should return None for unknown tab."""
        category = get_category_for_tab("Unknown Tab")
        assert category is None

    def test_get_all_categories(self) -> None:
        """Should return all category names in order."""
        categories = get_all_categories()
        assert categories == ["ANALYZE", "FEATURES", "MONTE CARLO", "PORTFOLIO", "CHARTS"]

    def test_get_category_index(self) -> None:
        """Should return correct index for category."""
        assert get_category_index("ANALYZE") == 0
        assert get_category_index("FEATURES") == 1
        assert get_category_index("MONTE CARLO") == 2
        assert get_category_index("PORTFOLIO") == 3
        assert get_category_index("CHARTS") == 4

    def test_get_category_index_unknown(self) -> None:
        """Should return -1 for unknown category."""
        assert get_category_index("UNKNOWN") == -1

    def test_tab_count(self) -> None:
        """Should have exactly 14 tabs total."""
        total_tabs = sum(len(tabs) for tabs in TAB_CATEGORIES.values())
        assert total_tabs == 14

    def test_no_duplicate_tabs(self) -> None:
        """Each tab should appear in exactly one category."""
        all_tabs = []
        for tabs in TAB_CATEGORIES.values():
            all_tabs.extend(tabs)
        assert len(all_tabs) == len(set(all_tabs)), "Duplicate tabs found"

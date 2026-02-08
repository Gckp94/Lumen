"""Tab category configuration for two-tier navigation."""

from collections import OrderedDict

# Ordered dict to preserve category display order
TAB_CATEGORIES: OrderedDict[str, list[str]] = OrderedDict([
    ("ANALYZE", [
        "Data Input",
        "Feature Explorer",
        "Breakdown",
        "Data Binning",
        "P&L Stats",
        "Statistics",
    ]),
    ("FEATURES", [
        "Feature Insights",
        "Feature Impact",
        "Parameter Sensitivity",
    ]),
    ("MONTE CARLO", [
        "Monte Carlo",
    ]),
    ("PORTFOLIO", [
        "Portfolio Overview",
        "Portfolio Breakdown",
        "Portfolio Metrics",
    ]),
    ("CHARTS", [
        "Chart Viewer",
    ]),
])

# Reverse lookup: tab name -> category
_TAB_TO_CATEGORY: dict[str, str] = {}
for category, tabs in TAB_CATEGORIES.items():
    for tab in tabs:
        _TAB_TO_CATEGORY[tab] = category


def get_category_for_tab(tab_name: str) -> str | None:
    """Get the category a tab belongs to."""
    return _TAB_TO_CATEGORY.get(tab_name)


def get_tabs_in_category(category: str) -> list[str]:
    """Get all tabs in a category."""
    return TAB_CATEGORIES.get(category, [])


def get_all_categories() -> list[str]:
    """Get all category names in order."""
    return list(TAB_CATEGORIES.keys())


def get_category_index(category: str) -> int:
    """Get the index of a category (for keyboard shortcuts)."""
    try:
        return list(TAB_CATEGORIES.keys()).index(category)
    except ValueError:
        return -1

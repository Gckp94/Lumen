"""Tests for parameter sensitivity validation logic."""

import pytest
from unittest.mock import MagicMock

from src.core.models import FilterCriteria


class TestGetAnalyzableFilters:
    """Tests for _get_analyzable_filters helper."""

    @pytest.fixture
    def tab(self):
        """Create a mock ParameterSensitivityTab with just the helper method."""
        from src.tabs.parameter_sensitivity import ParameterSensitivityTab

        # We need to test the method in isolation
        # Create a minimal mock that has our method
        mock_tab = MagicMock(spec=ParameterSensitivityTab)
        mock_tab._get_analyzable_filters = (
            ParameterSensitivityTab._get_analyzable_filters.__get__(
                mock_tab, ParameterSensitivityTab
            )
        )
        return mock_tab

    def test_all_complete_filters(self, tab):
        """All filters with both bounds should be analyzable."""
        filters = [
            FilterCriteria(column="col1", operator="between", min_val=0.0, max_val=10.0),
            FilterCriteria(column="col2", operator="between", min_val=5.0, max_val=15.0),
        ]
        analyzable, partial = tab._get_analyzable_filters(filters)
        assert len(analyzable) == 2
        assert len(partial) == 0

    def test_all_partial_filters_min_only(self, tab):
        """Filters with only min_val should be partial."""
        filters = [
            FilterCriteria(column="col1", operator="between", min_val=0.0, max_val=None),
        ]
        analyzable, partial = tab._get_analyzable_filters(filters)
        assert len(analyzable) == 0
        assert len(partial) == 1

    def test_all_partial_filters_max_only(self, tab):
        """Filters with only max_val should be partial."""
        filters = [
            FilterCriteria(column="col1", operator="between", min_val=None, max_val=10.0),
        ]
        analyzable, partial = tab._get_analyzable_filters(filters)
        assert len(analyzable) == 0
        assert len(partial) == 1

    def test_mixed_filters(self, tab):
        """Mix of complete and partial filters."""
        filters = [
            FilterCriteria(column="col1", operator="between", min_val=0.0, max_val=10.0),
            FilterCriteria(column="col2", operator="between", min_val=5.0, max_val=None),
            FilterCriteria(column="col3", operator="between", min_val=None, max_val=20.0),
        ]
        analyzable, partial = tab._get_analyzable_filters(filters)
        assert len(analyzable) == 1
        assert analyzable[0].column == "col1"
        assert len(partial) == 2

    def test_empty_filters(self, tab):
        """Empty filter list."""
        analyzable, partial = tab._get_analyzable_filters([])
        assert len(analyzable) == 0
        assert len(partial) == 0

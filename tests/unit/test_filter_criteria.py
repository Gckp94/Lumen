"""Unit tests for FilterCriteria model."""

import pandas as pd

from src.core.models import FilterCriteria


class TestFilterCriteriaBetween:
    """Tests for 'between' operator."""

    def test_between_filter_includes_boundaries(self) -> None:
        """BETWEEN filter includes min and max values (inclusive)."""
        df = pd.DataFrame({"gain_pct": [0, 5, 10]})
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.all()  # All values should match

    def test_between_filter_excludes_outside_range(self) -> None:
        """BETWEEN filter excludes values outside range."""
        df = pd.DataFrame({"gain_pct": [-1, 5, 11]})
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [False, True, False]

    def test_between_filter_single_value_range(self) -> None:
        """BETWEEN filter works with min == max."""
        df = pd.DataFrame({"gain_pct": [4, 5, 6]})
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=5, max_val=5
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [False, True, False]


class TestFilterCriteriaNotBetween:
    """Tests for 'not_between' operator."""

    def test_not_between_filter_excludes_range(self) -> None:
        """NOT BETWEEN filter excludes values in range."""
        df = pd.DataFrame({"gain_pct": [-5, 5, 15]})
        criteria = FilterCriteria(
            column="gain_pct", operator="not_between", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [True, False, True]

    def test_not_between_excludes_boundaries(self) -> None:
        """NOT BETWEEN filter excludes boundary values."""
        df = pd.DataFrame({"gain_pct": [0, 5, 10]})
        criteria = FilterCriteria(
            column="gain_pct", operator="not_between", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [False, False, False]

    def test_not_between_includes_outside(self) -> None:
        """NOT BETWEEN filter includes values outside range."""
        df = pd.DataFrame({"gain_pct": [-0.1, 10.1]})
        criteria = FilterCriteria(
            column="gain_pct", operator="not_between", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.all()


class TestFilterCriteriaValidation:
    """Tests for validate() method."""

    def test_validate_returns_error_when_min_greater_than_max(self) -> None:
        """validate() returns error when min > max."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=10, max_val=5
        )
        error = criteria.validate()
        assert error is not None
        assert "min" in error.lower() or "Min" in error

    def test_validate_returns_none_for_valid_criteria(self) -> None:
        """validate() returns None for valid criteria."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0, max_val=10
        )
        error = criteria.validate()
        assert error is None

    def test_validate_returns_none_when_min_equals_max(self) -> None:
        """validate() returns None when min == max (valid single value filter)."""
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=5, max_val=5
        )
        error = criteria.validate()
        assert error is None


class TestFilterCriteriaEdgeCases:
    """Tests for edge cases."""

    def test_filter_with_negative_values(self) -> None:
        """Filter handles negative value ranges correctly."""
        df = pd.DataFrame({"gain_pct": [-10, -5, 0, 5]})
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=-10, max_val=-5
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [True, True, False, False]

    def test_filter_with_float_precision(self) -> None:
        """Filter handles float precision correctly."""
        df = pd.DataFrame({"gain_pct": [0.0001, 0.0002, 0.0003]})
        criteria = FilterCriteria(
            column="gain_pct", operator="between", min_val=0.0001, max_val=0.0002
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [True, True, False]

    def test_filter_different_column(self) -> None:
        """Filter applies to correct column."""
        df = pd.DataFrame({"gain_pct": [1, 2, 3], "volume": [100, 200, 300]})
        criteria = FilterCriteria(
            column="volume", operator="between", min_val=150, max_val=250
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [False, True, False]


class TestFilterCriteriaBetweenBlanks:
    """Tests for 'between_blanks' operator."""

    def test_between_blanks_includes_nulls(self) -> None:
        """BETWEEN + BLANKS includes NaN/null values."""
        df = pd.DataFrame({"gain_pct": [5.0, None, float("nan")]})
        criteria = FilterCriteria(
            column="gain_pct", operator="between_blanks", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [True, True, True]

    def test_between_blanks_includes_range_and_nulls(self) -> None:
        """BETWEEN + BLANKS includes values in range AND nulls."""
        df = pd.DataFrame({"gain_pct": [-5.0, 5.0, 15.0, None]})
        criteria = FilterCriteria(
            column="gain_pct", operator="between_blanks", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [False, True, False, True]


class TestFilterCriteriaNotBetweenBlanks:
    """Tests for 'not_between_blanks' operator."""

    def test_not_between_blanks_includes_nulls(self) -> None:
        """NOT BETWEEN + BLANKS includes NaN/null values."""
        df = pd.DataFrame({"gain_pct": [5.0, None, float("nan")]})
        criteria = FilterCriteria(
            column="gain_pct", operator="not_between_blanks", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [False, True, True]

    def test_not_between_blanks_includes_outside_and_nulls(self) -> None:
        """NOT BETWEEN + BLANKS includes values outside range AND nulls."""
        df = pd.DataFrame({"gain_pct": [-5.0, 5.0, 15.0, None]})
        criteria = FilterCriteria(
            column="gain_pct", operator="not_between_blanks", min_val=0, max_val=10
        )
        mask = criteria.apply(df)
        assert mask.tolist() == [True, False, True, True]

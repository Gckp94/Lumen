"""Binning engine for assigning DataFrame rows to bins."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.core.models import BinDefinition, BinMetrics


class BinningEngine:
    """Assign DataFrame rows to bins and calculate per-bin metrics."""

    UNCATEGORIZED = "Uncategorized"

    def assign_bins(
        self,
        df: pd.DataFrame,
        column: str,
        bin_definitions: list[BinDefinition],
    ) -> pd.Series:
        """Assign each row to a bin based on column value.

        Args:
            df: Source DataFrame
            column: Column name to bin on
            bin_definitions: List of bin definitions (first match wins)

        Returns:
            Series with bin labels for each row
        """
        if df.empty or not bin_definitions:
            return pd.Series(dtype=str)

        values = df[column]
        result = pd.Series([self.UNCATEGORIZED] * len(df), index=df.index)

        # Process bins in reverse order so first definition wins
        for bin_def in reversed(bin_definitions):
            label = bin_def.label or self._generate_label(bin_def)
            mask = self._create_bin_mask(values, bin_def)
            result.loc[mask] = label

        return result

    def _create_bin_mask(
        self,
        values: pd.Series,
        bin_def: BinDefinition,
    ) -> pd.Series:
        """Create boolean mask for rows matching bin definition."""
        op = bin_def.operator

        if op == "nulls":
            return pd.isna(values)
        elif op == "<":
            return values < bin_def.value1
        elif op == ">":
            return values > bin_def.value1
        elif op == "range":
            return (values >= bin_def.value1) & (values <= bin_def.value2)
        else:
            return pd.Series([False] * len(values), index=values.index)

    def _format_number(self, value: float | None) -> str:
        """Format a number with K/M/B abbreviations for readability.

        Args:
            value: Number to format.

        Returns:
            Formatted string with appropriate suffix.
        """
        if value is None:
            return "N/A"

        abs_value = abs(value)
        sign = "-" if value < 0 else ""

        if abs_value >= 1_000_000_000:
            formatted = abs_value / 1_000_000_000
            suffix = "B"
        elif abs_value >= 1_000_000:
            formatted = abs_value / 1_000_000
            suffix = "M"
        elif abs_value >= 1_000:
            formatted = abs_value / 1_000
            suffix = "K"
        else:
            # Small numbers: show as-is
            if abs_value == int(abs_value):
                return f"{sign}{int(abs_value)}"
            return f"{sign}{abs_value:.1f}"

        # Format with suffix, removing unnecessary decimals
        rounded = round(formatted, 1)
        if rounded == int(rounded):
            return f"{sign}{int(rounded)}{suffix}"
        return f"{sign}{rounded:.1f}{suffix}"

    def _generate_label(self, bin_def: BinDefinition) -> str:
        """Generate auto-label from bin definition."""
        op = bin_def.operator

        if op == "nulls":
            return "Nulls"
        elif op == "<":
            return f"< {self._format_number(bin_def.value1)}"
        elif op == ">":
            return f"> {self._format_number(bin_def.value1)}"
        elif op == "range":
            return f"{self._format_number(bin_def.value1)} - {self._format_number(bin_def.value2)}"
        return "Unknown"

    def calculate_bin_metrics(
        self,
        df: pd.DataFrame,
        bin_labels: pd.Series,
        metric_column: str,
    ) -> dict[str, BinMetrics]:
        """Calculate metrics for each bin.

        Args:
            df: Source DataFrame
            bin_labels: Series with bin label for each row
            metric_column: Column to calculate metrics on (gain_pct or adjusted_gain_pct)

        Returns:
            Dict mapping bin label to BinMetrics dataclass
        """
        from src.core.models import BinMetrics

        if df.empty or bin_labels.empty:
            return {}

        results: dict[str, BinMetrics] = {}
        unique_labels = bin_labels.unique()

        for label in unique_labels:
            mask = bin_labels == label
            bin_data = df.loc[mask, metric_column]

            count = len(bin_data)
            if count == 0:
                results[label] = BinMetrics(
                    label=label,
                    count=0,
                    average=None,
                    median=None,
                    win_rate=None,
                    total_gain=0.0,
                )
                continue

            # Calculate metrics
            valid_data = bin_data.dropna()
            average = valid_data.mean() if len(valid_data) > 0 else None
            median = valid_data.median() if len(valid_data) > 0 else None

            # Win rate: percentage of rows where metric > 0
            wins = (valid_data > 0).sum() if len(valid_data) > 0 else 0
            win_rate = (wins / len(valid_data) * 100) if len(valid_data) > 0 else None

            # Total gain: sum of all gains in bin
            total_gain = float(valid_data.sum()) if len(valid_data) > 0 else 0.0

            results[label] = BinMetrics(
                label=label,
                count=count,
                average=average,
                median=median,
                win_rate=win_rate,
                total_gain=total_gain,
            )

        return results

    def get_percentile_splits(
        self,
        data: pd.Series,
        num_splits: int,
    ) -> list[float]:
        """Calculate percentile breakpoints for auto-split binning.

        Args:
            data: Series of values to calculate percentiles from.
            num_splits: Number of bins to create (4=quartile, 5=quintile, 10=decile).

        Returns:
            List of breakpoint values. Length is num_splits - 1.
            Empty list if data is empty or all NaN.
        """
        import numpy as np

        # Remove NaN values
        clean_data = data.dropna()

        if len(clean_data) == 0:
            return []

        # Calculate percentile positions (e.g., for 4 splits: 25, 50, 75)
        percentile_positions = [
            (i * 100) / num_splits for i in range(1, num_splits)
        ]

        breakpoints = np.percentile(clean_data, percentile_positions).tolist()

        return breakpoints

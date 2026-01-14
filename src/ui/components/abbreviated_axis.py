"""Custom PyQtGraph axis with abbreviated tick labels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyqtgraph as pg  # type: ignore[import-untyped]

from src.ui.utils.number_format import format_number_abbreviated

if TYPE_CHECKING:
    from collections.abc import Sequence


class AbbreviatedAxisItem(pg.AxisItem):
    """PyQtGraph axis that displays tick values with K/M/B abbreviations.

    Replaces scientific notation (1e+09) with human-readable suffixes:
    - 1,000 -> "1K"
    - 1,000,000 -> "1M"
    - 1,000,000,000 -> "1B"
    """

    def tickStrings(
        self, values: Sequence[float], scale: float, spacing: float
    ) -> list[str]:
        """Generate tick label strings with abbreviated formatting.

        Args:
            values: Numeric tick values to format.
            scale: Scale factor (unused, required by PyQtGraph).
            spacing: Tick spacing (unused, required by PyQtGraph).

        Returns:
            List of formatted tick label strings.
        """
        return [format_number_abbreviated(v) for v in values]

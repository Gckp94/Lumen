"""Horizontal bar chart showing feature impact scores."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyqtgraph as pg
from PyQt6.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from src.core.feature_analyzer import FeatureAnalyzerResults


class FeatureImpactChart(QWidget):
    """Bar chart displaying feature impact scores."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot = pg.PlotWidget()
        self._plot.setBackground("#1e1e1e")
        self._plot.setLabel("bottom", "Impact Score")
        self._plot.setLabel("left", "Feature")
        self._plot.setXRange(0, 100)

        layout.addWidget(self._plot)

    def update_data(self, results: FeatureAnalyzerResults) -> None:
        """Update chart with analysis results."""
        self._plot.clear()

        if not results.features:
            return

        # Prepare data
        features = results.features[::-1]  # Reverse for bottom-to-top
        y_positions = list(range(len(features)))
        scores = [f.impact_score for f in features]
        names = [f.feature_name for f in features]

        # Create bar chart
        bar = pg.BarGraphItem(
            x0=0,
            y=y_positions,
            height=0.6,
            width=scores,
            brush="#4a9eff",
        )
        self._plot.addItem(bar)

        # Set y-axis labels
        y_axis = self._plot.getAxis("left")
        y_axis.setTicks([list(zip(y_positions, names))])

"""ComparisonGridHorizontal widget with 4 side-by-side section cards.

Displays 23 metrics in 4 horizontally-arranged section cards, each using
the MetricsSectionCard component. This layout better utilizes horizontal
screen space compared to the vertical ComparisonGrid.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QWidget,
)

from src.ui.components.comparison_grid import METRIC_CONFIG, SECTIONS
from src.ui.components.metrics_section_card import MetricsSectionCard
from src.ui.constants import Colors, Spacing

if TYPE_CHECKING:
    from src.core.models import TradingMetrics

logger = logging.getLogger(__name__)


class ComparisonGridHorizontal(QFrame):
    """Horizontal grid displaying 23 metrics in 4 side-by-side section cards.

    Sections:
    - Core Statistics (14 metrics)
    - Streak & Loss (3 metrics)
    - Flat Stake (4 metrics)
    - Compounded Kelly (4 metrics)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize ComparisonGridHorizontal.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._section_cards: dict[str, MetricsSectionCard] = {}
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the horizontal layout with 4 section cards."""
        self.setObjectName("comparisonGridHorizontal")

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Set minimum height based on tallest section
        # Core Statistics: 14 rows × 26px + ~56px headers ≈ 420px
        self.setMinimumHeight(350)

        # Horizontal scroll area for sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        self._cards_layout = QHBoxLayout(scroll_content)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(Spacing.SM)

        # Proportional stretch factors per section:
        # - Core Statistics: largest (14 metrics) - gets most space
        # - Streak & Loss: smallest (3 metrics) - 60% relative
        # - Flat Stake: medium (4 metrics) - 80% relative
        # - Compounded Kelly: medium (4 metrics) - 80% relative
        section_stretch = {
            "core_statistics": 5,   # Largest - takes remaining space
            "streak_loss": 3,       # 60% relative
            "flat_stake": 4,        # 80% relative
            "kelly": 4,             # 80% relative
        }

        # Minimum content width: name(130) + values(120×3) + tight padding ≈ 500px
        MIN_CARD_WIDTH = 500

        # Create section cards
        for section_id, title, metrics in SECTIONS:
            # Convert metric field names to (field_name, display_label) tuples
            metric_tuples = []
            for field_name in metrics:
                config = METRIC_CONFIG.get(field_name)
                display_label = config[0] if config else field_name
                metric_tuples.append((field_name, display_label))

            # Create the section card
            card = MetricsSectionCard(title, metric_tuples)
            card.setMinimumWidth(MIN_CARD_WIDTH)

            # Apply proportional stretch factor
            stretch = section_stretch.get(section_id, 1)
            self._cards_layout.addWidget(card, stretch=stretch)

            self._section_cards[section_id] = card

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

    def _apply_style(self) -> None:
        """Apply styling to the grid."""
        self.setStyleSheet(f"""
            QFrame#comparisonGridHorizontal {{
                background-color: {Colors.BG_SURFACE};
            }}
            QScrollArea {{
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
        """)

    def set_values(
        self,
        baseline: TradingMetrics,
        filtered: TradingMetrics | None = None,
    ) -> None:
        """Update all section cards with baseline and filtered values.

        Args:
            baseline: Baseline metrics (full dataset).
            filtered: Filtered metrics, or None if no filter applied.
        """
        for section_id, _, metrics in SECTIONS:
            card = self._section_cards.get(section_id)
            if card is None:
                continue

            # Convert TradingMetrics to dict for this section
            baseline_dict: dict[str, float | int | str | None] = {}
            filtered_dict: dict[str, float | int | str | None] | None = (
                {} if filtered else None
            )

            for field_name in metrics:
                baseline_dict[field_name] = getattr(baseline, field_name, None)
                if filtered_dict is not None:
                    filtered_dict[field_name] = getattr(filtered, field_name, None)

            card.set_values(baseline_dict, filtered_dict)

        logger.debug("ComparisonGridHorizontal updated with %d sections", len(SECTIONS))

    def clear(self) -> None:
        """Clear all section cards, showing dashes."""
        for card in self._section_cards.values():
            card.clear()

    def toggle_section(self, section_id: str) -> None:
        """Toggle a section's expanded state (no-op for horizontal layout).

        In the horizontal layout, sections are always visible as cards.
        This method is provided for API compatibility with ComparisonGrid.

        Args:
            section_id: ID of the section to toggle.
        """
        # No-op: horizontal layout doesn't support collapsing
        pass

    def get_section_state(self, section_id: str) -> bool:
        """Get expansion state of a section (always True for horizontal layout).

        In the horizontal layout, sections are always visible.
        This method is provided for API compatibility with ComparisonGrid.

        Args:
            section_id: ID of the section.

        Returns:
            Always True since sections cannot be collapsed.
        """
        return True

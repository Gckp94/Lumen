# src/ui/components/contribution_panel.py
"""Portfolio contribution panel for metrics display.

Shows Sharpe, VaR, and CVaR contribution in a triple-value layout.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.constants import Colors, Fonts, Spacing


class ContributionRow(QFrame):
    """Single contribution metric row with baseline/combined/improvement."""

    def __init__(
        self,
        title: str,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title_text = title
        self._setup_ui()
        if tooltip:
            self.setToolTip(tooltip)

    def _setup_ui(self) -> None:
        self.setObjectName("contributionRow")
        self.setStyleSheet(f"""
            QFrame#contributionRow {{
                background-color: {Colors.BG_ELEVATED};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Title
        title = QLabel(self._title_text)
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: '{Fonts.UI}';
                font-size: 11px;
                padding-bottom: 4px;
                border-bottom: 1px solid {Colors.BG_BORDER};
            }}
        """)
        layout.addWidget(title)

        # Values row
        values_layout = QHBoxLayout()
        values_layout.setSpacing(Spacing.SM)

        # Baseline
        baseline_container = QVBoxLayout()
        baseline_label = QLabel("BASELINE")
        baseline_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        baseline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        baseline_container.addWidget(baseline_label)

        self._baseline_value = QLabel("—")
        self._baseline_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                font-size: 14px;
                font-weight: 600;
            }}
        """)
        self._baseline_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        baseline_container.addWidget(self._baseline_value)
        values_layout.addLayout(baseline_container)

        # Combined
        combined_container = QVBoxLayout()
        combined_label = QLabel("COMBINED")
        combined_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        combined_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        combined_container.addWidget(combined_label)

        self._combined_value = QLabel("—")
        self._combined_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.DATA}';
                font-size: 14px;
                font-weight: 600;
            }}
        """)
        self._combined_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        combined_container.addWidget(self._combined_value)
        values_layout.addLayout(combined_container)

        # Improvement
        improvement_container = QVBoxLayout()
        improvement_label = QLabel("CHANGE")
        improvement_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED};
                font-family: '{Fonts.UI}';
                font-size: 9px;
            }}
        """)
        improvement_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        improvement_container.addWidget(improvement_label)

        self._improvement_value = QLabel("—")
        self._improvement_value.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SIGNAL_CYAN};
                font-family: '{Fonts.DATA}';
                font-size: 16px;
                font-weight: 600;
            }}
        """)
        self._improvement_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        improvement_container.addWidget(self._improvement_value)
        values_layout.addLayout(improvement_container)

        layout.addLayout(values_layout)

    def set_values(
        self,
        baseline: float | None,
        combined: float | None,
        improvement: float | None,
        format_str: str = "{:.2f}",
        higher_is_better: bool = True,
    ) -> None:
        """Update all three values with formatting."""
        if baseline is not None:
            self._baseline_value.setText(format_str.format(baseline))
        else:
            self._baseline_value.setText("—")

        if combined is not None:
            self._combined_value.setText(format_str.format(combined))
        else:
            self._combined_value.setText("—")

        if improvement is not None:
            prefix = "+" if improvement > 0 else ""
            self._improvement_value.setText(f"{prefix}{format_str.format(improvement)}")

            is_better = (improvement > 0) == higher_is_better
            color = Colors.SIGNAL_CYAN if is_better else Colors.SIGNAL_CORAL
            self._improvement_value.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-family: '{Fonts.DATA}';
                    font-size: 16px;
                    font-weight: 600;
                }}
            """)
        else:
            self._improvement_value.setText("—")


class ContributionPanel(QFrame):
    """Panel displaying portfolio contribution metrics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("contributionPanel")
        self.setStyleSheet(f"""
            QFrame#contributionPanel {{
                background-color: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.SM)

        # Title
        title = QLabel("PORTFOLIO CONTRIBUTION")
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: '{Fonts.UI}';
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
        """)
        layout.addWidget(title)

        # Contribution rows
        self._sharpe_row = ContributionRow(
            "Marginal Sharpe Contribution",
            "Change in Sharpe ratio from adding strategy"
        )
        layout.addWidget(self._sharpe_row)

        self._var_row = ContributionRow(
            "VaR Contribution (95%)",
            "Change in Value at Risk"
        )
        layout.addWidget(self._var_row)

        self._cvar_row = ContributionRow(
            "CVaR Contribution (95%)",
            "Change in Expected Shortfall"
        )
        layout.addWidget(self._cvar_row)

        layout.addStretch()

    def update_metrics(
        self,
        sharpe: dict[str, float | None] | None,
        var: dict[str, float | None] | None,
        cvar: dict[str, float | None] | None,
    ) -> None:
        """Update all contribution metrics."""
        if sharpe:
            self._sharpe_row.set_values(
                sharpe.get("sharpe_baseline"),
                sharpe.get("sharpe_combined"),
                sharpe.get("sharpe_improvement"),
            )
        else:
            self._sharpe_row.set_values(None, None, None)

        if var:
            self._var_row.set_values(
                var.get("var_baseline"),
                var.get("var_combined"),
                var.get("var_marginal"),
                format_str="{:.2f}%",
                higher_is_better=True,  # Less negative VaR is better
            )
        else:
            self._var_row.set_values(None, None, None)

        if cvar:
            self._cvar_row.set_values(
                cvar.get("cvar_baseline"),
                cvar.get("cvar_combined"),
                cvar.get("cvar_marginal"),
                format_str="{:.2f}%",
                higher_is_better=True,  # Less negative CVaR is better
            )
        else:
            self._cvar_row.set_values(None, None, None)

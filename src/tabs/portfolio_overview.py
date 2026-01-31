# src/tabs/portfolio_overview.py
"""Portfolio Overview tab widget.

Integrates toolbar, strategy table, and portfolio charts for managing
and visualizing multi-strategy portfolio performance.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.core.app_state import AppState
from src.core.portfolio_calculator import PortfolioCalculator
from src.core.portfolio_config_manager import PortfolioConfigManager
from src.core.portfolio_models import PortfolioColumnMapping, StrategyConfig
from src.ui.components.no_scroll_widgets import NoScrollDoubleSpinBox
from src.ui.components.portfolio_charts import PortfolioChartsWidget
from src.ui.components.strategy_table import StrategyTableWidget
from src.ui.constants import Colors, Fonts, FontSizes, Spacing
from src.ui.dialogs import ImportStrategyDialog

logger = logging.getLogger(__name__)

# Debounce delay for recalculation (ms)
RECALC_DEBOUNCE_MS = 300


class PortfolioOverviewTab(QWidget):
    """Main tab widget for Portfolio Overview feature.

    Provides UI for adding strategies, configuring position sizing parameters,
    and visualizing combined portfolio equity curves and drawdowns.

    Attributes:
        _app_state: Application state for shared data access.
        _calculator: Portfolio calculator for equity curve computation.
        _strategy_data: Dictionary mapping strategy names to loaded DataFrames.
        _recalc_timer: Timer for debounced recalculation.
    """

    # Signal emitted when portfolio data changes (for Portfolio Breakdown tab)
    portfolio_data_changed = pyqtSignal(dict)  # {"baseline": df, "combined": df}

    def __init__(
        self,
        app_state: AppState,
        parent: Optional[QWidget] = None,
        config_manager: Optional[PortfolioConfigManager] = None,
    ) -> None:
        """Initialize the Portfolio Overview tab.

        Args:
            app_state: Application state instance.
            parent: Optional parent widget.
            config_manager: Optional config manager for dependency injection.
        """
        super().__init__(parent)
        self._app_state = app_state
        self._calculator = PortfolioCalculator()
        self._config_manager = config_manager or PortfolioConfigManager()
        self._strategy_data: dict[str, pd.DataFrame] = {}
        self._recalc_timer = QTimer(self)
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.timeout.connect(self._recalculate)

        self._setup_ui()
        self._connect_signals()
        self._load_saved_config()

    def _setup_ui(self) -> None:
        """Set up the tab layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main content splitter (table above, charts below)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BG_BORDER};
            }}
            QSplitter::handle:hover {{
                background-color: {Colors.SIGNAL_CYAN};
            }}
        """)

        # Strategy table
        self._strategy_table = StrategyTableWidget()
        self._strategy_table.setMinimumHeight(150)
        splitter.addWidget(self._strategy_table)

        # Charts
        self._charts = PortfolioChartsWidget()
        self._charts.setMinimumHeight(300)
        splitter.addWidget(self._charts)

        # Set initial splitter sizes (40% table, 60% charts)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter, stretch=1)

    def _create_toolbar(self) -> QWidget:
        """Create the toolbar widget with add button and account start input.

        Returns:
            Toolbar widget.
        """
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(Spacing.MD)

        # Add Strategy button
        self._add_strategy_btn = QPushButton("+ Add Strategy")
        self._add_strategy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SIGNAL_CYAN};
                color: {Colors.BG_BASE};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
                font-weight: 600;
                padding: {Spacing.SM}px {Spacing.MD}px;
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {Colors.SIGNAL_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self._add_strategy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self._add_strategy_btn)

        toolbar_layout.addStretch()

        # Account Start label and spinner
        account_label = QLabel("Account Start:")
        account_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-family: {Fonts.UI};
                font-size: {FontSizes.BODY}px;
            }}
        """)
        toolbar_layout.addWidget(account_label)

        self._account_start_spin = NoScrollDoubleSpinBox()
        self._account_start_spin.setRange(1_000, 100_000_000)
        self._account_start_spin.setValue(100_000)
        self._account_start_spin.setDecimals(0)
        self._account_start_spin.setPrefix("$")
        self._account_start_spin.setSingleStep(10_000)
        self._account_start_spin.setMinimumWidth(120)
        self._account_start_spin.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-family: {Fonts.DATA};
                font-size: {FontSizes.BODY}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                border: 1px solid {Colors.BG_BORDER};
                border-radius: 4px;
            }}
            QDoubleSpinBox:focus {{
                border-color: {Colors.SIGNAL_CYAN};
            }}
        """)
        toolbar_layout.addWidget(self._account_start_spin)

        return toolbar

    def _connect_signals(self) -> None:
        """Connect widget signals to handlers."""
        self._add_strategy_btn.clicked.connect(self._on_add_strategy)
        self._strategy_table.strategy_changed.connect(self._schedule_recalculation)
        self._account_start_spin.valueChanged.connect(self._schedule_recalculation)

    def _load_saved_config(self) -> None:
        """Load saved strategies on startup."""
        strategies, account_start = self._config_manager.load()
        self._account_start_spin.setValue(account_start)

        valid_strategies = []
        for config in strategies:
            file_path = Path(config.file_path)

            # Skip strategies with missing files
            if not file_path.exists():
                logger.warning(
                    f"Skipping strategy '{config.name}': file not found at {config.file_path}"
                )
                continue

            # Try to reload the data
            try:
                if config.file_path.endswith(".csv"):
                    df = pd.read_csv(config.file_path)
                else:
                    sheet = config.sheet_name if config.sheet_name else 0
                    df = pd.read_excel(config.file_path, sheet_name=sheet)

                self._strategy_data[config.name] = df
                self._strategy_table.add_strategy(config)
                valid_strategies.append(config)
                logger.info(f"Loaded strategy '{config.name}' from {config.file_path}")
            except Exception as e:
                logger.warning(f"Could not load file for {config.name}: {e}")
                # Don't add strategy if file can't be loaded

        # Update config to remove invalid entries
        if len(valid_strategies) < len(strategies):
            self._config_manager.save(valid_strategies, account_start)
            logger.info(f"Cleaned up config: {len(strategies) - len(valid_strategies)} invalid entries removed")

        if valid_strategies:
            self._schedule_recalculation()

    def _on_add_strategy(self) -> None:
        """Handle Add Strategy button click."""
        dialog = ImportStrategyDialog(self)

        if dialog.exec():
            # Get data from dialog
            file_path = dialog.get_file_path()
            strategy_name = dialog.get_strategy_name()
            column_mapping = dialog.get_column_mapping()
            df = dialog.get_dataframe()

            logger.debug(
                f"Import dialog result: file_path={file_path}, "
                f"strategy_name={strategy_name}, df_shape={df.shape if df is not None else None}"
            )

            if df is not None and file_path:
                # Create strategy config
                config = StrategyConfig(
                    name=strategy_name,
                    file_path=file_path,
                    column_mapping=column_mapping,
                    sheet_name=dialog.get_selected_sheet(),
                )

                # Store the data
                self._strategy_data[strategy_name] = df

                # Add to table
                self._strategy_table.add_strategy(config)

                # Trigger recalculation
                self._schedule_recalculation()

                logger.info(f"Added strategy: {strategy_name} from {file_path}")
            else:
                logger.warning(
                    f"Import cancelled or failed: df={df is not None}, file_path={file_path}"
                )

    def _schedule_recalculation(self) -> None:
        """Schedule a recalculation with debouncing."""
        self._recalc_timer.start(RECALC_DEBOUNCE_MS)

    def _recalculate(self) -> None:
        """Recalculate equity curves for all strategies.

        Calculates:
        1. Individual equity curves for each strategy
        2. Baseline aggregate (strategies marked as baseline)
        3. Combined aggregate (strategies marked as candidate)
        """
        # Guard against widget being deleted during test cleanup
        try:
            strategies = self._strategy_table.get_strategies()
        except RuntimeError:
            # Widget has been deleted, skip recalculation
            return
        if not strategies:
            self._charts.set_data({})
            return

        # Update calculator starting capital
        self._calculator.starting_capital = self._account_start_spin.value()

        chart_data: dict[str, pd.DataFrame] = {}

        # Calculate individual strategy curves
        baseline_strategies: list[tuple[pd.DataFrame, StrategyConfig]] = []
        candidate_strategies: list[tuple[pd.DataFrame, StrategyConfig]] = []

        for config in strategies:
            df = self._strategy_data.get(config.name)
            if df is None:
                continue

            # Calculate individual equity curve
            try:
                equity_df = self._calculator.calculate_single_strategy(df, config)
                if not equity_df.empty:
                    chart_data[config.name] = equity_df

                    # Collect for aggregates
                    if config.is_baseline:
                        baseline_strategies.append((df, config))
                    if config.is_candidate:
                        candidate_strategies.append((df, config))

            except Exception as e:
                logger.error(f"Failed to calculate equity for {config.name}: {e}")

        # Calculate baseline aggregate
        if baseline_strategies:
            try:
                baseline_df = self._calculator.calculate_portfolio(baseline_strategies)
                if not baseline_df.empty:
                    chart_data["baseline"] = baseline_df
            except Exception as e:
                logger.error(f"Failed to calculate baseline aggregate: {e}")

        # Calculate combined aggregate
        if candidate_strategies:
            try:
                combined_df = self._calculator.calculate_portfolio(candidate_strategies)
                if not combined_df.empty:
                    chart_data["combined"] = combined_df
            except Exception as e:
                logger.error(f"Failed to calculate combined aggregate: {e}")

        # Update charts (guard against widget deletion during test cleanup)
        try:
            self._charts.set_data(chart_data)
            logger.debug(f"Recalculated {len(chart_data)} equity curves")

            # Emit signal for other tabs (Portfolio Breakdown)
            self.portfolio_data_changed.emit(chart_data)

            # Save configuration
            self._config_manager.save(strategies, self._account_start_spin.value())
        except RuntimeError:
            # Widget has been deleted, skip updates
            pass

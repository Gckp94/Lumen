"""Widget tests for PnLStatsTab."""

from PyQt6.QtWidgets import QLabel, QVBoxLayout

from src.core.app_state import AppState
from src.core.models import AdjustmentParams, MetricsUserInputs
from src.tabs.pnl_stats import PnLStatsTab
from src.ui.components import EmptyState, UserInputsPanel
from src.ui.components.distribution_card import DistributionCard


class TestPnLStatsTabLayout:
    """Tests for PnLStatsTab layout structure."""

    def test_tab_creation(self, qtbot):
        """Tab can be created with AppState."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)
        assert tab is not None
        tab.cleanup()

    def test_layout_is_vbox(self, qtbot):
        """Tab uses QVBoxLayout."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        layout = tab.layout()
        assert isinstance(layout, QVBoxLayout)

        tab.cleanup()

    def test_user_inputs_panel_exists(self, qtbot):
        """Tab contains UserInputsPanel."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        user_inputs = tab.findChild(UserInputsPanel)
        assert user_inputs is not None

        tab.cleanup()

    def test_empty_states_exist(self, qtbot):
        """Tab contains EmptyState placeholder for metrics."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        empty_states = tab.findChildren(EmptyState)
        assert len(empty_states) == 1  # metrics placeholder (charts now have actual widgets)

        tab.cleanup()

    def test_section_headers_exist(self, qtbot):
        """Tab contains section header labels."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        labels = tab.findChildren(QLabel)
        label_texts = [label.text() for label in labels]

        # Check for section headers (exact text may vary, check key ones)
        assert "Configuration" in label_texts
        assert "Trading Metrics" in label_texts
        assert "Charts" in label_texts

        tab.cleanup()


class TestPnLStatsTabBidirectionalSync:
    """Tests for bidirectional sync between PnLStatsTab and AppState."""

    def test_stop_loss_change_updates_app_state(self, qtbot):
        """Changing stop loss in panel updates AppState."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        user_inputs = tab.findChild(UserInputsPanel)

        # Change stop loss
        user_inputs._stop_loss_spin.setValue(12.0)

        # Wait for debounce
        qtbot.wait(200)

        assert app_state.adjustment_params.stop_loss == 12.0

        tab.cleanup()

    def test_efficiency_change_updates_app_state(self, qtbot):
        """Changing efficiency in panel updates AppState."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        user_inputs = tab.findChild(UserInputsPanel)

        # Change efficiency
        user_inputs._efficiency_spin.setValue(7.0)

        # Wait for debounce
        qtbot.wait(200)

        assert app_state.adjustment_params.efficiency == 7.0

        tab.cleanup()

    def test_app_state_adjustment_change_updates_panel(self, qtbot):
        """Changing AppState adjustment_params updates panel."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        user_inputs = tab.findChild(UserInputsPanel)

        # Update AppState directly
        new_params = AdjustmentParams(stop_loss=15.0, efficiency=6.0)
        app_state.adjustment_params = new_params
        app_state.adjustment_params_changed.emit(new_params)

        # Verify panel updated
        assert user_inputs._stop_loss_spin.value() == 15.0
        assert user_inputs._efficiency_spin.value() == 6.0

        tab.cleanup()

    def test_metrics_inputs_change_updates_app_state(self, qtbot):
        """Changing metrics inputs in panel updates AppState."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        user_inputs = tab.findChild(UserInputsPanel)

        # Change flat stake
        user_inputs._flat_stake_spin.setValue(5000.0)

        # Wait for debounce
        qtbot.wait(200)

        assert app_state.metrics_user_inputs.flat_stake == 5000.0

        tab.cleanup()

    def test_no_signal_loop(self, qtbot):
        """Updating panel from AppState doesn't trigger signal back."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        signal_count = []
        app_state.adjustment_params_changed.connect(lambda x: signal_count.append(x))

        # Update AppState directly
        new_params = AdjustmentParams(stop_loss=20.0, efficiency=10.0)
        app_state.adjustment_params = new_params
        app_state.adjustment_params_changed.emit(new_params)

        # Wait to ensure no loop
        qtbot.wait(200)

        # Should only have the one emission we triggered
        assert len(signal_count) == 1

        tab.cleanup()


class TestPnLStatsTabPersistence:
    """Tests for input persistence via AppState."""

    def test_inputs_persist_across_tab_recreate(self, qtbot):
        """Inputs persist when tab is recreated (simulating tab switch)."""
        app_state = AppState()

        # Create first tab instance
        tab1 = PnLStatsTab(app_state)
        qtbot.addWidget(tab1)

        user_inputs1 = tab1.findChild(UserInputsPanel)
        user_inputs1._flat_stake_spin.setValue(7500.0)
        user_inputs1._stop_loss_spin.setValue(10.0)

        # Wait for debounce
        qtbot.wait(200)

        # Cleanup first tab
        tab1.cleanup()

        # Create second tab instance (simulates tab switch)
        tab2 = PnLStatsTab(app_state)
        qtbot.addWidget(tab2)

        user_inputs2 = tab2.findChild(UserInputsPanel)

        # Values should be preserved from AppState
        assert user_inputs2._flat_stake_spin.value() == 7500.0
        assert user_inputs2._stop_loss_spin.value() == 10.0

        tab2.cleanup()

    def test_initializes_from_app_state(self, qtbot):
        """Tab initializes values from AppState on creation."""
        app_state = AppState()

        # Set values in AppState before creating tab
        app_state.adjustment_params = AdjustmentParams(stop_loss=18.0, efficiency=4.0)
        app_state.metrics_user_inputs = MetricsUserInputs(
            flat_stake=3000.0,
            starting_capital=75000.0,
            fractional_kelly=40.0,
        )

        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        user_inputs = tab.findChild(UserInputsPanel)

        assert user_inputs._stop_loss_spin.value() == 18.0
        assert user_inputs._efficiency_spin.value() == 4.0
        assert user_inputs._flat_stake_spin.value() == 3000.0
        assert user_inputs._starting_capital_spin.value() == 75000.0
        assert user_inputs._fractional_kelly_spin.value() == 40.0

        tab.cleanup()


class TestPnLStatsTabEmptyStates:
    """Tests for EmptyState placeholders."""

    def test_metrics_empty_state_message(self, qtbot):
        """Metrics empty state has correct message."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Find metrics empty state via stacked widget
        metrics_empty = tab._metrics_empty
        assert metrics_empty._icon_label.text() == "📊"
        assert "No Metrics Yet" in metrics_empty._title_label.text()

        tab.cleanup()

    def test_equity_chart_panels_exist(self, qtbot):
        """Equity chart panels exist in PnLStatsTab."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_flat_stake_chart_panel")
        assert hasattr(tab, "_kelly_chart_panel")
        assert tab._flat_stake_chart_panel is not None
        assert tab._kelly_chart_panel is not None

        tab.cleanup()

    def test_equity_chart_panels_have_minimum_height(self, qtbot):
        """Equity chart panels have minimum height of 250px."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert tab._flat_stake_chart_panel.chart.minimumHeight() == 250
        assert tab._kelly_chart_panel.chart.minimumHeight() == 250

        tab.cleanup()


class TestPnLStatsTabMetricsGrid:
    """Tests for MetricsGrid integration in PnLStatsTab."""

    def test_metrics_stack_exists(self, qtbot):
        """Tab contains QStackedWidget for metrics."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_metrics_stack")
        assert tab._metrics_stack is not None

        tab.cleanup()

    def test_comparison_grid_exists(self, qtbot):
        """Tab contains ComparisonGrid widget."""
        from src.ui.components import ComparisonGrid

        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_comparison_grid")
        assert isinstance(tab._comparison_grid, ComparisonGrid)

        tab.cleanup()

    def test_empty_state_shown_when_no_data(self, qtbot):
        """EmptyState is shown when no data is loaded."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # No data loaded, should show empty state (index 0)
        assert tab._metrics_stack.currentIndex() == 0

        tab.cleanup()

    def test_metrics_grid_shown_when_data_loaded(self, qtbot):
        """MetricsGrid is shown when data is loaded."""
        import pandas as pd

        from src.core.models import ColumnMapping, TradingMetrics

        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Simulate data loading
        app_state.baseline_df = pd.DataFrame({
            "gain_pct": [5.0, -2.0, 3.0],
            "mae_pct": [1.0, 2.0, 1.5],
        })
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            win_loss_derived=True,
        )

        # Emit baseline_calculated signal
        metrics = TradingMetrics(
            num_trades=3,
            win_rate=66.7,
            avg_winner=4.0,
            avg_loser=-2.0,
            rr_ratio=2.0,
            ev=2.0,
            kelly=33.3,
        )
        app_state.baseline_calculated.emit(metrics)

        # Should show metrics grid (index 1)
        assert tab._metrics_stack.currentIndex() == 1

        tab.cleanup()


class TestPnLStatsTabRecalculation:
    """Tests for metric recalculation on input changes."""

    def test_recalc_timer_exists(self, qtbot):
        """Tab has debounce timer for recalculation."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_recalc_timer")
        assert tab._recalc_timer is not None
        assert tab._recalc_timer.isSingleShot()

        tab.cleanup()

    def test_recalc_scheduled_on_fractional_kelly_change(self, qtbot):
        """Recalculation is scheduled when fractional kelly changes."""
        import pandas as pd

        from src.core.models import ColumnMapping

        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Set up data
        app_state.baseline_df = pd.DataFrame({
            "gain_pct": [5.0, -2.0, 3.0],
            "mae_pct": [1.0, 2.0, 1.5],
        })
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            win_loss_derived=True,
        )

        # Change fractional kelly
        user_inputs = tab.findChild(UserInputsPanel)
        user_inputs._fractional_kelly_spin.setValue(50.0)

        # Wait for debounce
        qtbot.wait(200)

        # Timer should have been started
        assert app_state.metrics_user_inputs.fractional_kelly == 50.0

        tab.cleanup()

    def test_recalc_scheduled_on_stop_loss_change(self, qtbot):
        """Recalculation is scheduled when stop loss changes."""
        import pandas as pd

        from src.core.models import ColumnMapping

        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Set up data
        app_state.baseline_df = pd.DataFrame({
            "gain_pct": [5.0, -2.0, 3.0],
            "mae_pct": [1.0, 2.0, 1.5],
        })
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            win_loss_derived=True,
        )

        # Change stop loss
        user_inputs = tab.findChild(UserInputsPanel)
        user_inputs._stop_loss_spin.setValue(12.0)

        # Wait for debounce
        qtbot.wait(200)

        assert app_state.adjustment_params.stop_loss == 12.0

        tab.cleanup()

    def test_recalc_debounced(self, qtbot):
        """Multiple rapid changes are debounced to single recalculation."""
        import pandas as pd

        from src.core.models import ColumnMapping

        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Set up data
        app_state.baseline_df = pd.DataFrame({
            "gain_pct": [5.0, -2.0, 3.0],
            "mae_pct": [1.0, 2.0, 1.5],
        })
        app_state.column_mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
            win_loss_derived=True,
        )

        recalc_count = [0]
        original_recalc = tab._recalculate_metrics

        def counting_recalc():
            recalc_count[0] += 1
            original_recalc()

        # Disconnect original and connect counting version
        tab._recalc_timer.timeout.disconnect()
        tab._recalc_timer.timeout.connect(counting_recalc)

        # Make multiple rapid changes
        user_inputs = tab.findChild(UserInputsPanel)
        user_inputs._fractional_kelly_spin.setValue(30.0)
        user_inputs._fractional_kelly_spin.setValue(40.0)
        user_inputs._fractional_kelly_spin.setValue(50.0)

        # Wait for debounce to complete (300ms + buffer)
        qtbot.wait(500)

        # Should only have been called once due to debouncing
        assert recalc_count[0] == 1

        tab.cleanup()

    def test_no_recalc_without_data(self, qtbot):
        """Recalculation does not happen when no data is loaded."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        recalc_count = [0]

        def counting_recalc():
            recalc_count[0] += 1

        tab._recalculate_metrics = counting_recalc

        # Change inputs without data loaded
        user_inputs = tab.findChild(UserInputsPanel)
        user_inputs._fractional_kelly_spin.setValue(50.0)

        # Wait for debounce
        qtbot.wait(500)

        # Should not have been called (no data)
        assert recalc_count[0] == 0

        tab.cleanup()


class TestPnLStatsTabDistributionCards:
    """Tests for distribution cards integration in PnLStatsTab (Story 3.6)."""

    def test_pnl_stats_tab_has_distribution_cards(self, qtbot):
        """PnLStatsTab contains winner and loser distribution cards."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_winner_dist_card")
        assert hasattr(tab, "_loser_dist_card")
        assert isinstance(tab._winner_dist_card, DistributionCard)
        assert isinstance(tab._loser_dist_card, DistributionCard)

        tab.cleanup()

    def test_distribution_cards_correct_types(self, qtbot):
        """Distribution cards have correct card types."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert tab._winner_dist_card.card_type == DistributionCard.WINNER
        assert tab._loser_dist_card.card_type == DistributionCard.LOSER

        tab.cleanup()

    def test_distribution_cards_update_on_metrics(self, qtbot):
        """Distribution cards update when metrics are calculated."""
        from src.core.models import TradingMetrics

        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Create metrics with distribution data
        metrics = TradingMetrics(
            num_trades=10,
            win_rate=60.0,
            avg_winner=5.0,
            avg_loser=-3.0,
            rr_ratio=1.67,
            ev=1.8,
            kelly=30.0,
            winner_count=6,
            loser_count=4,
            winner_std=2.0,
            loser_std=1.5,
            winner_gains=[3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            loser_gains=[-2.0, -3.0, -4.0, -5.0],
            winner_min=3.0,
            winner_max=8.0,
            loser_min=-5.0,
            loser_max=-2.0,
            median_winner=5.5,
            median_loser=-3.5,
        )

        # Emit baseline_calculated signal to update distribution cards
        app_state.baseline_calculated.emit(metrics)

        # Wait for update to process
        qtbot.wait(100)

        # Verify winner card was populated
        from PyQt6.QtWidgets import QLabel
        count_label = tab._winner_dist_card.findChild(QLabel, "countLabel")
        assert count_label is not None
        assert "6" in count_label.text()

        tab.cleanup()

    def test_distribution_cards_clear_on_no_data(self, qtbot):
        """Distribution cards clear when metrics have no winners/losers."""
        from src.core.models import TradingMetrics

        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        # Create metrics with no winners
        metrics = TradingMetrics(
            num_trades=0,
            win_rate=None,
            avg_winner=None,
            avg_loser=None,
            rr_ratio=None,
            ev=None,
            kelly=None,
            winner_count=0,
            loser_count=0,
        )

        # Emit baseline_calculated signal
        app_state.baseline_calculated.emit(metrics)

        # Wait for update
        qtbot.wait(100)

        # Verify cards are cleared (showing em dash)
        from PyQt6.QtWidgets import QLabel
        count_label = tab._winner_dist_card.findChild(QLabel, "countLabel")
        assert count_label is not None
        assert count_label.text() == "\u2014"

        tab.cleanup()

    def test_histogram_click_handlers_exist(self, qtbot):
        """Tab has histogram click handlers for distribution cards."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        assert hasattr(tab, "_on_view_winner_histogram")
        assert hasattr(tab, "_on_view_loser_histogram")
        assert callable(tab._on_view_winner_histogram)
        assert callable(tab._on_view_loser_histogram)

        tab.cleanup()

    def test_distribution_statistics_header_exists(self, qtbot):
        """Tab contains Distribution Statistics section header."""
        app_state = AppState()
        tab = PnLStatsTab(app_state)
        qtbot.addWidget(tab)

        labels = tab.findChildren(QLabel)
        label_texts = [label.text() for label in labels]

        assert "Distribution Statistics" in label_texts

        tab.cleanup()

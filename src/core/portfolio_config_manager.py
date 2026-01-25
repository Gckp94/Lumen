# src/core/portfolio_config_manager.py
"""Persistence for portfolio configurations."""
import json
import logging
from pathlib import Path
from typing import Optional

from src.core.portfolio_models import StrategyConfig, PortfolioColumnMapping, PositionSizeType

logger = logging.getLogger(__name__)


class PortfolioConfigManager:
    """Manages saving and loading portfolio configurations."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / ".lumen" / "portfolio_config.json"
        self._config_path = Path(config_path)

    def save(self, strategies: list[StrategyConfig], account_start: float = 100_000):
        """Save strategies and account start to JSON file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "account_start": account_start,
            "strategies": [self._strategy_to_dict(s) for s in strategies],
        }

        with open(self._config_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved portfolio config to {self._config_path}")

    def load(self) -> tuple[list[StrategyConfig], float]:
        """Load strategies and account start from JSON file."""
        if not self._config_path.exists():
            return [], 100_000

        try:
            with open(self._config_path) as f:
                data = json.load(f)

            account_start = data.get("account_start", 100_000)
            strategies = [self._dict_to_strategy(s) for s in data.get("strategies", [])]

            logger.info(f"Loaded {len(strategies)} strategies from {self._config_path}")
            return strategies, account_start

        except Exception as e:
            logger.error(f"Failed to load portfolio config: {e}")
            return [], 100_000

    def _strategy_to_dict(self, config: StrategyConfig) -> dict:
        return {
            "name": config.name,
            "file_path": config.file_path,
            "column_mapping": {
                "date_col": config.column_mapping.date_col,
                "gain_pct_col": config.column_mapping.gain_pct_col,
                "mae_pct_col": config.column_mapping.mae_pct_col,
                "ticker_col": config.column_mapping.ticker_col,
            },
            "sheet_name": config.sheet_name,
            "stop_pct": config.stop_pct,
            "efficiency": config.efficiency,
            "size_type": config.size_type.value,
            "size_value": config.size_value,
            "max_compound": config.max_compound,
            "is_baseline": config.is_baseline,
            "is_candidate": config.is_candidate,
        }

    def _dict_to_strategy(self, data: dict) -> StrategyConfig:
        mapping = PortfolioColumnMapping(
            date_col=data["column_mapping"]["date_col"],
            gain_pct_col=data["column_mapping"]["gain_pct_col"],
            mae_pct_col=data["column_mapping"].get("mae_pct_col"),
            ticker_col=data["column_mapping"].get("ticker_col"),
        )

        # Migrate old efficiency format (decimal) to new format (percentage points)
        # Old format: 0.05 = 5%, New format: 5.0 = 5%
        efficiency = data.get("efficiency", 5.0)
        if efficiency < 1.0:
            # Old decimal format, convert to percentage points
            efficiency = efficiency * 100.0
            logger.info(f"Migrated efficiency from {data.get('efficiency')} to {efficiency}")

        return StrategyConfig(
            name=data["name"],
            file_path=data["file_path"],
            column_mapping=mapping,
            sheet_name=data.get("sheet_name"),
            stop_pct=data.get("stop_pct", 2.0),
            efficiency=efficiency,
            size_type=PositionSizeType(data.get("size_type", "custom_pct")),
            size_value=data.get("size_value", 10.0),
            max_compound=data.get("max_compound"),
            is_baseline=data.get("is_baseline", False),
            is_candidate=data.get("is_candidate", False),
        )

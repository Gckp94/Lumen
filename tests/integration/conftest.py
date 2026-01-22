# tests/integration/conftest.py
import pytest
from src.core.portfolio_config_manager import PortfolioConfigManager


@pytest.fixture
def isolated_config_manager(tmp_path):
    """Provide a config manager that writes to tmp_path, not user's home."""
    config_file = tmp_path / "portfolio_config.json"
    return PortfolioConfigManager(config_file)

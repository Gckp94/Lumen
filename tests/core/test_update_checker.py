"""Tests for UpdateChecker."""

from unittest.mock import MagicMock, patch

from src.core.update_checker import UpdateChecker


class TestUpdateChecker:
    """Tests for UpdateChecker class."""

    def test_parse_version(self):
        """Test version parsing."""
        checker = UpdateChecker("owner", "repo")

        assert checker._parse_version("1.0.0") == (1, 0, 0)
        assert checker._parse_version("2.1.3") == (2, 1, 3)
        assert checker._parse_version("v1.2.0") == (1, 2, 0)

    def test_is_newer_version(self):
        """Test version comparison."""
        checker = UpdateChecker("owner", "repo")

        assert checker._is_newer("2.0.0", "1.0.0") is True
        assert checker._is_newer("1.1.0", "1.0.0") is True
        assert checker._is_newer("1.0.1", "1.0.0") is True
        assert checker._is_newer("1.0.0", "1.0.0") is False
        assert checker._is_newer("0.9.0", "1.0.0") is False

    @patch("src.core.update_checker.requests.get")
    def test_check_for_update_available(self, mock_get):
        """Test checking for updates when update is available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tag_name": "v2.0.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v2.0.0",
            "assets": [
                {
                    "name": "Lumen.exe",
                    "browser_download_url": "https://example.com/Lumen.exe",
                }
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        checker = UpdateChecker("owner", "repo")
        result = checker.check_for_update("1.0.0")

        assert result is not None
        assert result.version == "2.0.0"
        assert result.download_url == "https://example.com/Lumen.exe"

    @patch("src.core.update_checker.requests.get")
    def test_check_for_update_not_available(self, mock_get):
        """Test checking for updates when already up to date."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "tag_name": "v1.0.0",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "assets": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        checker = UpdateChecker("owner", "repo")
        result = checker.check_for_update("1.0.0")

        assert result is None

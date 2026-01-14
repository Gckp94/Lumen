"""Auto-update checker using GitHub Releases API.

Checks for new versions and provides download URLs for updates.
"""

import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}/releases/latest"


@dataclass
class UpdateInfo:
    """Information about an available update."""

    version: str
    download_url: str
    release_url: str


class UpdateChecker:
    """Checks GitHub releases for updates.

    Uses the GitHub Releases API to check for newer versions
    and provides download URLs for the Windows executable.
    """

    def __init__(self, owner: str, repo: str) -> None:
        """Initialize the update checker.

        Args:
            owner: GitHub repository owner.
            repo: GitHub repository name.
        """
        self.owner = owner
        self.repo = repo
        self._api_url = GITHUB_API_URL.format(owner=owner, repo=repo)

    def _parse_version(self, version_str: str) -> tuple[int, int, int]:
        """Parse a version string into a tuple.

        Args:
            version_str: Version string like "1.0.0" or "v1.0.0".

        Returns:
            Tuple of (major, minor, patch).
        """
        # Remove 'v' prefix if present
        version_str = version_str.lstrip("v")
        parts = version_str.split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    def _is_newer(self, remote_version: str, current_version: str) -> bool:
        """Check if remote version is newer than current.

        Args:
            remote_version: Version from GitHub.
            current_version: Currently installed version.

        Returns:
            True if remote is newer.
        """
        remote = self._parse_version(remote_version)
        current = self._parse_version(current_version)
        return remote > current

    def check_for_update(self, current_version: str) -> UpdateInfo | None:
        """Check GitHub for a newer version.

        Args:
            current_version: Currently installed version.

        Returns:
            UpdateInfo if update available, None otherwise.
        """
        try:
            response = requests.get(self._api_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            remote_version = data.get("tag_name", "").lstrip("v")
            if not remote_version:
                logger.warning("No version tag found in release")
                return None

            if not self._is_newer(remote_version, current_version):
                logger.info("Already up to date: %s", current_version)
                return None

            # Find Windows executable in assets
            download_url = None
            for asset in data.get("assets", []):
                if asset.get("name", "").lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url")
                    break

            if not download_url:
                logger.warning("No Windows executable found in release assets")
                return None

            logger.info("Update available: %s -> %s", current_version, remote_version)
            return UpdateInfo(
                version=remote_version,
                download_url=download_url,
                release_url=data.get("html_url", ""),
            )

        except requests.RequestException as e:
            logger.error("Failed to check for updates: %s", e)
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.error("Failed to parse release data: %s", e)
            return None

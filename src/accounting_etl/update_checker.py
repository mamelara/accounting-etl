"""Update checker for the application."""

import json
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta


class UpdateChecker:
    """Checks for application updates from GitHub releases."""
    
    GITHUB_REPO = "yourusername/accounting-etl"  # TODO: Update with actual repo
    VERSION_FILE = "version.txt"
    CHECK_FILE = "last_check.txt"
    CHECK_INTERVAL_DAYS = 1
    
    def __init__(self):
        self.current_version = self._get_current_version()
    
    def _get_current_version(self) -> str:
        """Read current version from version file."""
        version_path = Path(self.VERSION_FILE)
        if version_path.exists():
            return version_path.read_text().strip()
        return "1.0.0"  # Default version
    
    def _should_check(self) -> bool:
        """Check if we should check for updates (once per day)."""
        check_path = Path(self.CHECK_FILE)
        if not check_path.exists():
            return True
        
        last_check = check_path.read_text().strip()
        try:
            last_date = datetime.strptime(last_check, "%Y-%m-%d")
            return (datetime.now() - last_date).days >= self.CHECK_INTERVAL_DAYS
        except ValueError:
            return True
    
    def _record_check(self) -> None:
        """Record that we checked for updates today."""
        check_path = Path(self.CHECK_FILE)
        check_path.write_text(datetime.now().strftime("%Y-%m-%d"))
    
    def _get_latest_version(self) -> tuple:
        """
        Check GitHub releases for latest version.
        
        Returns (version, download_url) or (None, None) if check fails.
        """
        try:
            api_url = f"https://api.github.com/repos/{self.GITHUB_REPO}/releases/latest"
            
            req = urllib.request.Request(
                api_url,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                version = data.get("tag_name", "").lstrip("v")
                download_url = data.get("html_url", "")
                
                return version, download_url
                
        except Exception:
            # Silently fail if can't check (no internet, etc.)
            return None, None
    
    def check_and_notify(self) -> None:
        """Check for updates and notify user if new version available."""
        if not self._should_check():
            return
        
        self._record_check()
        
        latest_version, download_url = self._get_latest_version()
        
        if latest_version and self._version_is_newer(latest_version, self.current_version):
            print("\n" + "=" * 60)
            print("UPDATE AVAILABLE")
            print("=" * 60)
            print(f"Current version: {self.current_version}")
            print(f"Latest version:  {latest_version}")
            print(f"\nDownload at: {download_url}")
            print("=" * 60 + "\n")
    
    def _version_is_newer(self, new: str, current: str) -> bool:
        """Compare version strings."""
        try:
            new_parts = [int(x) for x in new.split(".")]
            current_parts = [int(x) for x in current.split(".")]
            return new_parts > current_parts
        except ValueError:
            return False

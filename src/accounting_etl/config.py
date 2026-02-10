"""Configuration management for Accounting ETL."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Config:
    """Application configuration."""
    gl_codes: Dict[str, str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.gl_codes is None:
            self.gl_codes = {}

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> Optional["Config"]:
        """Load configuration from JSON file."""
        if config_path is None:
            # Get the directory where this script is located
            script_dir = Path(__file__).parent.parent.parent
            config_path = script_dir / "config" / "config.json"

        if not config_path.exists():
            return None

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except (json.JSONDecodeError, TypeError):
            return None

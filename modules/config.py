"""
Configuration module - Handles loading and storing bot configuration
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Set


DEFAULT_COOLDOWNS = {"retry": 2.0, "hunting": 20.0, "fishing": 40.0}


REQUIRED_GLOBAL_SETTINGS: Set[str] = {
    "various_cooldowns",
    "captcha_retry_amount",
    "solve_captchas",
    "dynamic_delay_amount",
    "console_clear",
}


@dataclass
class BotConfig:
    """Settings container for an individual bot configuration"""

    channel_id_hunting: int
    channel_id_fishing: int

    ball_exceptions: Dict[str, str]
    mon_rarity_hunting: Dict[str, str]
    mon_rarity_fishing: Dict[str, str]

    autobuy: Dict[str, int]
    release_duplicates_amount: int

    retry_cooldown: float
    hunting_cooldown: float
    fishing_cooldown: float

    captcha_retry_amount: int
    solve_captchas: bool
    dynamic_delay_amount: int


class ConfigManager:
    """Manages configuration loading and access"""

    def __init__(self, config_path: str = "config.json"):
        """Initialize configuration manager

        Args:
            config_path: Path to config file
        """
        self.config_path = Path(config_path)
        self.global_config: Dict[str, Any] = {}
        self.bot_configs: Dict[str, Dict[str, Any]] = {}
        self.tokens: List[str] = []
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file"""

        if not self.config_path.exists():
            raise FileNotFoundError(f"Missing config file: {self.config_path}")

        try:

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            missing = REQUIRED_GLOBAL_SETTINGS - set(config.keys())
            if missing:
                raise ValueError(f"Missing required settings: {', '.join(missing)}")

            self.global_config = {
                key: config[key] for key in REQUIRED_GLOBAL_SETTINGS if key in config
            }

            self.tokens = [
                token
                for token in config.keys()
                if token and token not in REQUIRED_GLOBAL_SETTINGS
            ]

            self.bot_configs = {token: config[token] for token in self.tokens}

        except json.JSONDecodeError as e:
            raise ValueError(f"Config file has invalid JSON: {e}")

    def get_bot_config(self, token: str) -> BotConfig:
        """Get configuration for a specific bot

        Args:
            token: Bot token

        Returns:
            BotConfig object with the bot's settings
        """
        if token not in self.bot_configs:
            raise ValueError(f"No configuration for token: {token[:5]}...")

        bot_settings = self.bot_configs[token]
        cooldowns = self.global_config.get("various_cooldowns", {})

        return BotConfig(
            channel_id_hunting=bot_settings.get("channel_id_hunting", 0),
            channel_id_fishing=bot_settings.get("channel_id_fishing", 0),
            ball_exceptions=bot_settings.get("ball_exceptions", {}),
            mon_rarity_hunting=bot_settings.get("mon_rarity_hunting", {}),
            mon_rarity_fishing=bot_settings.get("mon_rarity_fishing", {}),
            autobuy=bot_settings.get("autobuy", {}),
            release_duplicates_amount=bot_settings.get("release_duplicates_amount", 0),
            retry_cooldown=cooldowns.get("retry_cooldown", DEFAULT_COOLDOWNS["retry"]),
            hunting_cooldown=cooldowns.get(
                "hunting_cooldown", DEFAULT_COOLDOWNS["hunting"]
            ),
            fishing_cooldown=cooldowns.get(
                "fishing_cooldown", DEFAULT_COOLDOWNS["fishing"]
            ),
            captcha_retry_amount=self.global_config.get("captcha_retry_amount", 3),
            solve_captchas=self.global_config.get("solve_captchas", False),
            dynamic_delay_amount=self.global_config.get("dynamic_delay_amount", 0),
        )

    def get_global_setting(self, key: str, default: Any = None) -> Any:
        """Get a global setting

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value
        """
        return self.global_config.get(key, default)

    def get_bot_tokens(self) -> List[str]:
        """Get list of configured bot tokens

        Returns:
            List of bot tokens
        """
        return self.tokens

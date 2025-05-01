"""
Logging module - Handles centralized logging and statistics display
"""

import os
import logging
from typing import List, Optional
from rich.table import Table
from datetime import datetime
from rich.console import Console
from discord.ext.commands import Bot


console = Console()


_logger = logging.getLogger("Telerium")


_logging_setup_done = False


def setup_logging(log_level: int = logging.INFO, log_file: str = "telerium.log"):
    """Set up logging configuration

    Args:
        log_level: Logging level (default: INFO)
        log_file: Log file path
    """
    global _logging_setup_done

    if _logging_setup_done:
        return

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    for handler in _logger.handlers[:]:
        _logger.removeHandler(handler)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ],
    )

    _logger.setLevel(log_level)

    try:
        import discord.utils

        if hasattr(discord.utils, "setup_logging"):

            discord_logger = logging.getLogger("discord")
            discord_logger.setLevel(log_level)

    except (ImportError, AttributeError):
        pass

    _logging_setup_done = True


def get_logger() -> logging.Logger:
    """Get the module logger

    Returns:
        Logger instance
    """
    return _logger


def display_stats(bots: List[Bot], start_time: datetime, clear_console: bool) -> None:
    """Display bot statistics in a rich table

    Args:
        bots: List of active bots
        start_time: Time when the program started
        clear_console: Whether to clear console before display
    """

    elapsed_time = datetime.now() - start_time
    hours = elapsed_time.seconds // 3600
    minutes = (elapsed_time.seconds % 3600) // 60
    seconds = elapsed_time.seconds % 60

    table = Table(
        show_header=True,
        title=f"Telerium ETA {hours} hours {minutes} minutes {seconds} seconds",
        header_style="bold green",
        title_style="bold red",
    )

    for name in [
        "Username",
        "Encounters",
        "Catches",
        "Fish Encounters",
        "Fish Catches",
        "Coins Earned",
        "Hunting Status",
        "Fishing Status",
    ]:
        table.add_column(name, style="bold blue")

    total_encounters = total_catches = total_fish_encounters = total_fish_catches = (
        total_coins_earned
    ) = 0

    for bot in bots:
        if not bot.is_ready():
            continue

        table.add_row(
            str(bot.user.name),
            str(bot.encounters),
            str(bot.catches),
            str(bot.fish_encounters),
            str(bot.fish_catches),
            str(bot.coins_earned),
            str(bot.hunting_status),
            str(bot.fishing_status),
        )

        total_encounters += bot.encounters
        total_catches += bot.catches
        total_fish_encounters += bot.fish_encounters
        total_fish_catches += bot.fish_catches
        total_coins_earned += bot.coins_earned

    table.add_section()
    table.add_row(
        "Total",
        str(total_encounters),
        str(total_catches),
        str(total_fish_encounters),
        str(total_fish_catches),
        str(total_coins_earned),
        "",
        "",
        style="bold red",
    )

    if clear_console:
        os.system("cls" if os.name == "nt" else "clear")

    console.print(table)

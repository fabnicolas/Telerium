"""
Utility module - Common functions used throughout the application

This module provides shared utility functions for delay management,
button interaction, and other common operations.
"""

import asyncio
import random
from typing import Optional, Callable, Any, List
from functools import wraps


def safe_async(func: Callable) -> Callable:
    """Makes async functions safer by catching errors"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            from modules.logging import get_logger

            log = get_logger()
            log.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return None

    return wrapper


async def random_delay(base_delay: float = 0, max_random_ms: int = 0) -> None:
    """Add a human-like random delay to actions

    Args:
        base_delay: Base delay in seconds
        max_random_ms: Maximum random milliseconds to add
    """
    if max_random_ms > 0:
        random_ms = random.randint(0, max_random_ms) / 1000
        await asyncio.sleep(base_delay + random_ms)
    else:
        await asyncio.sleep(base_delay)

async def find_and_click_button(
    components: List[Any], button_ids: List[str], delay_before_click: float = 0
) -> bool:
    """Find and click a button with one of the given IDs

    Args:
        components: List of component rows from a message
        button_ids: List of button IDs to look for, in order of preference
        delay_before_click: Delay in seconds before clicking

    Returns:
        True if button was found and clicked, False otherwise
    """
    try:

        button = None
        for component in components:
            for child in component.children:
                if hasattr(child, "custom_id") and child.custom_id in button_ids:

                    if button is None or button_ids.index(
                        child.custom_id
                    ) > button_ids.index(button.custom_id):
                        button = child

        if button:

            if delay_before_click > 0:
                await asyncio.sleep(delay_before_click)

            await button.click()
            return True

    except Exception as e:
        from modules.logging import get_logger

        log = get_logger()
        log.error(f"Error clicking button: {e}")

    return False


def extract_coins(text: str) -> int:
    """Extract coin amount from a text string

    Args:
        text: Text containing coin amount

    Returns:
        Extracted coin amount as integer, 0 if not found
    """
    try:
        if "You earned " in text:
            coin_text = text.split("You earned ")[1].split(" ")[0]
            return int(coin_text.replace(",", ""))
    except (IndexError, ValueError):
        pass

    return 0
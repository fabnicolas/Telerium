"""
Ball manager module - Handles Pokeball selection and purchasing
"""
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from modules.utils import random_delay, safe_async
from i18n import get_string

# Mapping for ball auto-buy detection
BALLS_TO_BUY = {
    get_string("BALLS", "pokeballs_empty")[0]: "pb",
    get_string("BALLS", "pokeballs_empty")[1]: "pb",
    get_string("BALLS", "greatballs_empty"): "gb",
    get_string("BALLS", "ultraballs_empty"): "ub",
    get_string("BALLS", "masterballs_empty"): "mb",
}


@safe_async
async def auto_buy(bot: Any, config: Any, commands: Dict[str, Any], message: Any) -> None:
    """Automatically buy Pokeballs when they run out

    Args:
        bot: Bot instance
        config: Configuration object
        commands: Available commands dictionary
        message: Message containing embed with ball information
    """
    # Skip if no embeds or footer
    if not message.embeds or not message.embeds[0].footer:
        return

    # Check which balls we need to buy
    footer_text = message.embeds[0].footer.text
    to_buy = []

    for text, ball_code in BALLS_TO_BUY.items():
        if text in footer_text:
            to_buy.append(ball_code)
            break  # Only buy one type at a time

    # If we need balls and auto-buy is enabled
    if to_buy and to_buy[0] in config.autobuy and config.autobuy[to_buy[0]] > 0:
        # Only buy if we're not already buying
        if not bot.auto_buy_queued:
            bot.auto_buy_queued = True

            # Add a small delay to seem human
            await random_delay(2, config.dynamic_delay_amount)

            # Buy the balls
            ball_type = to_buy[0]
            amount = config.autobuy[ball_type]

            task = asyncio.create_task(
                commands["shop buy"](item=ball_type, amount=amount)
            )

            bot.auto_buy_queued = False
            await task


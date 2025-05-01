"""
CAPTCHA handling module - Detects and solves CAPTCHA challenges

This module contains logic for detecting when a CAPTCHA appears and
delegating to appropriate solvers to handle it.
"""

import asyncio
import re
from typing import Dict, Any, Optional, Callable, List

from modules.utils import safe_async, random_delay, find_and_click_button
from modules.logging import get_logger
from i18n import get_string


class CaptchaHandler:
    """Handles CAPTCHA detection and solving"""

    def __init__(self, bot: Any, config: Any):
        """Initialize the CAPTCHA handler

        Args:
            bot: Bot instance
            config: Configuration object
        """
        self.bot = bot
        self.config = config
        self.retry_count = 0
        self.solver_active = False
        self.logger = get_logger()

    @safe_async
    async def detect_captcha(self, message: Any) -> bool:
        """Check if a message contains a CAPTCHA

        Args:
            message: Discord message to check

        Returns:
            True if message contains a CAPTCHA, False otherwise
        """

        if (
            not message.embeds
            or not message.interaction
            or message.interaction.user != self.bot.user
        ):
            return False

        embed = message.embeds[0]
        captcha_indicators = ["captcha", "verification"]

        if embed.title:
            title_lower = embed.title.lower()
            if any(indicator in title_lower for indicator in captcha_indicators):
                return True

        if embed.description:
            desc_lower = embed.description.lower()
            if any(indicator in desc_lower for indicator in captcha_indicators):
                return True

        return False

    @safe_async
    async def solve_captcha(self, message: Any) -> bool:
        """Attempt to solve a CAPTCHA

        Args:
            message: Message containing the CAPTCHA

        Returns:
            True if CAPTCHA was solved, False otherwise
        """

        if self.retry_count >= self.config.captcha_retry_amount:
            self.logger.warning("CAPTCHA retry limit reached")
            return False

        self.retry_count += 1

        if not self.config.solve_captchas or self.solver_active:
            return False

        self.solver_active = True

        try:

            if not message.embeds or not message.embeds[0].description:
                return False

            description = message.embeds[0].description

            captcha_type = self._determine_captcha_type(description)

            if captcha_type == "simple_math":
                return await self._solve_math_captcha(message, description)
            elif captcha_type == "pokemon_silhouette":
                return await self._solve_silhouette_captcha(message, description)
            elif captcha_type == "multiple_choice":
                return await self._solve_multiple_choice_captcha(message)
            else:
                self.logger.warning(f"Unknown CAPTCHA type: {captcha_type}")
                return False

        except Exception as e:
            self.logger.error(f"Error solving CAPTCHA: {e}")
            return False
        finally:

            self.solver_active = False

    def _determine_captcha_type(self, description: str) -> str:
        """Determine the type of CAPTCHA based on the description

        Args:
            description: CAPTCHA description text

        Returns:
            CAPTCHA type as string
        """

        if any(
            op in description.lower()
            for op in ["add", "subtract", "plus", "minus", "+"]
        ):
            return "simple_math"

        if (
            "silhouette" in description.lower()
            or "who's that pokemon" in description.lower()
        ):
            return "pokemon_silhouette"

        return "multiple_choice"

    async def _solve_math_captcha(self, message: Any, description: str) -> bool:
        """Solve a math equation CAPTCHA

        Args:
            message: Message containing the CAPTCHA
            description: CAPTCHA description text

        Returns:
            True if solved successfully, False otherwise
        """

        try:

            math_patterns = [
                r"(\d+)\s*\+\s*(\d+)",
                r"(\d+)\s*\-\s*(\d+)",
                r"add\s*(\d+)\s*(?:and|to)\s*(\d+)",
                r"subtract\s*(\d+)\s*from\s*(\d+)",
            ]

            result = None

            for pattern in math_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    a, b = int(match.group(1)), int(match.group(2))

                    if "+" in pattern or "add" in pattern:
                        result = a + b
                    elif "-" in pattern or "subtract" in pattern:
                        if "from" in pattern:
                            result = b - a
                        else:
                            result = a - b
                    break

            if result is not None:

                await random_delay(1.5, self.config.dynamic_delay_amount)

                for component in message.components:
                    for child in component.children:
                        if (
                            hasattr(child, "custom_id")
                            and child.type.name == "TextInput"
                        ):

                            await child.send(str(result))
                            return True

                for component in message.components:
                    for child in component.children:
                        if hasattr(child, "label") and child.label == str(result):
                            await child.click()
                            return True

        except Exception as e:
            self.logger.error(f"Error solving math CAPTCHA: {e}")

        return False

    async def _solve_silhouette_captcha(self, message: Any, description: str) -> bool:
        """Solve a Pokemon silhouette CAPTCHA

        Args:
            message: Message containing the CAPTCHA
            description: CAPTCHA description text

        Returns:
            True if solved successfully, False otherwise
        """

        await random_delay(2, self.config.dynamic_delay_amount)

        if len(message.components) > 0 and len(message.components[0].children) > 0:

            buttons = []
            for component in message.components:
                buttons.extend(
                    [
                        child
                        for child in component.children
                        if hasattr(child, "custom_id")
                    ]
                )

            if buttons:

                import random

                button = random.choice(buttons)
                await button.click()
                return True

        return False

    async def _solve_multiple_choice_captcha(self, message: Any) -> bool:
        """Solve a multiple choice CAPTCHA

        Args:
            message: Message containing the CAPTCHA

        Returns:
            True if solved successfully, False otherwise
        """

        await random_delay(2, self.config.dynamic_delay_amount)

        buttons = []
        for component in message.components:
            buttons.extend(
                [child for child in component.children if hasattr(child, "custom_id")]
            )

        if buttons:

            import random

            button = random.choice(buttons)
            await button.click()
            return True

        return False

    @safe_async
    async def handle_message(self, message: Any) -> bool:
        """Check for and handle CAPTCHAs in a message

        Args:
            message: Discord message to check

        Returns:
            True if a CAPTCHA was detected and handled, False otherwise
        """

        if await self.detect_captcha(message):
            self.logger.info("CAPTCHA detected")

            solved = await self.solve_captcha(message)

            if solved:
                self.logger.info("CAPTCHA potentially solved")

                self.retry_count = 0
                return True
            else:
                self.logger.warning("Failed to solve CAPTCHA")
                return True

        return False

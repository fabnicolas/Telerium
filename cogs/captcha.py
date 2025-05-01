"""
CAPTCHA handling module - Detects and solves CAPTCHA challenges automatically

This module detects when a CAPTCHA appears during hunting or fishing
and uses the configured solver to respond with the correct answer.
"""

from discord.ext import commands
from modules.captcha_handler import CaptchaHandler
from i18n import get_string


class Captcha(commands.Cog):
    """Handles CAPTCHA detection and solving"""

    def __init__(self, bot):
        """Initialize the CAPTCHA cog

        Args:
            bot: Bot instance
        """
        self.bot = bot
        self.config = bot.config
        self.handler = CaptchaHandler(bot, bot.config)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages and check for CAPTCHAs

        Args:
            message: Message to check
        """

        if not message.interaction or message.interaction.user != self.bot.user:
            return

        await self.handler.handle_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Listen for edited messages and check for CAPTCHAs

        Args:
            before: Original message
            after: Edited message
        """

        if not after.interaction or after.interaction.user != self.bot.user:
            return

        await self.handler.handle_message(after)

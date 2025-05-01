"""
Startup module - Handles bot initialization and game command loops
"""

from time import time
from discord.ext import commands, tasks


async def get_available_commands(bot, channel_id):
    """Get available commands in a channel

    Returns a tuple of (channel, commands_dict) or (None, None) if not available
    """

    if channel_id == 0:
        return None, None

    channel = bot.get_channel(channel_id)

    pokecord_id = 664508672713424926

    command_dict = {}
    app_commands = await channel.application_commands()

    for cmd in app_commands:
        if cmd.application_id == pokecord_id:
            command_dict[cmd.name] = cmd

    for cmd in list(command_dict.values()):
        for sub_cmd in cmd.children:
            command_dict[f"{cmd.name} {sub_cmd.name}"] = sub_cmd

    return channel, command_dict


class Startup(commands.Cog):
    """Handles bot startup and core automation loops"""

    def __init__(self, bot):
        """Initialize the startup cog"""
        self.bot = bot
        self.config = bot.config

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready and logged in"""
        print(f"Started grinding as {self.bot.user.name}!")

        self.bot.hunting_channel, self.bot.hunting_channel_commands = (
            await get_available_commands(self.bot, self.config.channel_id_hunting)
        )

        self.bot.fishing_channel, self.bot.fishing_channel_commands = (
            await get_available_commands(self.bot, self.config.channel_id_fishing)
        )

        if self.bot.hunting_channel_commands:

            await self.bot.hunting_channel_commands["pokemon"]()
            self.check_hunt.start()

        if self.bot.fishing_channel_commands:

            await self.bot.fishing_channel_commands["fish spawn"]()
            self.check_fish.start()

    @tasks.loop(seconds=20)
    async def check_hunt(self):
        """Periodically checks if we can hunt again"""
        try:

            if not hasattr(self.bot, "limit"):
                self.bot.limit = False
            if not hasattr(self.bot, "last_hunt"):
                self.bot.last_hunt = time()

            if self.bot.limit:
                self.check_hunt.stop()
                return

            if time() - self.bot.last_hunt < 20:
                return

            await self.bot.hunting_channel_commands["pokemon"]()

        except Exception as e:
            import logging

            logging.getLogger("Telerium").error(
                f"Error in check_hunt: {e}", exc_info=True
            )

    @tasks.loop(seconds=40)
    async def check_fish(self):
        """Periodically checks if we can fish again"""
        try:

            if not hasattr(self.bot, "last_fish"):
                self.bot.last_fish = time()

            if time() - self.bot.last_fish < 40:
                return

            await self.bot.fishing_channel_commands["fish spawn"]()

        except Exception as e:
            import logging

            logging.getLogger("Telerium").error(
                f"Error in check_fish: {e}", exc_info=True
            )

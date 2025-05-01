"""
Fishing module - Handles Pokemon fishing automation

This module manages the fishing gameplay loop:
- Spawning fish
- Catching fish based on configured preferences
- Managing ball usage based on fish rarity
- Handling auto-release of duplicates
- Managing cooldowns between fishing attempts
"""

import json
import asyncio
from time import time
from random import randint

from discord import InvalidData
from discord.ext import commands

from modules.auto_buy import auto_buy


with open("fishing_map.json") as f:
    FISH_RARITY = json.load(f)


class Fishing(commands.Cog):
    """Handles automated Pokemon fishing"""

    def __init__(self, bot):
        """Set up the fishing module"""
        self.bot = bot
        self.config = bot.config

    async def wait_delay(self, base_delay=0):
        """Add a human-like random delay to actions"""
        random_ms = randint(0, self.config.dynamic_delay_amount) / 1000
        await asyncio.sleep(base_delay + random_ms)

    async def retry_hunt(self):
        """Wait for cooldown and try fishing again"""

        self.bot.last_fish = time()
        await asyncio.sleep(self.config.fishing_cooldown)

        await self.wait_delay()

        await self.bot.fishing_channel_commands["fish spawn"]()

    def ball_selector(self, fish_name):
        """Determine which ball to use based on the fish"""

        description = fish_name.lower()

        if "shiny" in description:
            return self.config.mon_rarity_fishing["Shiny"]
        elif "golden" in description:
            return self.config.mon_rarity_fishing["Golden"]
        else:

            fish_name = fish_name.split("**")[3]
            rarity = FISH_RARITY[fish_name]
            return self.config.mon_rarity_fishing[rarity]

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle new fishing messages"""

        if not message.interaction:
            return

        is_our_fishing = (
            message.interaction.name == "fish spawn"
            and message.interaction.user == self.bot.user
            and message.channel.id == self.config.channel_id_fishing
        )

        if not is_our_fishing:
            return

        if "Please wait" in message.content:

            self.bot.fishing_status = "Grinding..."
            await self.bot.log()

            await asyncio.sleep(self.config.retry_cooldown)
            await self.wait_delay()
            await self.bot.fishing_channel_commands["fish spawn"]()

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Handle fishing message updates"""

        if not after.interaction or not after.embeds:
            return

        is_our_fishing = (
            after.interaction.user == self.bot.user
            and after.interaction.name == "fish spawn"
            and after.channel.id == self.config.channel_id_fishing
        )

        if not is_our_fishing:
            return

        content_unchanged = after.content == before.content
        embed_unchanged = False

        if before.embeds and after.embeds:
            embed_unchanged = (
                after.embeds[0].description == before.embeds[0].description
            )

        if content_unchanged and embed_unchanged:
            return

        description = after.embeds[0].description

        if (
            "Not even a nibble" in description
            or "The Pokemon got away..." in description
        ):
            self.bot.fishing_status = "Grinding..."
            await self.bot.log()
            await self.retry_hunt()

        elif "cast" in description and "click the" in description:
            self.bot.fishing_status = "Grinding..."
            self.bot.last_fish = time()
            await self.bot.log()

            try:
                await after.components[0].children[0].click()
            except (InvalidData, IndexError, AttributeError):

                pass

        elif "fished" in description:

            self.bot.fish_encounters += 1
            await self.bot.log()

            ball = self.ball_selector(description)

            available_balls = ["mb", "db", "prb", "ub", "gb", "pb"]

            usable_balls = available_balls[available_balls.index(ball) :]

            buttons = []
            for component in after.components:
                for child in component.children:
                    for ball in usable_balls:
                        if child.custom_id == f"{ball}_fish":
                            buttons.append(child)

            if buttons:

                await self.wait_delay()
                await buttons[-1].click()

        elif "fished" in before.embeds[0].description:

            tasks = []

            if "caught" in description:
                self.bot.fish_catches += 1
                self.bot.duplicates += 1
                await self.bot.log()

                should_release = (
                        self.config.release_duplicates_amount > 0
                        and self.bot.duplicates >= self.config.release_duplicates_amount
                )

                if should_release:
                    self.bot.duplicates = 0
                    await asyncio.sleep(2)
                    await self.wait_delay()

                    tasks.append(
                        asyncio.create_task(
                            self.bot.fishing_channel_commands["release duplicates"]()
                        )
                    )

            if "Your next Quest is now ready!" in before.content:
                await asyncio.sleep(1)
                await self.wait_delay()

                tasks.append(
                    asyncio.create_task(
                        self.bot.fishing_channel_commands["quest info"]()
                    )
                )

            tasks.append(
                asyncio.create_task(
                    auto_buy(
                        self.bot, self.config, self.bot.fishing_channel_commands, after
                    )
                )
            )

            await asyncio.sleep(self.config.fishing_cooldown)
            await self.wait_delay()
            await self.bot.fishing_channel_commands["fish spawn"]()

            for task in tasks:
                await task
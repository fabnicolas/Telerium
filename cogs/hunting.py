"""
Hunting module - Automates Pokemon hunting on Discord

This module handles the Pokemon hunting gameplay loop:
- Detecting and catching wild Pokemon
- Selecting appropriate Pokeballs based on rarity
- Managing cooldowns and rate limits
- Handling auto-release of duplicates
- Auto-buying Pokeballs when supplies are low
"""

import asyncio
from time import time
from random import randint

from discord.ext import commands
from discord import InvalidData
from modules.auto_buy import auto_buy


BALLS_TO_BUY = {
    "Pokeballs: 0": "pb",
    "Pokeballs : 0": "pb",
    "Greatballs: 0": "gb",
    "Ultraballs: 0": "ub",
    "Masterballs: 0": "mb",
}


class Hunting(commands.Cog):
    """Handles Pokemon hunting automation"""

    def __init__(self, bot):
        """Set up the hunting module"""
        self.bot = bot
        self.config = bot.config

    async def wait_delay(self, base_delay=0):
        """Add a human-like random delay to actions"""
        random_ms = randint(0, self.config.dynamic_delay_amount) / 1000
        await asyncio.sleep(base_delay + random_ms)

    async def retry_hunt(self):
        """Wait for cooldown and try hunting again"""

        await asyncio.sleep(self.config.retry_cooldown)

        await self.wait_delay()

        await self.bot.hunting_channel_commands["pokemon"]()

    def ball_selector(self, pokemon_name, rarity_text):
        """Choose the best ball based on Pokemon and rarity"""

        if pokemon_name in self.config.ball_exceptions:
            return self.config.ball_exceptions[pokemon_name]

        matching_rarities = []

        for rarity in self.config.mon_rarity_hunting:
            if rarity in rarity_text:
                matching_rarities.append(rarity)

        if matching_rarities:
            return self.config.mon_rarity_hunting[matching_rarities[-1]]

        return "pb"

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle new hunting messages"""
        try:

            if not message.interaction:
                return

            is_our_hunt = (
                message.interaction.name == "pokemon"
                and message.interaction.user == self.bot.user
                and message.channel.id == self.config.channel_id_hunting
            )

            if not is_our_hunt:
                return

            if "Please wait" in message.content:
                await self.retry_hunt()
                return

            if not message.embeds:
                return

            description = message.embeds[0].description
            if "You have reached your daily catch limit!" in description:

                if not hasattr(self.bot, "limit"):
                    self.bot.limit = False

                self.bot.limit = True
                self.bot.hunting_status = "Encounter limit reached!"
                await self.bot.log()
                return

            if "found a wild" not in message.content:
                return

            self.bot.hunting_status = "Grinding..."

            if not hasattr(self.bot, "encounters"):
                self.bot.encounters = 0

            self.bot.encounters += 1
            self.bot.last_hunt = time()
            await self.bot.log()

        except Exception as e:
            import logging

            logging.getLogger("Telerium").error(
                f"Error in hunting on_message: {e}", exc_info=True
            )

        pokemon_name = description.split("**")[3]
        footer_text = message.embeds[0].footer.text

        ball = self.ball_selector(pokemon_name, footer_text)

        available_balls = ["mb", "prb", "ub", "gb", "pb"]

        usable_balls = available_balls[available_balls.index(ball) :]

        buttons = []
        for component in message.components:
            for child in component.children:
                if hasattr(child, "custom_id"):
                    for ball_type in usable_balls:
                        if child.custom_id == ball_type:
                            buttons.append(child)

        if not buttons:
            return

        try:

            await self.wait_delay()
            await buttons[-1].click()
        except InvalidData:

            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Handle edited hunting messages (typically catch results)"""
        try:

            if not after.interaction:
                return

            is_our_hunt = (
                after.interaction.name == "pokemon"
                and after.interaction.user == self.bot.user
                and after.channel.id == self.config.channel_id_hunting
                and "found a wild" in before.content
            )

            if not is_our_hunt:
                return

            content_unchanged = after.content == before.content
            embed_unchanged = False

            if after.embeds and before.embeds:
                if after.embeds[0].description == before.embeds[0].description:
                    embed_unchanged = True

            if content_unchanged and embed_unchanged:
                return

            tasks = []

            if after.embeds and "caught" in after.embeds[0].description:

                if not hasattr(self.bot, "catches"):
                    self.bot.catches = 0
                if not hasattr(self.bot, "coins_earned"):
                    self.bot.coins_earned = 0
                if not hasattr(self.bot, "duplicates"):
                    self.bot.duplicates = 0

                self.bot.catches += 1

                footer_text = after.embeds[0].footer.text
                if "You earned " in footer_text:
                    coin_text = footer_text.split("You earned ")[1].split(" ")[0]
                    self.bot.coins_earned += int(coin_text.replace(",", ""))

                await self.bot.log()

                if "has been added to your Pokedex" not in after.embeds[0].description:
                    self.bot.duplicates += 1

                if (
                    self.config.release_duplicates_amount > 0
                    and self.bot.duplicates >= self.config.release_duplicates_amount
                ):

                    self.bot.duplicates = 0
                    await asyncio.sleep(2)
                    await self.wait_delay()

                    tasks.append(
                        asyncio.create_task(
                            self.bot.hunting_channel_commands["release duplicates"]()
                        )
                    )

        except Exception as e:
            import logging

            logging.getLogger("Telerium").error(
                f"Error in hunting on_message_edit: {e}", exc_info=True
            )

        if "Your next Quest is now ready!" in before.content:
            await asyncio.sleep(1)
            await self.wait_delay()

            tasks.append(
                asyncio.create_task(self.bot.hunting_channel_commands["quest info"]())
            )

        tasks.append(
            asyncio.create_task(
                auto_buy(
                    self.bot, self.config, self.bot.hunting_channel_commands, after
                )
            )
        )

        await asyncio.sleep(self.config.hunting_cooldown)
        await self.wait_delay()
        await self.bot.hunting_channel_commands["pokemon"]()

        for task in tasks:
            await task
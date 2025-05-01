#!/usr/bin/env python3
"""
Telerium - Discord Bot Automation

This application automates hunting and fishing gameplay with Discord bots,
optimizing ball selection, handling captchas, and managing resources efficiently.
"""
import asyncio
import contextlib
import logging
import signal
import sys
from datetime import datetime
from time import time
from typing import List

import discord
from discord.ext import commands
from rich.console import Console

from modules.config import ConfigManager
from modules.logging import setup_logging, display_stats, get_logger
from i18n import load_language, get_string

# Set up console
console = Console()

# Global variables
active_bots: List[commands.Bot] = []
start_time = datetime.now()
running = True

# Set up logging
setup_logging()
logger = get_logger()


async def log_stats():
    """Display bot statistics in the console"""
    global active_bots, start_time
    
    try:
        # Get global settings
        clear_console = config_manager.get_global_setting("console_clear", True)
        
        # Display stats
        display_stats(active_bots, start_time, clear_console)
        
    except Exception as e:
        logger.error(f"Error displaying stats: {e}")


async def create_bot(token: str):
    """Create and set up a bot instance
    
    Args:
        token: Bot token
        
    Returns:
        Configured Bot instance
    """
    # Create bot without intents (discord.py-self doesn't use intents)
    bot = commands.Bot(command_prefix="!")
    
    # Get bot config
    try:
        bot.config = config_manager.get_bot_config(token)
    except ValueError as e:
        logger.error(f"Config error: {e}")
        return None
        
    # Initialize bot stats
    bot.encounters = 0
    bot.catches = 0
    bot.fish_encounters = 0
    bot.fish_catches = 0
    bot.coins_earned = 0
    bot.duplicates = 0
    bot.last_hunt = time()
    bot.last_fish = time()
    bot.auto_buy_queued = False
    bot.limit = False
    
    # Set up status
    bot.hunting_status = "Initializing"
    bot.fishing_status = "Initializing"
        
    # Add logging function
    bot.log = log_stats
    
    # Load cogs
    from cogs.startup import Startup
    from cogs.hunting import Hunting
    from cogs.fishing import Fishing
    from cogs.captcha import Captcha
    
    await bot.add_cog(Startup(bot))
    await bot.add_cog(Hunting(bot))
    await bot.add_cog(Fishing(bot))
    await bot.add_cog(Captcha(bot))
    
    # Log when bot disconnects
    @bot.event
    async def on_disconnect():
        if not running:
            return  # Don't log during shutdown
        logger.warning(get_string("LOG", "bot_disconnected").format(bot.user.name if bot.user else token[:10]))
    
    return bot


# Global variable to track which bots are currently starting
_bot_starting_tokens = set()

async def start_bot(token: str):
    """Start a bot with the given token
    
    Args:
        token: Bot token
        
    Returns:
        Started bot instance or None if failed
    """
    # Check if this bot is already starting
    token_id = token[:10]  # Use just the first part for identification
    if token_id in _bot_starting_tokens:
        logger.warning(f"Bot with token {token_id}... is already starting")
        return None
        
    try:
        # Mark this bot as starting
        _bot_starting_tokens.add(token_id)
        
        # Create and configure the bot
        bot = await create_bot(token)
        if not bot:
            return None
            
        # Store the start task for later reference/cleanup
        bot._start_task = asyncio.create_task(bot.start(token))
            
        # Wait for bot to be ready
        ready = False
        for _ in range(30):  # Wait up to 30 seconds
            if bot.is_ready():
                ready = True
                break
            
            # Check if the task failed
            if bot._start_task.done() and bot._start_task.exception():
                logger.error(f"Bot startup failed: {bot._start_task.exception()}")
                return None
                
            await asyncio.sleep(1)
            
        if not ready:
            # Cancel the task if the bot didn't become ready
            bot._start_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await bot._start_task
            logger.error(get_string("LOG", "failed_setup").format(token_id))
            return None
            
        return bot
        
    except discord.errors.LoginFailure:
        logger.error(get_string("LOG", "wrong_token").format(token_id))
        return None
    except Exception as e:
        logger.error(get_string("LOG", "bot_error").format(str(e)))
        return None
    finally:
        # Remove token from starting set regardless of outcome
        if token_id in _bot_starting_tokens:
            _bot_starting_tokens.remove(token_id)


async def stop_bot(bot: commands.Bot):
    """Gracefully stop a bot
    
    Args:
        bot: Bot to stop
    """
    try:
        if bot.is_ready():
            logger.info(get_string("LOG", "stopping_bot").format(bot.user.name))
        await bot.close()
    except Exception as e:
        logger.error(get_string("LOG", "error_stopping").format(str(e)))


async def shutdown():
    """Shutdown all bots and exit"""
    global running, active_bots
    
    if not running:
        return
        
    # Mark as shutting down
    running = False
    logger.info(get_string("LOG", "shutting_down"))
    
    try:
        # Stop all bots
        for bot in active_bots[:]:  # Create a copy to avoid modification during iteration
            await stop_bot(bot)
            
        logger.info(get_string("LOG", "all_stopped"))
        
        # Clean up tasks
        loop = asyncio.get_running_loop()
        tasks = [task for task in asyncio.all_tasks(loop) 
                if task is not asyncio.current_task() and not task.done()]
        
        if tasks:
            logger.info(f"Cancelling {len(tasks)} remaining tasks")
            # Cancel all remaining tasks
            for task in tasks:
                task.cancel()
                
            # Wait for tasks to acknowledge cancellation (with timeout)
            try:
                await asyncio.wait(tasks, timeout=3.0)
            except asyncio.CancelledError:
                pass  # This is expected during shutdown
                
        # Stop the loop and exit
        loop.stop()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        # Ensure exit happens
        sys.exit(0)


async def main():
    """Main application entry point"""
    global active_bots, running, config_manager
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        
        # Get bot tokens
        tokens = config_manager.get_bot_tokens()
        if not tokens:
            logger.error(get_string("LOG", "no_tokens"))
            return
            
        # Load language settings
        language = config_manager.get_global_setting("Language", "en")
        load_language(language)
        
        # Log startup
        logger.info(get_string("LOG", "starting_bots").format(len(tokens)))
        
        # Start all bots
        for token in tokens:
            bot = await start_bot(token)
            if bot:
                active_bots.append(bot)
                
        if not active_bots:
            logger.error(get_string("LOG", "no_bots"))
            return
            
        # Keep running until interrupted
        while running:
            await asyncio.sleep(3600)  # Just keep alive
            
    except KeyboardInterrupt:
        logger.info(get_string("LOG", "stopped_by_user"))
    except Exception as e:
        logger.critical(get_string("LOG", "fatal_error").format(str(e)), exc_info=True)
    finally:
        await shutdown()


if __name__ == "__main__":
    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info(get_string("LOG", "shutdown_requested"))
        
        # Handle differently based on whether we're in an event loop
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # We're in an event loop, schedule shutdown task
                loop.create_task(shutdown())
                return
        except RuntimeError:
            # No running event loop
            pass
            
        # If we get here, we're outside the event loop or it's not running
        # Just exit directly
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the main function with proper exception handling
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This shouldn't typically be hit due to the signal handler
        logger.info(get_string("LOG", "stopped_by_user"))
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

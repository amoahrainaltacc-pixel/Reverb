"""
Reverb Music Bot – Entry Point
─────────────────────────────
A production-ready Discord music bot powered by discord.py 2.x, yt-dlp, and FFmpeg.

Usage:
  python main.py

Required env vars (set in .env or your host's secrets panel):
  BOT_TOKEN   – Discord bot token
  PREFIX      – Command prefix (default: .)
  OWNER_ID    – Your Discord user ID
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Optional

import discord
from discord.ext import commands

# ── Ensure project root is on the path ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.player import PlayerManager

# ─── Logging setup ─────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
# Silence noisy discord.py gateway noise
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.voice_client").setLevel(logging.WARNING)

log = logging.getLogger("reverb.main")

# ─── Bot setup ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True   # required for prefix commands
intents.voice_states = True       # track voice channel membership
intents.guilds = True


class Reverb(commands.Bot):
    """Main bot class with startup lifecycle management."""

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.PREFIX),
            intents=intents,
            help_command=None,            # custom help command in General cog
            case_insensitive=True,
            owner_id=config.OWNER_ID or None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"music | {config.PREFIX}help",
            ),
            status=discord.Status.online,
        )
        self.player_manager: Optional[PlayerManager] = None

    # ── Lifecycle ───────────────────────────────────────────────────────────

    async def setup_hook(self) -> None:
        """Called once before the bot logs in; load cogs here."""
        self.player_manager = PlayerManager(self)

        # Load cogs
        from cogs.music import Music
        from cogs.commands import General

        await self.add_cog(Music(self, self.player_manager))
        general_cog = General(self)
        await self.add_cog(general_cog)
        log.info("Cogs loaded successfully.")

        # Wire up the slash-command (app_commands) error handler from the General cog
        self.tree.on_error = general_cog.on_app_command_error

        # Sync slash commands globally (may take ~1 hr for Discord to propagate)
        try:
            synced = await self.tree.sync()
            log.info("Synced %d slash command(s).", len(synced))
        except Exception as exc:
            log.error("Failed to sync slash commands: %s", exc)

    async def on_ready(self) -> None:
        banner = r"""
  ____                        _
 |  _ \ _____   _____ _ __| |__
 | |_) / _ \ \ / / _ \ '__| '_ \
 |  _ <  __/\ V /  __/ |  | |_) |
 |_| \_\___| \_/ \___|_|  |_.__/

        """
        print(banner)
        log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log.info("  Reverb Music Bot is online!  🎵")
        log.info("  User    : %s (ID: %s)", self.user, self.user.id)  # type: ignore
        log.info("  Servers : %d", len(self.guilds))
        log.info("  Prefix  : %s", config.PREFIX)
        log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"🎵 Listening to music | {config.PREFIX}help",
            ),
            status=discord.Status.online,
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info("Joined guild: %s (ID: %s, members: %d)", guild.name, guild.id, guild.member_count)
        # Find a general / system channel to greet
        channel = guild.system_channel or next(
            (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
            None,
        )
        if channel:
            embed = discord.Embed(
                title="🎵  Hey there! I'm Reverb.",
                description=(
                    f"Thanks for inviting me! I'm a powerful music bot that streams "
                    f"high-quality audio from YouTube.\n\n"
                    f"Get started with `{config.PREFIX}play <song>` or `{config.PREFIX}help`."
                ),
                color=config.BRAND_COLOR,
            )
            embed.add_field(
                name="🎶 Quick Start",
                value=(
                    f"`{config.PREFIX}play Never Gonna Give You Up`\n"
                    f"`{config.PREFIX}help` — full command list"
                ),
                inline=False,
            )
            embed.set_footer(text="🎵 Reverb Music Bot  ·  Enjoy the music!")
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        log.info("Left guild: %s (ID: %s)", guild.name, guild.id)
        if self.player_manager:
            self.player_manager.remove(guild)

    # ── Graceful shutdown ───────────────────────────────────────────────────

    async def close(self) -> None:
        log.info("Shutting down Reverb…")
        if self.player_manager:
            for guild in list(self.guilds):
                self.player_manager.remove(guild)
        await super().close()


# ─── Entry point ───────────────────────────────────────────────────────────

async def main() -> None:
    if not config.BOT_TOKEN:
        log.critical(
            "BOT_TOKEN is not set! Please set it in your .env file or environment variables."
        )
        sys.exit(1)

    bot = Reverb()
    async with bot:
        await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Reverb stopped by user.")

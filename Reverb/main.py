"""
Reverb Music Bot – Entry Point
─────────────────────────────
A production-ready Discord music bot powered by discord.py 2.x, yt-dlp, and FFmpeg.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from utils.player import PlayerManager

# ─── Logging ───────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.voice_client").setLevel(logging.WARNING)

log = logging.getLogger("reverb.main")

# ─── Intents ───────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states    = True
intents.guilds          = True


# ─── Bot class ─────────────────────────────────────────────────────────────

class Reverb(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.PREFIX),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_id=config.OWNER_ID or None,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"music | {config.PREFIX}help",
            ),
            status=discord.Status.online,
        )
        self.player_manager: Optional[PlayerManager] = None

    async def setup_hook(self) -> None:
        self.player_manager = PlayerManager(self)

        from cogs.music    import Music
        from cogs.commands import General

        await self.add_cog(Music(self, self.player_manager))
        general_cog = General(self)
        await self.add_cog(general_cog)
        log.info("Cogs loaded successfully.")

        # Wire slash-command error handler
        self.tree.on_error = general_cog.on_app_command_error

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
        log.info("━" * 56)
        log.info("  Reverb Music Bot is online!  🎵")
        log.info("  User    : %s (ID: %s)", self.user, self.user.id)   # type: ignore
        log.info("  Servers : %d", len(self.guilds))
        log.info("  Prefix  : %s", config.PREFIX)
        log.info("━" * 56)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"music | {config.PREFIX}help",
            ),
            status=discord.Status.online,
        )

    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info("Joined guild: %s (ID: %s)", guild.name, guild.id)
        channel = guild.system_channel or next(
            (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
            None,
        )
        if channel:
            from utils.embeds import welcome as welcome_embed
            try:
                await channel.send(embed=welcome_embed(guild.name, config.PREFIX))
            except discord.HTTPException:
                pass

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        log.info("Left guild: %s (ID: %s)", guild.name, guild.id)
        if self.player_manager:
            self.player_manager.remove(guild)

    async def close(self) -> None:
        log.info("Shutting down Reverb…")
        if self.player_manager:
            for guild in list(self.guilds):
                self.player_manager.remove(guild)
        await super().close()


# ─── Entry point ───────────────────────────────────────────────────────────

async def main() -> None:
    if not config.BOT_TOKEN:
        log.critical("BOT_TOKEN is not set! Add it to your .env or Replit Secrets.")
        sys.exit(1)
    async with Reverb() as bot:
        await bot.start(config.BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Reverb stopped by user.")

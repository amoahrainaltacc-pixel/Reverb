"""
Reverb Bot – General Commands Cog
Help, ping, invite, and other utility commands.
"""
from __future__ import annotations

import platform
import time
import logging

import discord
from discord import app_commands
from discord.ext import commands

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import embeds

log = logging.getLogger("reverb.commands")


class General(commands.Cog, name="General"):
    """General utility commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── .help ───────────────────────────────────────────────────────────────

    @commands.command(name="help", aliases=["h"])
    async def help_cmd(self, ctx: commands.Context):
        """Show the full help menu."""
        embed = embeds.help_embed(config.PREFIX)
        await ctx.send(embed=embed)

    @app_commands.command(name="help", description="Show the Reverb help menu")
    async def slash_help(self, interaction: discord.Interaction):
        embed = embeds.help_embed(config.PREFIX)
        await interaction.response.send_message(embed=embed)

    # ── .ping ───────────────────────────────────────────────────────────────

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        """Check bot latency."""
        start = time.perf_counter()
        msg = await ctx.send("Pinging…")
        elapsed = (time.perf_counter() - start) * 1000

        embed = discord.Embed(title="🏓  Pong!", color=config.BRAND_COLOR)
        embed.add_field(name="API Latency", value=f"`{round(self.bot.latency * 1000)}ms`", inline=True)
        embed.add_field(name="Message RTT", value=f"`{round(elapsed)}ms`", inline=True)
        await msg.edit(content=None, embed=embed)

    @app_commands.command(name="ping", description="Check Reverb's latency")
    async def slash_ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(title="🏓  Pong!", color=config.BRAND_COLOR)
        embed.add_field(name="API Latency", value=f"`{latency}ms`", inline=True)
        await interaction.response.send_message(embed=embed)

    # ── .invite ─────────────────────────────────────────────────────────────

    @commands.command(name="invite")
    async def invite(self, ctx: commands.Context):
        """Get the bot invite link."""
        app_id = self.bot.user.id if self.bot.user else "YOUR_BOT_ID"
        perms = discord.Permissions(
            send_messages=True,
            embed_links=True,
            read_messages=True,
            connect=True,
            speak=True,
            use_voice_activation=True,
        )
        url = discord.utils.oauth_url(str(app_id), permissions=perms)

        embed = discord.Embed(
            title="📨  Invite Reverb",
            description=f"[Click here to invite Reverb]({url}) to your server!",
            color=config.BRAND_COLOR,
        )
        embed.set_footer(text="🎵 Reverb Music Bot")
        await ctx.send(embed=embed)

    @app_commands.command(name="invite", description="Get the Reverb invite link")
    async def slash_invite(self, interaction: discord.Interaction):
        app_id = self.bot.user.id if self.bot.user else "YOUR_BOT_ID"
        perms = discord.Permissions(
            send_messages=True,
            embed_links=True,
            read_messages=True,
            connect=True,
            speak=True,
        )
        url = discord.utils.oauth_url(str(app_id), permissions=perms)
        embed = discord.Embed(
            title="📨  Invite Reverb",
            description=f"[Click here]({url}) to invite Reverb to your server!",
            color=config.BRAND_COLOR,
        )
        await interaction.response.send_message(embed=embed)

    # ── .botinfo ────────────────────────────────────────────────────────────

    @commands.command(name="botinfo", aliases=["about"])
    async def botinfo(self, ctx: commands.Context):
        """Show information about Reverb."""
        embed = discord.Embed(
            title="🎵  About Reverb",
            description=(
                "Reverb is a high-quality Discord music bot powered by yt-dlp and FFmpeg. "
                "Stream music from YouTube with a beautiful, interactive player experience."
            ),
            color=config.BRAND_COLOR,
        )
        embed.add_field(name="🐍 Python", value=platform.python_version(), inline=True)
        embed.add_field(name="📦 discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="🖥 Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(
            name="📌 Prefix",
            value=f"`{config.PREFIX}` or slash commands",
            inline=True,
        )
        embed.set_footer(text="🎵 Reverb Music Bot  ·  Made with ❤️")
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    # ─── Global error handler ───────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=embeds.error(
                    f"Missing required argument: `{error.param.name}`.\n"
                    f"Use `{config.PREFIX}help` for usage info.",
                    title="⚠️  Missing Argument",
                )
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=embeds.error(str(error), title="⚠️  Invalid Argument"))
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(embed=embeds.error("This command cannot be used in DMs."))
        elif isinstance(error, commands.BotMissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await ctx.send(
                embed=embeds.error(f"I need the following permissions: `{missing}`")
            )
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                embed=embeds.warning(
                    f"Slow down! Try again in `{error.retry_after:.1f}s`.",
                    title="⏱  Cooldown",
                )
            )
        else:
            log.error("Unhandled command error in %s: %s", ctx.command, error, exc_info=error)
            await ctx.send(
                embed=embeds.error(
                    "An unexpected error occurred. Please try again later.",
                    title="💥  Internal Error",
                )
            )

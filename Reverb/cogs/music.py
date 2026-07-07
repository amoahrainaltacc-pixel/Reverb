"""
Reverb Bot – Music Cog
All music commands and interactive button view.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils import embeds
from utils.player import GuildPlayer, PlayerManager, YTDLSource

log = logging.getLogger("reverb.music")

# Default idle status
_IDLE_ACTIVITY = discord.Activity(
    type=discord.ActivityType.listening,
    name=f"music | {config.PREFIX}help",
)


# ─── Interactive Player Buttons ────────────────────────────────────────────

class PlayerView(discord.ui.View):
    """Persistent button row attached to every now-playing card."""

    def __init__(self, player: GuildPlayer):
        super().__init__(timeout=None)
        self.player = player

    async def _guard(self, interaction: discord.Interaction) -> bool:
        vc = interaction.guild.voice_client if interaction.guild else None
        member_vc = interaction.user.voice.channel if interaction.user.voice else None
        if not vc or not member_vc or vc.channel != member_vc:
            await interaction.response.send_message(
                embed=embeds.error("You must be in the same voice channel as Reverb."),
                ephemeral=True,
            )
            return False
        return True

    # ── ▶️ Resume ──────────────────────────────────────────────────────────
    @discord.ui.button(
        emoji="▶️",
        label="Resume",
        style=discord.ButtonStyle.success,
        custom_id="reverb:resume",
        row=0,
    )
    async def btn_resume(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not await self._guard(interaction):
            return
        ok = self.player.resume()
        embed = (
            embeds.success("Resumed playback.", title="Resumed")
            if ok
            else embeds.warning("Nothing is paused.", title="Warning")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── ⏸ Pause ───────────────────────────────────────────────────────────
    @discord.ui.button(
        emoji="⏸",
        label="Pause",
        style=discord.ButtonStyle.secondary,
        custom_id="reverb:pause",
        row=0,
    )
    async def btn_pause(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not await self._guard(interaction):
            return
        ok = self.player.pause()
        embed = (
            embeds.success("Paused playback.", title="Paused")
            if ok
            else embeds.warning("Nothing is playing.", title="Warning")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── ⏭ Skip ────────────────────────────────────────────────────────────
    @discord.ui.button(
        emoji="⏭",
        label="Skip",
        style=discord.ButtonStyle.primary,
        custom_id="reverb:skip",
        row=0,
    )
    async def btn_skip(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not await self._guard(interaction):
            return
        self.player.skip()
        await interaction.response.send_message(
            embed=embeds.success("Skipped the current track.", title="Skipped"),
            ephemeral=True,
        )

    # ── 🔁 Loop ───────────────────────────────────────────────────────────
    @discord.ui.button(
        emoji="🔁",
        label="Loop",
        style=discord.ButtonStyle.secondary,
        custom_id="reverb:loop",
        row=0,
    )
    async def btn_loop(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not await self._guard(interaction):
            return
        self.player.looping = not self.player.looping
        state = "enabled 🔁" if self.player.looping else "disabled"
        await interaction.response.send_message(
            embed=embeds.success(f"Loop mode **{state}**.", title="Loop"),
            ephemeral=True,
        )

    # ── ⏹ Stop ────────────────────────────────────────────────────────────
    @discord.ui.button(
        emoji="⏹",
        label="Stop",
        style=discord.ButtonStyle.danger,
        custom_id="reverb:stop",
        row=0,
    )
    async def btn_stop(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not await self._guard(interaction):
            return
        self.player.stop()
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
        # Reset bot status
        try:
            await interaction.client.change_presence(activity=_IDLE_ACTIVITY)
        except Exception:
            pass
        await interaction.response.send_message(
            embed=embeds.success("Stopped playback and cleared the queue.", title="Stopped"),
            ephemeral=True,
        )


# ─── Music Cog ─────────────────────────────────────────────────────────────

class Music(commands.Cog, name="Music"):
    """Music commands powered by yt-dlp and FFmpeg."""

    def __init__(self, bot: commands.Bot, manager: PlayerManager):
        self.bot = bot
        self.manager = manager
        self._check_empty_vc.start()

    def cog_unload(self):
        self._check_empty_vc.cancel()

    # ── Helpers ─────────────────────────────────────────────────────────────

    async def _ensure_voice(self, ctx: commands.Context) -> Optional[discord.VoiceClient]:
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(embed=embeds.error("You must be in a voice channel first."))
            return None
        vc: discord.VoiceClient = ctx.guild.voice_client  # type: ignore
        if vc and vc.channel != ctx.author.voice.channel:
            await ctx.send(embed=embeds.error("I'm already playing in a different voice channel."))
            return None
        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect()
            except Exception as exc:
                log.error("VC connect error: %s", exc)
                await ctx.send(embed=embeds.error("Could not connect to your voice channel."))
                return None
        return vc

    async def _reset_status(self):
        try:
            await self.bot.change_presence(activity=_IDLE_ACTIVITY)
        except Exception:
            pass

    # ── .play ───────────────────────────────────────────────────────────────

    @commands.command(name="play", aliases=["p"])
    @commands.guild_only()
    async def play(self, ctx: commands.Context, *, query: str):
        """Play a song or playlist from YouTube."""
        vc = await self._ensure_voice(ctx)
        if not vc:
            return

        player = self.manager.get(ctx.guild)
        player.text_channel = ctx.channel  # type: ignore
        player.bot_ref = self.bot          # give player a ref for presence updates
        player._cancel_auto_disconnect()

        async with ctx.typing():
            try:
                tracks = await YTDLSource.search_entries(query, loop=self.bot.loop)
            except Exception as exc:
                log.error("Search error: %s", exc)
                await ctx.send(embed=embeds.error(f"Could not find anything for: `{query}`"))
                return

        if not tracks:
            await ctx.send(embed=embeds.error("No results found. Try a different search."))
            return

        requestor = str(ctx.author.display_name)

        if len(tracks) > 1:
            added = 0
            for t in tracks:
                t["requestor"] = requestor
                try:
                    await player.add(t)
                    added += 1
                except OverflowError:
                    break
            await ctx.send(
                embed=embeds.playlist_added(tracks[0].get("title", "Playlist"), added, requestor)
            )
        else:
            track = tracks[0]
            track["requestor"] = requestor
            try:
                pos = await player.add(track)
            except OverflowError:
                await ctx.send(embed=embeds.error("The queue is full! (max 100 tracks)"))
                return
            # Only show enqueued card if something is already playing
            if vc.is_playing() or vc.is_paused():
                await ctx.send(embed=embeds.track_added(track, pos))

        await player.start()

    @app_commands.command(name="play", description="Play a song or playlist from YouTube")
    @app_commands.guild_only()
    async def slash_play(self, interaction: discord.Interaction, query: str):
        ctx = await commands.Context.from_interaction(interaction)
        await self.play(ctx, query=query)

    # ── .pause ──────────────────────────────────────────────────────────────

    @commands.command(name="pause")
    @commands.guild_only()
    async def pause(self, ctx: commands.Context):
        """Pause the current song."""
        player = self.manager.get_existing(ctx.guild)
        if not player or not player.pause():
            await ctx.send(embed=embeds.warning("Nothing is currently playing.", title="Warning"))
            return
        await ctx.send(embed=embeds.success(f"Paused. Use `{config.PREFIX}resume` to continue.", title="Paused"))

    @app_commands.command(name="pause", description="Pause the current song")
    @app_commands.guild_only()
    async def slash_pause(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.pause(ctx)

    # ── .resume ─────────────────────────────────────────────────────────────

    @commands.command(name="resume", aliases=["r"])
    @commands.guild_only()
    async def resume(self, ctx: commands.Context):
        """Resume a paused song."""
        player = self.manager.get_existing(ctx.guild)
        if not player or not player.resume():
            await ctx.send(embed=embeds.warning("Nothing is paused.", title="Warning"))
            return
        await ctx.send(embed=embeds.success("Resumed playback!", title="Resumed"))

    @app_commands.command(name="resume", description="Resume a paused song")
    @app_commands.guild_only()
    async def slash_resume(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.resume(ctx)

    # ── .skip ───────────────────────────────────────────────────────────────

    @commands.command(name="skip", aliases=["s"])
    @commands.guild_only()
    async def skip(self, ctx: commands.Context):
        """Skip the current song."""
        player = self.manager.get_existing(ctx.guild)
        if not player or not ctx.guild.voice_client:
            await ctx.send(embed=embeds.warning("Nothing is playing.", title="Warning"))
            return
        title = player.current_meta.get("title", "the current track") if player.current_meta else "the current track"
        player.skip()
        await ctx.send(embed=embeds.success(f"Skipped **{title}**.", title="Skipped ⏭"))

    @app_commands.command(name="skip", description="Skip the current song")
    @app_commands.guild_only()
    async def slash_skip(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.skip(ctx)

    # ── .stop ───────────────────────────────────────────────────────────────

    @commands.command(name="stop")
    @commands.guild_only()
    async def stop(self, ctx: commands.Context):
        """Stop playback and clear the queue."""
        player = self.manager.get_existing(ctx.guild)
        if player:
            player.stop()
        vc = ctx.guild.voice_client
        if vc:
            await vc.disconnect()
        self.manager.remove(ctx.guild)
        await self._reset_status()
        await ctx.send(embed=embeds.success("Stopped playback and cleared the queue. Goodbye! 👋", title="Stopped"))

    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    @app_commands.guild_only()
    async def slash_stop(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.stop(ctx)

    # ── .queue ──────────────────────────────────────────────────────────────

    @commands.command(name="queue", aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx: commands.Context, page: int = 1):
        """Show the music queue."""
        player = self.manager.get_existing(ctx.guild)
        tracks  = player.queue_list if player else []
        current = player.current_meta if player else None
        embed = embeds.queue_list(tracks, page=page, current=current)
        await ctx.send(embed=embed)

    @app_commands.command(name="queue", description="Show the music queue")
    @app_commands.guild_only()
    async def slash_queue(self, interaction: discord.Interaction, page: int = 1):
        ctx = await commands.Context.from_interaction(interaction)
        await self.queue(ctx, page=page)

    # ── .nowplaying ─────────────────────────────────────────────────────────

    @commands.command(name="nowplaying", aliases=["np"])
    @commands.guild_only()
    async def nowplaying(self, ctx: commands.Context):
        """Show information about the current song."""
        player = self.manager.get_existing(ctx.guild)
        if not player or not player.current_meta:
            await ctx.send(embed=embeds.warning("Nothing is currently playing.", title="Nothing Playing"))
            return
        position = player.current.position if player.current else 0.0
        embed = embeds.now_playing(
            player.current_meta,
            position=position,
            volume=player.volume,
            looping=player.looping,
            queue_size=player.queue_size(),
        )
        view = PlayerView(player)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="nowplaying", description="Show current song info")
    @app_commands.guild_only()
    async def slash_nowplaying(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.nowplaying(ctx)

    # ── .volume ─────────────────────────────────────────────────────────────

    @commands.command(name="volume", aliases=["vol"])
    @commands.guild_only()
    async def volume(self, ctx: commands.Context, vol: int):
        """Set playback volume (0–100)."""
        if not 0 <= vol <= 100:
            await ctx.send(embed=embeds.error("Volume must be between **0** and **100**."))
            return
        player = self.manager.get_existing(ctx.guild)
        if not player:
            await ctx.send(embed=embeds.warning("Nothing is playing.", title="Warning"))
            return
        player.set_volume(vol)
        filled = round(vol / 10)
        bar = "█" * filled + "░" * (10 - filled)
        await ctx.send(embed=embeds.success(f"Volume set to **{vol}%**\n`{bar}`", title="Volume"))

    @app_commands.command(name="volume", description="Set the playback volume (0–100)")
    @app_commands.guild_only()
    async def slash_volume(
        self,
        interaction: discord.Interaction,
        volume: app_commands.Range[int, 0, 100] = 50,
    ):
        ctx = await commands.Context.from_interaction(interaction)
        await self.volume(ctx, vol=volume)

    # ── .loop ───────────────────────────────────────────────────────────────

    @commands.command(name="loop", aliases=["l"])
    @commands.guild_only()
    async def loop(self, ctx: commands.Context):
        """Toggle song looping."""
        player = self.manager.get_existing(ctx.guild)
        if not player:
            await ctx.send(embed=embeds.warning("Nothing is playing.", title="Warning"))
            return
        player.looping = not player.looping
        state = "enabled 🔁" if player.looping else "disabled"
        await ctx.send(embed=embeds.success(f"Loop mode **{state}**.", title="Loop"))

    @app_commands.command(name="loop", description="Toggle song looping")
    @app_commands.guild_only()
    async def slash_loop(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.loop(ctx)

    # ── .shuffle ────────────────────────────────────────────────────────────

    @commands.command(name="shuffle")
    @commands.guild_only()
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the queue."""
        player = self.manager.get_existing(ctx.guild)
        if not player or player.queue_size() == 0:
            await ctx.send(embed=embeds.warning("The queue is empty.", title="Warning"))
            return
        player.shuffle()
        await ctx.send(
            embed=embeds.success(f"Shuffled **{player.queue_size()}** tracks! 🔀", title="Shuffled")
        )

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    @app_commands.guild_only()
    async def slash_shuffle(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.shuffle(ctx)

    # ── .leave ──────────────────────────────────────────────────────────────

    @commands.command(name="leave", aliases=["dc", "disconnect"])
    @commands.guild_only()
    async def leave(self, ctx: commands.Context):
        """Disconnect the bot from the voice channel."""
        vc = ctx.guild.voice_client
        if not vc:
            await ctx.send(embed=embeds.warning("I'm not in a voice channel.", title="Warning"))
            return
        player = self.manager.get_existing(ctx.guild)
        if player:
            player.stop()
        await vc.disconnect()
        self.manager.remove(ctx.guild)
        await self._reset_status()
        await ctx.send(embed=embeds.success("Disconnected. See you next time! 👋", title="Left"))

    @app_commands.command(name="leave", description="Disconnect Reverb from voice")
    @app_commands.guild_only()
    async def slash_leave(self, interaction: discord.Interaction):
        ctx = await commands.Context.from_interaction(interaction)
        await self.leave(ctx)

    # ── Auto-disconnect loop ────────────────────────────────────────────────

    @tasks.loop(seconds=30)
    async def _check_empty_vc(self):
        for guild in self.bot.guilds:
            vc = guild.voice_client
            if not vc or not vc.is_connected():
                continue
            members = [m for m in vc.channel.members if not m.bot]
            if members:
                continue
            player = self.manager.get_existing(guild)
            if not player or not (vc.is_playing() or vc.is_paused()):
                if player:
                    player.stop()
                await vc.disconnect()
                self.manager.remove(guild)
                await self._reset_status()
                log.info("Auto-disconnected from %s (empty VC)", guild.name)

    @_check_empty_vc.before_loop
    async def _before_check(self):
        await self.bot.wait_until_ready()

    # ── Voice state listener ────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        vc = member.guild.voice_client
        if not vc or not before.channel:
            return
        if before.channel != vc.channel:
            return
        remaining = [m for m in vc.channel.members if not m.bot]
        if not remaining:
            player = self.manager.get_existing(member.guild)
            if player:
                player.schedule_auto_disconnect()

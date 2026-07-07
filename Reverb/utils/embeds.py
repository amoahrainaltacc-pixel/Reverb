"""
Reverb Bot – Embed Builders
All Discord embed construction lives here to keep cogs clean.
"""
from __future__ import annotations

import datetime
from typing import Optional

import discord

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ─── Helpers ───────────────────────────────────────────────────────────────

def _base(color: int = config.BRAND_COLOR) -> discord.Embed:
    embed = discord.Embed(color=color)
    embed.set_footer(
        text="🎵 Reverb Music Bot",
        icon_url="https://cdn.discordapp.com/embed/avatars/0.png",
    )
    embed.timestamp = datetime.datetime.utcnow()
    return embed


def _progress_bar(current: float, total: float, length: int = 15) -> str:
    """Return a text progress bar string."""
    if total <= 0:
        return "▬" * length
    filled = int((current / total) * length)
    filled = min(filled, length)
    bar = "▬" * filled + "🔘" + "▬" * (length - filled)
    return bar


def _fmt_duration(seconds: float) -> str:
    """Format seconds → MM:SS or HH:MM:SS."""
    if seconds == 0:
        return "∞"
    seconds = int(seconds)
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ─── Public builders ───────────────────────────────────────────────────────

def now_playing(track: dict, position: float = 0.0, volume: int = 50, looping: bool = False) -> discord.Embed:
    """Embed for the currently-playing track."""
    embed = _base(config.BRAND_COLOR)
    embed.title = "🎵  Now Playing"
    embed.description = f"**[{track['title']}]({track['url']})**"

    duration = track.get("duration", 0)
    bar = _progress_bar(position, duration)
    time_display = f"`{_fmt_duration(position)} {bar} {_fmt_duration(duration)}`"
    embed.add_field(name="Progress", value=time_display, inline=False)

    embed.add_field(name="🎤 Uploader", value=track.get("uploader", "Unknown"), inline=True)
    embed.add_field(name="⏱ Duration", value=_fmt_duration(duration), inline=True)
    embed.add_field(name="🔊 Volume", value=f"{volume}%", inline=True)

    flags = []
    if looping:
        flags.append("🔁 Looping")
    if flags:
        embed.add_field(name="Flags", value=" · ".join(flags), inline=False)

    thumbnail = track.get("thumbnail")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    return embed


def track_added(track: dict, position: int) -> discord.Embed:
    """Embed shown when a track is added to the queue."""
    embed = _base(config.SUCCESS_COLOR)
    embed.title = "✅  Added to Queue"
    embed.description = f"**[{track['title']}]({track['url']})**"
    embed.add_field(name="⏱ Duration", value=_fmt_duration(track.get("duration", 0)), inline=True)
    embed.add_field(name="📋 Position", value=f"#{position}", inline=True)

    thumbnail = track.get("thumbnail")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed


def playlist_added(title: str, count: int) -> discord.Embed:
    embed = _base(config.SUCCESS_COLOR)
    embed.title = "📀  Playlist Added"
    embed.description = f"**{title}**"
    embed.add_field(name="Tracks", value=str(count), inline=True)
    return embed


def queue_list(tracks: list[dict], page: int = 1, per_page: int = 10, current: Optional[dict] = None) -> discord.Embed:
    """Paginated queue embed."""
    embed = _base(config.BRAND_COLOR)
    embed.title = "📋  Music Queue"

    if current:
        embed.add_field(
            name="▶️ Now Playing",
            value=f"**[{current['title']}]({current['url']})** `{_fmt_duration(current.get('duration', 0))}`",
            inline=False,
        )

    if not tracks:
        embed.add_field(name="Up Next", value="Queue is empty.", inline=False)
        return embed

    start = (page - 1) * per_page
    end = start + per_page
    slice_ = tracks[start:end]
    total_pages = (len(tracks) + per_page - 1) // per_page

    lines = []
    for i, t in enumerate(slice_, start=start + 1):
        dur = _fmt_duration(t.get("duration", 0))
        lines.append(f"`{i}.` **[{t['title']}]({t['url']})** · `{dur}`")

    embed.add_field(name=f"Up Next  (page {page}/{total_pages})", value="\n".join(lines) or "—", inline=False)

    total_dur = sum(t.get("duration", 0) for t in tracks)
    embed.set_footer(
        text=f"🎵 Reverb  ·  {len(tracks)} tracks  ·  {_fmt_duration(total_dur)} total"
    )
    return embed


def error(message: str, title: str = "❌  Error") -> discord.Embed:
    embed = _base(config.ERROR_COLOR)
    embed.title = title
    embed.description = message
    return embed


def success(message: str, title: str = "✅  Success") -> discord.Embed:
    embed = _base(config.SUCCESS_COLOR)
    embed.title = title
    embed.description = message
    return embed


def warning(message: str, title: str = "⚠️  Warning") -> discord.Embed:
    embed = _base(config.WARNING_COLOR)
    embed.title = title
    embed.description = message
    return embed


def help_embed(prefix: str) -> discord.Embed:
    embed = _base(config.BRAND_COLOR)
    embed.title = "🎵  Reverb — Help"
    embed.description = (
        "A high-quality music bot powered by YouTube. "
        "Use the commands below or the interactive buttons on the player.\n\u200b"
    )

    music_cmds = (
        f"`{prefix}play <song/url>` — Play a song or playlist\n"
        f"`{prefix}pause` — Pause playback\n"
        f"`{prefix}resume` — Resume playback\n"
        f"`{prefix}skip` — Skip the current song\n"
        f"`{prefix}stop` — Stop and clear queue\n"
        f"`{prefix}queue` — Show the queue\n"
        f"`{prefix}nowplaying` — Show current song\n"
        f"`{prefix}volume <0-100>` — Set volume\n"
        f"`{prefix}loop` — Toggle loop mode\n"
        f"`{prefix}shuffle` — Shuffle the queue\n"
        f"`{prefix}leave` — Disconnect bot"
    )
    embed.add_field(name="🎵  Music", value=music_cmds, inline=False)

    info_cmds = (
        f"`{prefix}help` — Show this menu\n"
        f"`{prefix}ping` — Bot latency\n"
        f"`{prefix}invite` — Invite Reverb to your server"
    )
    embed.add_field(name="⚙️  General", value=info_cmds, inline=False)

    embed.add_field(
        name="🎮  Player Controls",
        value="Interactive ▶️ ⏸ ⏭ 🔁 ⏹ buttons appear on the now-playing card.",
        inline=False,
    )
    embed.set_footer(text=f"Prefix: {prefix}  ·  🎵 Reverb Music Bot")
    return embed

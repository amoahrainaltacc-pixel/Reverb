"""
Reverb Bot – Embed Builders
All Discord embed construction lives here to keep cogs clean.
"""
from __future__ import annotations

import datetime
from typing import Optional

import discord

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


# ─── Internal helpers ──────────────────────────────────────────────────────

def _base(color: int = config.BRAND_COLOR) -> discord.Embed:
    embed = discord.Embed(color=color)
    embed.timestamp = datetime.datetime.utcnow()
    return embed


def _fmt_duration(seconds: float) -> str:
    """Format seconds → M:SS or H:MM:SS for inline display."""
    if not seconds:
        return "∞"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _fmt_duration_long(seconds: float) -> str:
    """Format seconds → 03m 33s style (used in footers, matching screenshot)."""
    if not seconds:
        return "∞"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"


def _progress_bar(current: float, total: float, length: int = 17) -> str:
    if total <= 0:
        return "━" * length
    filled = int((current / total) * length)
    filled = min(filled, length - 1)
    return "━" * filled + "🔘" + "━" * (length - filled - 1)


# ─── Public builders ───────────────────────────────────────────────────────

def now_playing(
    track: dict,
    position: float = 0.0,
    volume: int = 50,
    looping: bool = False,
    queue_size: int = 0,
) -> discord.Embed:
    """Rich now-playing card with progress bar and metadata."""
    embed = _base(config.NP_COLOR)
    embed.title = "Now Playing"

    title  = track.get("title", "Unknown")
    url    = track.get("url", "")
    embed.description = f"### [{title}]({url})"

    duration = track.get("duration", 0)
    bar = _progress_bar(position, duration)
    embed.add_field(
        name="\u200b",
        value=f"`{_fmt_duration(position)}` {bar} `{_fmt_duration(duration)}`",
        inline=False,
    )

    # Metadata row
    uploader  = track.get("uploader", "Unknown")
    requestor = track.get("requestor", "Unknown")
    embed.add_field(name="🎤  Artist", value=f"`{uploader}`", inline=True)
    embed.add_field(name="👤  Requested by", value=f"`{requestor}`", inline=True)
    embed.add_field(name="🔊  Volume", value=f"`{volume}%`", inline=True)

    # Status row
    loop_val = "🔁  On" if looping else "➡️  Off"
    next_val = f"`{queue_size} track{'s' if queue_size != 1 else ''} in queue`"
    embed.add_field(name="🔄  Loop", value=loop_val, inline=True)
    embed.add_field(name="📋  Up next", value=next_val, inline=True)
    embed.add_field(name="⏱  Duration", value=f"`{_fmt_duration(duration)}`", inline=True)

    thumbnail = track.get("thumbnail")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    embed.set_footer(text="Reverb Music  •  Use the buttons below to control playback")
    return embed


def track_added(track: dict, position: int) -> discord.Embed:
    """Enqueued-track card — matches the screenshot style exactly."""
    embed = _base(config.SUCCESS_COLOR)
    embed.title = "Enqueued Track"

    title = track.get("title", "Unknown")
    url   = track.get("url", "")
    embed.description = (
        f"{config.EMOJI_SUCCESS} Added **[{title}]({url})** to the queue."
    )

    # Thumbnail on the right
    thumbnail = track.get("thumbnail")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    dur       = _fmt_duration_long(track.get("duration", 0))
    requestor = track.get("requestor", "Unknown")
    embed.set_footer(text=f"Duration : {dur}  •  Requestor : {requestor}  •  Position : {position}")
    return embed


def playlist_added(title: str, count: int, requestor: str = "Unknown") -> discord.Embed:
    embed = _base(config.SUCCESS_COLOR)
    embed.title = "Playlist Enqueued"
    embed.description = (
        f"{config.EMOJI_SUCCESS} Added **{count}** tracks from **{title}** to the queue."
    )
    embed.set_footer(text=f"Requestor : {requestor}  •  {count} tracks added")
    return embed


def queue_list(
    tracks: list[dict],
    page: int = 1,
    per_page: int = 10,
    current: Optional[dict] = None,
) -> discord.Embed:
    embed = _base(config.BRAND_COLOR)
    embed.title = "Music Queue"

    if current:
        dur = _fmt_duration(current.get("duration", 0))
        req = current.get("requestor", "Unknown")
        embed.add_field(
            name="▶️  Now Playing",
            value=(
                f"**[{current['title']}]({current['url']})**\n"
                f"⏱ `{dur}`  •  👤 `{req}`"
            ),
            inline=False,
        )

    if not tracks:
        embed.add_field(
            name="📭  Up Next",
            value="The queue is empty. Use `.play` to add songs!",
            inline=False,
        )
        embed.set_footer(text="Reverb Music  •  Queue is empty")
        return embed

    start = (page - 1) * per_page
    total_pages = max(1, (len(tracks) + per_page - 1) // per_page)
    page = min(page, total_pages)

    lines = []
    for i, t in enumerate(tracks[start : start + per_page], start=start + 1):
        dur = _fmt_duration(t.get("duration", 0))
        req = t.get("requestor", "")
        req_str = f"  •  👤 `{req}`" if req else ""
        lines.append(f"`{i}.` **[{t['title']}]({t['url']})** — `{dur}`{req_str}")

    embed.add_field(
        name=f"📋  Up Next  (page {page}/{total_pages})",
        value="\n".join(lines),
        inline=False,
    )

    total_dur = sum(t.get("duration", 0) for t in tracks)
    embed.set_footer(
        text=f"Reverb Music  •  {len(tracks)} track{'s' if len(tracks) != 1 else ''}  •  {_fmt_duration_long(total_dur)} total  •  Page {page}/{total_pages}"
    )
    return embed


def error(message: str, title: str = "Error") -> discord.Embed:
    embed = _base(config.ERROR_COLOR)
    embed.title = f"{config.EMOJI_ERROR}  {title}"
    embed.description = message
    return embed


def success(message: str, title: str = "Success") -> discord.Embed:
    embed = _base(config.SUCCESS_COLOR)
    embed.title = f"{config.EMOJI_SUCCESS}  {title}"
    embed.description = message
    return embed


def warning(message: str, title: str = "Warning") -> discord.Embed:
    embed = _base(config.WARNING_COLOR)
    embed.title = f"⚠️  {title}"
    embed.description = message
    return embed


def info(message: str, title: str = "Info") -> discord.Embed:
    embed = _base(config.INFO_COLOR)
    embed.title = f"{config.EMOJI_INFO}  {title}"
    embed.description = message
    return embed


def help_embed(prefix: str, bot_avatar: Optional[str] = None) -> discord.Embed:
    embed = _base(config.BRAND_COLOR)
    embed.title = "Reverb — Command Reference"
    embed.description = (
        f"> A premium music bot that streams from YouTube with a beautiful player, "
        f"interactive controls, and rich queue management.\n\u200b"
    )

    music_cmds = (
        f"`{prefix}play <song/url>` — Stream a song or playlist\n"
        f"`{prefix}pause` — Pause playback\n"
        f"`{prefix}resume` — Resume playback\n"
        f"`{prefix}skip` — Skip the current song\n"
        f"`{prefix}stop` — Stop & clear the queue\n"
        f"`{prefix}queue` — View the queue\n"
        f"`{prefix}nowplaying` — Current song info\n"
        f"`{prefix}volume <0–100>` — Set volume\n"
        f"`{prefix}loop` — Toggle loop mode\n"
        f"`{prefix}shuffle` — Shuffle the queue\n"
        f"`{prefix}leave` — Disconnect Reverb"
    )
    embed.add_field(name="🎵  Music Commands", value=music_cmds, inline=True)

    info_cmds = (
        f"`{prefix}help` — Show this menu\n"
        f"`{prefix}ping` — Check latency\n"
        f"`{prefix}botinfo` — About Reverb\n"
        f"`{prefix}invite` — Get invite link"
    )
    embed.add_field(name="⚙️  General", value=info_cmds, inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    embed.add_field(
        name="🎮  Interactive Controls",
        value=(
            "Every now-playing card has live buttons:\n"
            "▶️ **Resume**  ·  ⏸ **Pause**  ·  ⏭ **Skip**  ·  🔁 **Loop**  ·  ⏹ **Stop**"
        ),
        inline=False,
    )
    embed.add_field(
        name=f"{config.EMOJI_INFO}  Slash Commands",
        value="All commands are also available as `/slash` commands.",
        inline=False,
    )

    if bot_avatar:
        embed.set_thumbnail(url=bot_avatar)

    embed.set_footer(text=f"Prefix: {prefix}  •  Reverb Music Bot  •  Powered by YouTube")
    return embed


def welcome(guild_name: str, prefix: str) -> discord.Embed:
    """Sent when the bot joins a new server."""
    embed = _base(config.BRAND_COLOR)
    embed.title = f"{config.EMOJI_MUSIC}  Hey there! I'm Reverb."
    embed.description = (
        f"Thanks for inviting me to **{guild_name}**! "
        f"I'm a premium music bot that streams high-quality audio straight from YouTube.\n\n"
        f"Get the party started with `{prefix}play <song>` or see all commands with `{prefix}help`."
    )
    embed.add_field(
        name="🚀  Quick Start",
        value=(
            f"`{prefix}play Never Gonna Give You Up`\n"
            f"`{prefix}play https://youtube.com/...` — direct URL\n"
            f"`{prefix}help` — full command list"
        ),
        inline=False,
    )
    embed.add_field(
        name="🎮  Controls",
        value="Interactive ▶️ ⏸ ⏭ 🔁 ⏹ buttons appear on every now-playing card.",
        inline=False,
    )
    embed.set_footer(text="Reverb Music  •  Enjoy the music!")
    return embed

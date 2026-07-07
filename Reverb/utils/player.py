"""
Reverb Bot – Music Player & Queue Manager
Handles all playback state, queue logic, and yt-dlp extraction.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import random
import time
from typing import Optional

import discord
import yt_dlp

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

log = logging.getLogger("reverb.player")


# ─── YTDLSource ────────────────────────────────────────────────────────────

class YTDLSource(discord.PCMVolumeTransformer):
    """A discord audio source backed by yt-dlp + FFmpeg."""

    def __init__(self, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume=volume)
        self.data = data
        self.title: str = data.get("title", "Unknown")
        self.url: str = data.get("webpage_url", data.get("url", ""))
        self.thumbnail: Optional[str] = data.get("thumbnail")
        self.duration: float = float(data.get("duration") or 0)
        self.uploader: str = data.get("uploader") or data.get("channel", "Unknown")
        self.start_time: float = time.time()

    @property
    def position(self) -> float:
        return time.time() - self.start_time

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "duration": self.duration,
            "uploader": self.uploader,
        }

    @classmethod
    async def from_url(
        cls,
        url: str,
        *,
        loop: asyncio.AbstractEventLoop,
        volume: float = 0.5,
        stream: bool = True,
    ) -> "YTDLSource":
        """Resolve a URL (or search query) into a single playable source."""
        ydl_opts = copy.deepcopy(config.YTDL_FORMAT_OPTIONS)
        ydl_opts["noplaylist"] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = await loop.run_in_executor(
                None, lambda: ydl.extract_info(url, download=not stream)
            )

        if "entries" in data:
            data = data["entries"][0]

        stream_url = data.get("url") if stream else ydl.prepare_filename(data)

        ffmpeg_opts = copy.deepcopy(config.FFMPEG_OPTIONS)
        # Inject volume into ffmpeg filter
        ffmpeg_opts["options"] = f"-vn -filter:a volume={volume}"

        source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
        return cls(source, data=data, volume=volume)

    @classmethod
    async def search_entries(
        cls,
        query: str,
        *,
        loop: asyncio.AbstractEventLoop,
    ) -> list[dict]:
        """Return a list of track dicts from a search query or playlist URL."""
        ydl_opts = copy.deepcopy(config.YTDL_FORMAT_OPTIONS)
        ydl_opts["noplaylist"] = False
        ydl_opts["extract_flat"] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = await loop.run_in_executor(
                None, lambda: ydl.extract_info(query, download=False)
            )

        if "entries" in data:
            return [
                {
                    "title": e.get("title", "Unknown"),
                    "url": e.get("url") or e.get("webpage_url", ""),
                    "thumbnail": e.get("thumbnail"),
                    "duration": float(e.get("duration") or 0),
                    "uploader": e.get("uploader") or e.get("channel", "Unknown"),
                }
                for e in data["entries"]
                if e
            ]

        return [
            {
                "title": data.get("title", "Unknown"),
                "url": data.get("webpage_url", data.get("url", "")),
                "thumbnail": data.get("thumbnail"),
                "duration": float(data.get("duration") or 0),
                "uploader": data.get("uploader") or data.get("channel", "Unknown"),
            }
        ]


# ─── GuildPlayer ───────────────────────────────────────────────────────────

class GuildPlayer:
    """Per-guild music player: owns the queue, loop flag, volume, etc."""

    def __init__(self, guild: discord.Guild, bot: discord.Client):
        self.guild = guild
        self.bot = bot

        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=config.MAX_QUEUE_SIZE)
        self._pending: list[dict] = []   # snapshot list for display / shuffle
        self.current: Optional[YTDLSource] = None
        self.current_meta: Optional[dict] = None

        self.volume: int = config.DEFAULT_VOLUME
        self.looping: bool = False
        self._play_next_event = asyncio.Event()
        self._auto_dc_task: Optional[asyncio.Task] = None
        self._player_task: Optional[asyncio.Task] = None

        self.text_channel: Optional[discord.TextChannel] = None
        self.np_message: Optional[discord.Message] = None

    # ── Queue helpers ───────────────────────────────────────────────────────

    @property
    def queue_list(self) -> list[dict]:
        return list(self._pending)

    def queue_size(self) -> int:
        return len(self._pending)

    async def add(self, track: dict) -> int:
        """Add a track dict to the queue. Returns 1-based position."""
        if self._queue.full():
            raise OverflowError("Queue is full.")
        await self._queue.put(track)
        self._pending.append(track)
        return len(self._pending)

    def shuffle(self) -> None:
        """Shuffle pending tracks (does not affect currently-playing)."""
        random.shuffle(self._pending)
        # Rebuild the asyncio.Queue from the shuffled list
        new_q: asyncio.Queue[dict] = asyncio.Queue(maxsize=config.MAX_QUEUE_SIZE)
        for t in self._pending:
            new_q.put_nowait(t)
        self._queue = new_q

    def clear(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._pending.clear()

    # ── Playback ────────────────────────────────────────────────────────────

    def _after_play(self, error: Optional[Exception]) -> None:
        if error:
            log.error("Playback error: %s", error)
        self.bot.loop.call_soon_threadsafe(self._play_next_event.set)

    async def _player_loop(self) -> None:
        """Main player loop – runs for the lifetime of the bot's vc connection."""
        await self.bot.wait_until_ready()
        self._play_next_event.clear()

        while True:
            self._play_next_event.clear()

            if self.looping and self.current_meta:
                track = self.current_meta
            else:
                try:
                    track = await asyncio.wait_for(self._queue.get(), timeout=180)
                    # Remove from pending mirror
                    if track in self._pending:
                        self._pending.remove(track)
                except asyncio.TimeoutError:
                    await self._idle_disconnect()
                    return

            self.current_meta = track

            try:
                source = await YTDLSource.from_url(
                    track["url"],
                    loop=self.bot.loop,
                    volume=self.volume / 100,
                )
            except Exception as exc:
                log.error("Failed to load track %s: %s", track.get("title"), exc)
                if self.text_channel:
                    from utils.embeds import error as err_embed
                    await self.text_channel.send(
                        embed=err_embed(f"Could not load **{track.get('title', 'Unknown')}**. Skipping."),
                        delete_after=10,
                    )
                continue

            self.current = source
            vc = self.guild.voice_client
            if not vc or not vc.is_connected():
                return

            vc.play(source, after=self._after_play)

            if self.text_channel:
                await self._send_np_card()

            await self._play_next_event.wait()
            self.current = None

            # Clean up old now-playing message
            if self.np_message:
                try:
                    await self.np_message.delete()
                except Exception:
                    pass
                self.np_message = None

    async def start(self) -> None:
        if self._player_task and not self._player_task.done():
            return
        self._player_task = self.bot.loop.create_task(self._player_loop())

    def stop(self) -> None:
        if self._player_task:
            self._player_task.cancel()
        self.clear()
        self.current = None
        self.current_meta = None
        vc = self.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()

    def skip(self) -> None:
        vc = self.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()

    def pause(self) -> bool:
        vc = self.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            return True
        return False

    def resume(self) -> bool:
        vc = self.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            return True
        return False

    def set_volume(self, vol: int) -> None:
        self.volume = vol
        if self.current:
            self.current.volume = vol / 100

    # ── Now-playing card ────────────────────────────────────────────────────

    async def _send_np_card(self) -> None:
        if not self.text_channel or not self.current_meta:
            return
        from utils.embeds import now_playing as np_embed
        from cogs.music import PlayerView
        embed = np_embed(
            self.current_meta,
            position=0,
            volume=self.volume,
            looping=self.looping,
        )
        view = PlayerView(self)
        try:
            self.np_message = await self.text_channel.send(embed=embed, view=view)
        except Exception as exc:
            log.warning("Could not send NP card: %s", exc)

    # ── Auto-disconnect ─────────────────────────────────────────────────────

    async def _idle_disconnect(self) -> None:
        vc = self.guild.voice_client
        if vc and vc.is_connected():
            await vc.disconnect()
        if self.text_channel:
            from utils.embeds import warning as warn_embed
            await self.text_channel.send(
                embed=warn_embed("Left the voice channel due to inactivity.", title="💤  Idle"),
                delete_after=15,
            )

    def schedule_auto_disconnect(self, delay: int = config.AUTO_DISCONNECT_DELAY) -> None:
        self._cancel_auto_disconnect()
        self._auto_dc_task = self.bot.loop.create_task(self._auto_disconnect_after(delay))

    def _cancel_auto_disconnect(self) -> None:
        if self._auto_dc_task and not self._auto_dc_task.done():
            self._auto_dc_task.cancel()

    async def _auto_disconnect_after(self, delay: int) -> None:
        await asyncio.sleep(delay)
        vc = self.guild.voice_client
        if vc and vc.is_connected():
            members = [m for m in vc.channel.members if not m.bot]
            if not members:
                await vc.disconnect()
                if self.text_channel:
                    from utils.embeds import warning as warn_embed
                    await self.text_channel.send(
                        embed=warn_embed(
                            "Everyone left the voice channel. Disconnected.",
                            title="💤  Auto-Disconnect",
                        ),
                        delete_after=15,
                    )


# ─── PlayerManager ─────────────────────────────────────────────────────────

class PlayerManager:
    """Holds one GuildPlayer per guild; creates on demand."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self._players: dict[int, GuildPlayer] = {}

    def get(self, guild: discord.Guild) -> GuildPlayer:
        if guild.id not in self._players:
            self._players[guild.id] = GuildPlayer(guild, self.bot)
        return self._players[guild.id]

    def remove(self, guild: discord.Guild) -> None:
        player = self._players.pop(guild.id, None)
        if player:
            player.stop()

    def get_existing(self, guild: discord.Guild) -> Optional[GuildPlayer]:
        return self._players.get(guild.id)

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  Reverb Bot – Configuration
# ─────────────────────────────────────────────

# Bot token – set via environment variable or .env file
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Command prefix
PREFIX: str = os.getenv("PREFIX", ".")

# Owner Discord user ID (int)
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))

# Embed brand colour (hex → int)
BRAND_COLOR: int = 0x7289DA   # Discord Blurple
SUCCESS_COLOR: int = 0x57F287  # Green
ERROR_COLOR: int = 0xED4245    # Red
WARNING_COLOR: int = 0xFEE75C  # Yellow

# Auto-disconnect delay (seconds) after voice channel is empty
AUTO_DISCONNECT_DELAY: int = int(os.getenv("AUTO_DISCONNECT_DELAY", "300"))

# Maximum queue size
MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "100"))

# Default volume (0–100)
DEFAULT_VOLUME: int = int(os.getenv("DEFAULT_VOLUME", "50"))

# yt-dlp options
YTDL_FORMAT_OPTIONS: dict = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": "in_playlist",
    "socket_timeout": 30,
}

# FFmpeg audio options
FFMPEG_OPTIONS: dict = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    ),
    "options": "-vn -filter:a volume=0.5",
}

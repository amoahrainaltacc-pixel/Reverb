import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  Reverb Bot – Configuration
# ─────────────────────────────────────────────

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
PREFIX: str = os.getenv("PREFIX", ".")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))

# ── Colours ────────────────────────────────────────────────────────────────
BRAND_COLOR:   int = 0x1DB954   # Spotify green  – primary accent
SUCCESS_COLOR: int = 0x1DB954   # same green for queue-add / success
ERROR_COLOR:   int = 0xED4245   # Discord red
WARNING_COLOR: int = 0xFEE75C   # Discord yellow
INFO_COLOR:    int = 0x5865F2   # Discord blurple
NP_COLOR:      int = 0x1DB954   # Now-playing green

# ── Custom server emojis ───────────────────────────────────────────────────
EMOJI_ERROR:      str = "<:XE:1524120772396712157>"           # ❌ fail / X
EMOJI_SUCCESS:    str = "<:THESWE:1524120674157858826>"       # ✅ enqueued / added
EMOJI_MUSIC:      str = "<:bear_music:1524121341349990541>"   # 🐻 welcome
EMOJI_INFO:       str = "<:info:1523416103206916297>"         # ℹ️  info

# ── Behaviour ──────────────────────────────────────────────────────────────
AUTO_DISCONNECT_DELAY: int = int(os.getenv("AUTO_DISCONNECT_DELAY", "300"))
MAX_QUEUE_SIZE:        int = int(os.getenv("MAX_QUEUE_SIZE", "100"))
DEFAULT_VOLUME:        int = int(os.getenv("DEFAULT_VOLUME", "50"))

# ── yt-dlp ─────────────────────────────────────────────────────────────────
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

# ── FFmpeg ──────────────────────────────────────────────────────────────────
FFMPEG_OPTIONS: dict = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -filter:a volume=0.5",
}

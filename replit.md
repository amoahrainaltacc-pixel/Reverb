# Reverb

A professional Discord music bot that streams high-quality audio from YouTube with interactive player controls, a paginated queue, slash commands, and beautiful branded embeds.

## Run & Operate

- **Workflow**: `Reverb Bot` — `cd Reverb && python3 main.py`
- **Install deps**: Use Replit package manager (packages declared in `Reverb/requirements.txt`; managed via `uv` into `.pythonlibs`)
- Required secret: `BOT_TOKEN` — Discord bot token (set via Replit Secrets)

## Stack

- Python 3.13 + discord.py 2.3.2
- yt-dlp for YouTube audio extraction
- FFmpeg (system) for audio playback
- asyncio for non-blocking queue management
- PyNaCl for Discord voice encryption
- audioop-lts (Python 3.13 compatibility shim for discord.py voice)

## Where things live

```
Reverb/
├── main.py           # Bot entry point, Reverb class, lifecycle hooks
├── config.py         # All config from env vars (.env or Replit Secrets)
├── requirements.txt  # Python dependencies
├── .env.example      # Template — copy to .env for local dev
├── cogs/
│   ├── music.py      # Music commands + PlayerView button row
│   └── commands.py   # General commands + global error handler
└── utils/
    ├── embeds.py     # All Discord embed builders
    └── player.py     # YTDLSource, GuildPlayer, PlayerManager
```

## Architecture decisions

- **PlayerManager**: one `GuildPlayer` instance per guild, created on demand, destroyed on disconnect. Keeps all playback state isolated per server.
- **asyncio.Queue + _pending list**: `asyncio.Queue` drives the player loop; `_pending` is a mirror list used for display and shuffle (asyncio.Queue has no random-access).
- **audioop-lts**: discord.py's voice client depends on `audioop` which was removed in Python 3.13. The `audioop-lts` shim restores it without downgrading Python.
- **Prefix + slash commands**: Both `.command` and `app_commands.command` decorators are used; slash commands delegate to their prefix counterpart via `Context.from_interaction` to avoid duplicate logic.
- **YTDLSource**: extends `PCMVolumeTransformer` so per-track volume can be set without restarting the stream.

## Product

- `.play <song/url>` — stream from YouTube (single track or playlist)
- Interactive ▶️ ⏸ ⏭ 🔁 ⏹ buttons on each now-playing card
- Queue management: add, skip, shuffle, loop, clear
- Volume control per guild
- Auto-disconnect when voice channel is empty
- Rich branded embeds with thumbnails, progress bars, duration display
- All commands available as both prefix (`.`) and slash (`/`) commands

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- **audioop-lts required on Python 3.13+**: `audioop` was removed from stdlib; always keep `audioop-lts` in requirements.
- **Do not run `python main.py` from workspace root** — run it from inside `Reverb/` or use `cd Reverb && python3 main.py` so relative imports resolve correctly.
- **Slash command sync delay**: Global slash commands can take up to 1 hour to appear in all servers after first sync. For instant sync during dev, use guild-specific sync.
- **FFmpeg must be in PATH**: Replit provides it at `/nix/store/.../ffmpeg`; no manual install needed.

## Pointers

- See `Reverb/README.md` for full setup guide and hosting instructions (Railway, Replit, VPS)
- Discord Developer Portal: https://discord.com/developers/applications

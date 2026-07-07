# 🎵 Reverb — Discord Music Bot

A professional, production-ready Discord music bot powered by **discord.py 2.x**, **yt-dlp**, and **FFmpeg**.

---

## ✨ Features

| Category | Details |
|---|---|
| **Music** | Play, Pause, Resume, Skip, Stop, Queue, Now Playing |
| **Controls** | Interactive ▶️ ⏸ ⏭ 🔁 ⏹ buttons on the player card |
| **Queue** | Paginated queue, Shuffle, Loop mode |
| **Volume** | Per-guild volume control (0–100) |
| **Auto DC** | Leaves VC automatically when everyone else leaves |
| **Slash cmds** | Full `/command` slash command support alongside prefix |
| **Embeds** | Branded embeds with thumbnails, progress bars, duration |

---

## 📂 Project Structure

```
Reverb/
├── main.py           # Bot entry point
├── config.py         # Configuration (reads from .env)
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
├── cogs/
│   ├── music.py      # All music commands + button view
│   └── commands.py   # General commands (help, ping, invite, botinfo)
└── utils/
    ├── embeds.py     # Embed builders (now-playing, queue, error, etc.)
    └── player.py     # YTDLSource, GuildPlayer, PlayerManager
```

---

## 🚀 Setup

### 1. Prerequisites

- Python 3.10+
- FFmpeg installed and available in `PATH`
  - **Replit**: `nix-env -iA nixpkgs.ffmpeg` or add `ffmpeg` to `replit.nix`
  - **Ubuntu/Debian**: `sudo apt install ffmpeg`
  - **macOS**: `brew install ffmpeg`
  - **Railway**: add `NIXPACKS_PKGS=ffmpeg` env var

### 2. Install dependencies

```bash
cd Reverb
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and set BOT_TOKEN, PREFIX, OWNER_ID
```

### 4. Run

```bash
python main.py
```

---

## ⚙️ Commands

### 🎵 Music

| Command | Description |
|---|---|
| `.play <song/url>` | Play a song or YouTube playlist |
| `.pause` | Pause playback |
| `.resume` | Resume playback |
| `.skip` | Skip current song |
| `.stop` | Stop and clear queue |
| `.queue [page]` | Show the music queue |
| `.nowplaying` | Show current song with progress |
| `.volume <0-100>` | Set volume |
| `.loop` | Toggle song looping |
| `.shuffle` | Shuffle the queue |
| `.leave` | Disconnect the bot |

### ⚙️ General

| Command | Description |
|---|---|
| `.help` | Show full help menu |
| `.ping` | Bot latency |
| `.invite` | Get invite link |
| `.botinfo` | Show bot info |

All commands are also available as `/slash` commands.

---

## 🌐 Hosting

### Replit
1. Add `BOT_TOKEN` to **Secrets** (padlock icon)
2. Add FFmpeg: in `.replit` or Nix config  
3. Set run command: `cd Reverb && python main.py`

### Railway
1. Set `BOT_TOKEN`, `PREFIX`, `OWNER_ID` as environment variables
2. Add `NIXPACKS_PKGS=ffmpeg` env var for FFmpeg
3. Start command: `python Reverb/main.py`

### VPS (Ubuntu)
```bash
sudo apt install ffmpeg python3-pip
pip3 install -r Reverb/requirements.txt
python3 Reverb/main.py
# Or with systemd / pm2 for process management
```

---

## 🔧 Discord Developer Portal Setup

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create **New Application** → name it **Reverb**
3. Go to **Bot** → create a bot, copy the token
4. Enable **Message Content Intent** and **Server Members Intent**
5. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Connect`, `Speak`, `Use Voice Activity`
6. Open the generated URL to invite Reverb to your server

---

## 📝 License

MIT — free to use and modify.

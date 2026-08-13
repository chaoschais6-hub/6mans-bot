# 6mans Discord Bot

A Discord bot for running **6mans** (6-player, 3v3) competitive queues with automatic
team balancing and MMR tracking.

## Commands

| Command | Description |
| --- | --- |
| `/queue join` | Join the queue (auto-starts a match at 6 players) |
| `/queue leave` | Leave the queue |
| `/queue status` | Show who's currently queued |
| `/result <my_score> <opp_score>` | Report your team's match result |
| `/active` | List all pending matches in the server |
| `/mmr` | Show your MMR and win/loss record |
| `/leaderboard` | Top 10 players by MMR |
| `/pingrole <role>` | Set a role to ping when matches start (Manage Roles) |
| `/clear_pingrole` | Remove the match ping role (Manage Roles) |

## How it works

1. Players `/queue join`. Once **6 players** are in, the bot forms a match.
2. Players are split into 2 teams of 3 to **minimize the MMR gap** between teams.
3. The winning team reports the score with `/result`.
4. **ELO is applied** (K-factor 32): each player gains/loses rating based on their
   rating vs. the opposing team's average rating.
5. New players start at **1000 MMR**.

## Local run (optional)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (or `source .venv/bin/activate` on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env          # then edit DISCORD_TOKEN
python bot.py
```

For instant slash-command sync while developing, also set `GUILD_ID` in `.env`.

## Running in the cloud (not on your PC)

### Option 1: Fly.io (recommended — free tier + persistent disk)

1. Create a bot token:
   - Go to <https://discord.com/developers/applications> → **New Application**.
   - **Bot** → **Reset Token** → copy it.
   - **OAuth2 → URL Generator**: check `bot` and `applications.commands` scopes,
     grant *Send Messages* / *Read Messages / View Channels*, then open the URL to
     invite the bot to your server.
2. Install the Fly CLI (<https://fly.io/docs/hands-on/install-fly-ctl/>) and log in:
   ```bash
   fly auth login
   ```
3. From the `6mans-bot` folder:
   ```bash
   fly apps create sixmans-bot
   fly secrets set DISCORD_TOKEN=your-token-here
   fly volumes create sixmans_data --size 1 --region iad
   fly deploy
   ```
4. Check logs with `fly logs`. The bot's SQLite data lives on the persistent volume.

### Option 2: Render (free)

1. Push this folder to a GitHub repo.
2. On Render → **New → Background Worker**, connect the repo.
3. Set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python bot.py`
   - Environment variable: `DISCORD_TOKEN`
   - **Important:** the free worker's disk is ephemeral — MMR data is lost on
     redeploys/restarts. Use a paid instance or the Fly.io option above for
     persistent data.

### Option 3: Railway

1. Create a project, deploy this repo, add the `DISCORD_TOKEN` variable.
2. Add a **Volume** mounted at `/data` for persistent storage.

## Project structure

```
bot.py          entry point
config.py       env config (token, data dir)
database.py     SQLite layer (players, matches, settings)
elo.py          ELO rating math
balancing.py    3v3 team balancing
cogs/           slash-command modules (queue, matches, mmr, settings)
Dockerfile      container image for cloud deploy
fly.toml        Fly.io config (persistent volume)
```

## Notes

- The queue lives in memory, so a bot restart clears it (matches/MMR persist in SQLite).
- Ties are not supported by `/result`; the winning team reports.
- Anyone who was in the match can report its result (first report wins, then it's locked).

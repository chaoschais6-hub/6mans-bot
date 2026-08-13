import os

TOKEN = os.environ.get("DISCORD_TOKEN", "")

# Optional: if set, slash commands sync instantly for this guild (handy while developing)
GUILD_ID = os.environ.get("GUILD_ID", "")
if GUILD_ID:
    GUILD_ID = int(GUILD_ID)

DATA_DIR = os.environ.get("DATA_DIR", "data")
DB_PATH = os.path.join(DATA_DIR, "sixmans.db")

RL_TRACKER_API_KEY = os.environ.get("RL_TRACKER_API_KEY", "")

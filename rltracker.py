import json
import urllib.error
import urllib.parse
import urllib.request

import config

PLATFORMS = ["epic", "steam", "xbl", "psn"]

# Parse.bot "RL Tracker Network API" — managed wrapper over
# rocketleague.tracker.network. Free tier: 200 credits/month, 1 credit per
# profile lookup.
PROFILE_URL = (
    "https://api.parse.bot/scraper/"
    "d0dcf8e8-3a72-4b21-bffb-8fa735257835/get_player_profile"
)

# 3s rating counts 1.25x vs 2s; pick whichever scoring is higher.
TRIPLES_MULTIPLIER = 1.25


class RLTrackerError(Exception):
    pass


class NoApiKeyError(RLTrackerError):
    pass


class PlayerNotFoundError(RLTrackerError):
    pass


def _find_rating(segments, *name_fragments):
    """Return the first rating value from a playlist segment matching a name.

    Parse.bot returns a `segments` array with a per-playlist entry for the
    current season. Each segment has `metadata.name` (e.g. "Ranked Doubles
    2v2", "Ranked Standard 3v3") and `stats.rating.value`.
    """
    for seg in segments:
        meta = seg.get("metadata") or {}
        name = (meta.get("name") or "").lower()
        if all(frag in name for frag in name_fragments):
            stats = seg.get("stats") or {}
            rating = stats.get("rating") or {}
            value = rating.get("value")
            if value is not None:
                return int(value)
    return None


def fetch_rank(platform, username):
    """Fetch a player's current-season 2v2 and 3v3 ratings.

    Returns a dict: {platform, username, twos, threes, rating, error}
    `rating` is the effective score = max(twos, threes * 1.25).
    """
    if platform not in PLATFORMS:
        raise RLTrackerError(
            f"Platform must be one of: {', '.join(PLATFORMS)}"
        )

    if not config.RL_TRACKER_API_KEY:
        raise NoApiKeyError(
            "No RL tracker API key configured. Set RL_TRACKER_API_KEY."
        )

    url = f"{PROFILE_URL}?platform={platform}&username={urllib.parse.quote(username)}"
    request = urllib.request.Request(
        url,
        headers={
            "X-API-Key": config.RL_TRACKER_API_KEY,
            "Accept": "application/json",
            "User-Agent": "6mans-bot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise PlayerNotFoundError(
                f"No RL Tracker profile found for `{username}` ({platform})."
            )
        if e.code == 429:
            raise RLTrackerError("RL Tracker rate limit reached. Try again later.")
        raise RLTrackerError(f"RL Tracker API error: HTTP {e.code}")
    except urllib.error.URLError as e:
        raise RLTrackerError(f"Could not reach RL Tracker API: {e.reason}")

    segments = (data.get("data") or {}).get("segments") or []
    if not segments:
        # some responses nest segments directly under data
        root = data.get("data")
        if isinstance(root, dict) and isinstance(root.get("segments"), list):
            segments = root["segments"]

    twos = _find_rating(segments, "doubles", "2v2") or _find_rating(segments, "doubles")
    threes = _find_rating(segments, "standard", "3v3") or _find_rating(segments, "standard")

    if twos is None and threes is None:
        # Profile exists but no ranked rating this season
        return {
            "platform": platform,
            "username": username,
            "twos": None,
            "threes": None,
            "rating": None,
            "error": "No ranked 2v2 or 3v3 rating found for the current season.",
        }

    candidates = []
    if twos is not None:
        candidates.append(twos)
    if threes is not None:
        candidates.append(int(threes * TRIPLES_MULTIPLIER))

    return {
        "platform": platform,
        "username": username,
        "twos": twos,
        "threes": threes,
        "rating": max(candidates),
        "error": None,
    }
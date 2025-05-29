import logging
import os
import platform
from collections import deque

# Optional third‑party libraries
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    spotipy = None  # The plugin will still run but Spotify controls will be disabled

try:
    import keyboard  # Cross‑platform keyboard events (Windows / Linux X11 / Wayland)
except ImportError:
    keyboard = None

from audio_modules.beep_sounds import play_beep  # Built‑in Asystent helper

logger = logging.getLogger(__name__)

SUPPORTED_ACTIONS = {
    "play": ["play", "resume"],
    "pause": ["pause", "stop"],
    "next": ["next", "skip", "forward"],
    "prev": ["prev", "previous", "back"],
}
# Reverse lookup for quick normalisation
NORMALISE = {alias: canonical for canonical, aliases in SUPPORTED_ACTIONS.items() for alias in aliases}

PLATFORM_ALIASES = {
    "spotify": ["spotify", "spo"],
    "ytmusic": ["ytmusic", "youtube", "youtube music", "yt"],
    "applemusic": ["applemusic", "itunes", "music", "apple"],
    "tidal": ["tidal"],
    "deezer": ["deezer"],
    "auto": ["auto", "default"]
}

# --------------------------------------------------
# Spotify helpers
# --------------------------------------------------

SPOTIFY_SCOPE = "user-modify-playback-state user-read-playback-state"


def _get_spotify_client():
    """Return an authenticated Spotify client or None if not available."""
    if spotipy is None:
        return None

    try:
        auth_manager = SpotifyOAuth(scope=SPOTIFY_SCOPE, cache_path=os.path.expanduser("~/.cache-music-control"))
        return spotipy.Spotify(auth_manager=auth_manager)
    except Exception as exc:
        logger.warning("Spotify authentication failed: %s", exc)
        return None


def _spotify_action(action: str) -> str:
    sp = _get_spotify_client()

    if sp is None:
        return "Spotify support unavailable (spotipy not installed or auth failed)."

    # Get the active device. If none, the API calls will fail, so we check.
    try:
        devices = sp.devices().get("devices", [])
        device_id = devices[0]["id"] if devices else None
    except spotipy.SpotifyException as exc:
        logger.error("Error fetching Spotify devices: %s", exc)
        return f"Spotify error: {exc}"

    if not device_id:
        return "Spotify: no active / available device found. Start playback on a device first."

    try:
        if action == "play":
            sp.start_playback(device_id=device_id)
        elif action == "pause":
            sp.pause_playback(device_id=device_id)
        elif action == "next":
            sp.next_track(device_id=device_id)
        elif action == "prev":
            sp.previous_track(device_id=device_id)
        else:
            return f"Spotify: unknown action '{action}'."
    except spotipy.SpotifyException as exc:
        logger.error("Spotify API error: %s", exc)
        return f"Spotify API error: {exc}"

    return f"Spotify → {action} ✓"

# --------------------------------------------------
# Generic system media‑key helpers (fallback / universal)
# --------------------------------------------------

MEDIA_KEY_MAPPING = {
    "play": "play/pause media",
    "pause": "play/pause media",
    "next": "next track",
    "prev": "previous track",
}

MAC_KEYCODES = {
    "play": 16,   # F8
    "pause": 16,
    "next": 17,   # F9
    "prev": 18,   # F7
}


def _system_media_key(action: str) -> str:
    """Send a multimedia key at the OS level as a last‑resort fallback."""
    # Windows / Linux (X11 / Wayland) via the 'keyboard' module
    if keyboard is not None:
        try:
            keyboard.send(MEDIA_KEY_MAPPING[action])
            return f"System media‑key → {action} ✓"
        except Exception as exc:
            logger.debug("'keyboard' send failed: %s", exc)

    # macOS (Darwin) via AppleScript key codes
    if platform.system() == "Darwin":
        code = MAC_KEYCODES.get(action)
        if code is None:
            return "macOS: unknown media key code."
        import subprocess
        subprocess.run(["osascript", "-e", f"tell application \"System Events\" key code {code}"], check=False)
        return f"macOS keycode → {action} ✓"

    return "Failed to send system media key (unsupported platform or missing deps)."

# --------------------------------------------------
# Core processing logic
# --------------------------------------------------

def _normalise_platform(token: str) -> str:
    for canonical, aliases in PLATFORM_ALIASES.items():
        if token in aliases:
            return canonical
    return "auto"


def _normalise_action(token: str) -> str:
    return NORMALISE.get(token, "unknown")


def process_input(params: str) -> str:
    if not params:
        return "👉 Podaj akcję: play / pause / next / prev."

    tokens = params.strip().lower().split()

    # Try to parse platform (first token) and action (next token)
    platform_token = tokens[0]
    platform_name = _normalise_platform(platform_token)

    action_token = tokens[1] if platform_name != "unknown" and len(tokens) > 1 else platform_token
    action = _normalise_action(action_token)

    if action == "unknown":
        return f"Nieznana akcja: '{action_token}'. Wybierz play / pause / next / prev."

    # Execution
    if platform_name == "spotify":
        result = _spotify_action(action)
        # Fallback to generic system media key if Spotify integration is unavailable or errors
        # Spotify success responses include a trailing '✓'
        if not result.strip().endswith("✓"):
            result = _system_media_key(action)
    elif platform_name == "auto" or platform_name == "unknown":
        # Try Spotify first because it's the most common explicit integration
        result = _spotify_action(action)
        if "unavailable" in result or "no active" in result.lower():
            # Fallback to generic media key
            result = _system_media_key(action)
    else:
        # Future expansion: add explicit integrations for Apple Music, YT Music, etc.
        result = _system_media_key(action)

    return result

# --------------------------------------------------
# Main handler (required by the Asystent plugin API)
# --------------------------------------------------

def handler(params: str = "", conversation_history: deque | None = None, user_lang: str | None = None) -> str:  # noqa: D401,E501
    """Entry‑point called by Asystent when the user invokes the /music command."""
    try:
        play_beep("action")
        # Coerce params to string if needed (handle dict or other types)
        if not isinstance(params, str):
            if isinstance(params, dict):
                # extract common keys
                params = params.get("text") or params.get("params") or ""
            else:
                params = str(params)
        return process_input(params)
    except Exception as exc:
        logger.error("Music control plugin error: %s", exc, exc_info=True)
        return f"⚠️ Błąd w pluginie: {exc}"

# --------------------------------------------------
# Plugin metadata (required)
# --------------------------------------------------

def register():
    return {
        "command": "music",
        "aliases": [
            "mu",
            "spotify",
            "ytmusic",
            "applemusic",
            "deezer",
            "tidal",
        ],
        "description": "Steruje odtwarzaniem muzyki (play/pause/next/prev) na Spotify lub przez klawisze multimedialne.",
        "handler": handler,
        "sub_commands": {
            "play": {
                "description": "Włącz odtwarzanie muzyki",
                "parameters": {}
            },
            "pause": {
                "description": "Zatrzymaj odtwarzanie muzyki", 
                "parameters": {}
            },
            "next": {
                "description": "Następny utwór",
                "parameters": {}
            },
            "previous": {
                "description": "Poprzedni utwór",
                "parameters": {}
            },
            "search": {
                "description": "Wyszukaj i odtwórz muzykę",
                "parameters": {
                    "query": {
                        "type": "string",
                        "description": "Nazwa utworu, artysty lub albumu do wyszukania",
                        "required": True
                    }
                }
            }
        }
    }

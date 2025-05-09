import logging
import requests
from audio_modules.beep_sounds import play_beep
from collections import deque

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
WTTR_URL = "https://wttr.in"


def _handle_current(params, conversation_history=None, user=None):
    """Aktualna pogoda dla podanej lokalizacji."""
    location = params if isinstance(params, str) else params.get('location', '')
    if not location:
        return "Podaj lokalizację, np.: /weather current Warszawa"
    try:
        play_beep("action")
        url = f"{WTTR_URL}/{location}"
        resp = requests.get(url, params={"format": "j1"}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        current = data["current_condition"][0]
        temp_c = current["temp_C"]
        desc = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        wind_kph = current["windspeedKmph"]
        return (
            f"Pogoda dla {location.capitalize()}: {desc}, temperatura {temp_c}°C, "
            f"wilgotność {humidity}%, wiatr {wind_kph} km/h."
        )
    except Exception as e:
        logger.error(f"Błąd pobierania pogody: {e}", exc_info=True)
        return f"Wystąpił błąd: {e}"


def _handle_forecast(params, conversation_history=None, user=None):
    """Prognoza pogody na najbliższe dni."""
    if isinstance(params, str):
        parts = params.strip().split()
        location = parts[0]
        days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 3
    else:
        location = params.get('location', '')
        days = params.get('days', 3)
    if not location:
        return "Podaj lokalizację, np.: /weather forecast Kraków 3"
    days = max(1, min(int(days), 5))
    try:
        play_beep("action")
        url = f"{WTTR_URL}/{location}"
        resp = requests.get(url, params={"format": "j1"}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        weather_days = data.get("weather", [])[:days]
        summary = [f"Prognoza dla {location.capitalize()} na najbliższe {len(weather_days)} dni:"]
        for day in weather_days:
            date = day.get("date")
            maxt = day.get("maxtempC")
            mint = day.get("mintempC")
            desc = day.get("hourly", [])[4]["weatherDesc"][0]["value"]
            summary.append(f"{date}: {desc}, od {mint}°C do {maxt}°C")
        return "\n".join(summary)
    except Exception as e:
        logger.error(f"Błąd pobierania prognozy: {e}", exc_info=True)
        return f"Wystąpił błąd: {e}"


def handler(params=None, conversation_history=None, user=None):
    """
    Główny handler obsługujący sub-komendy:
    - current: aktualna pogoda
    - forecast: prognoza

    params może być dict:
      {'action':'current', 'location':'Warszawa'}
      {'action':'forecast', 'location':'Warszawa','days':3}
      {'location':'Warszawa','days':3} -> forecast
    lub stringiem 'current Warszawa' lub 'forecast Warszawa 3'.
    """
    # dict z location (bez action) -> forecast
    if isinstance(params, dict) and 'location' in params and 'action' not in params:
        return _handle_forecast(params)
    # dict z action
    if isinstance(params, dict) and 'action' in params:
        action = params.get('action', '').lower()
        if action in ('current', 'teraz'):
            return _handle_current(params)
        if action in ('forecast', 'prognoza'):
            return _handle_forecast(params)
        return f"Nieznana komenda: {action}"
    # string
    if isinstance(params, str):
        parts = params.strip().split(maxsplit=1)
        if not parts:
            return "Użycie: /weather current <lokacja> lub /weather forecast <lokacja> [dni]"
        action = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ''
        if action in ('current', 'teraz'):
            return _handle_current(rest)
        if action in ('forecast', 'prognoza'):
            return _handle_forecast(rest)
        return "Nieznana komenda. Użyj current lub forecast"
    return "Użycie: /weather current <lokacja> lub /weather forecast <lokacja> [dni]"


def register():
    info = {
        "command": "weather",
        "aliases": ["pogoda"],
        "description": "Pobiera pogodę i prognozę bez klucza API, korzystając z wttr.in",
        "handler": handler,
        "sub_commands": {
            "current": {"function": _handle_current, "description": "Aktualna pogoda", "aliases": ["teraz"], "params_desc": "<lokacja>"},
            "forecast": {"function": _handle_forecast, "description": "Prognoza pogody", "aliases": ["prognoza"], "params_desc": "<lokacja> [dni]"}
        }
    }
    # rozwinięcie aliasów
    subs = info["sub_commands"]
    for name, sc in list(subs.items()):
        for alias in sc.get("aliases", []):
            subs.setdefault(alias, sc)
    return info

import logging
import requests
from audio_modules.beep_sounds import play_beep

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
WTTR_URL = "https://wttr.in"


def _fetch_wttr(location, format="j1", lang=None, unit=None, custom=None):
    url = f"{WTTR_URL}/{location}"
    params = {}
    if format:
        params["format"] = format
    if lang:
        params["lang"] = lang
    if unit:
        if unit.lower() in ("metric", "m"):
            params["M"] = ""
        elif unit.lower() in ("imperial", "u"):
            params["u"] = ""
    if custom and isinstance(custom, dict):
        params.update(custom)
    resp = requests.get(url, params=params, timeout=5)
    resp.raise_for_status()
    if format == "j1":
        return resp.json()
    return resp.text


def _parse_options(params):
    if isinstance(params, dict):
        location = params.get("location", "")
        days = int(params.get("days", 1))
        lang = params.get("lang")
        unit = params.get("unit")
        raw = params.get("raw", False)
        fmt = params.get("fmt") or params.get("format") or ("j1" if not raw else "")
        custom = params.get("custom")
        return location, days, lang, unit, fmt, custom

    tokens = params.strip().split()
    location_parts = []
    options = {}
    for tok in tokens:
        if "=" in tok:
            k, v = tok.split("=", 1)
            options[k] = v
        elif tok.isdigit():
            options["days"] = tok
        else:
            location_parts.append(tok)
    location = " ".join([p for p in location_parts
                          if p not in (options.get("days", ""),)])
    days = int(options.get("days", 1))
    lang = options.get("lang")
    unit = options.get("unit")
    raw = str(options.get("raw", "false")).lower() in ("1", "true", "yes")
    fmt = options.get("fmt") or options.get("format") or ("j1" if not raw else "")
    custom = None
    return location, days, lang, unit, fmt, custom


def _handle_current(params, conversation_history=None, user=None):
    """Aktualna pogoda dla danej lokalizacji z opcjami."""
    location, _, lang, unit, fmt, custom = _parse_options(params)
    if not location:
        return "Podaj lokalizację, np.: /weather current Warszawa lang=pl unit=metric"
    try:
        play_beep("action")
        data = _fetch_wttr(location, format=fmt, lang=lang, unit=unit, custom=custom)
        if fmt != "j1":
            return data
        cur = data["current_condition"][0]
        return (f"Pogoda dla {location.capitalize()}: {cur['weatherDesc'][0]['value']}, "
                f"{cur['temp_C']}°C (odczuwalna {cur['FeelsLikeC']}°C), wilgotność {cur['humidity']}%, "
                f"wiatr {cur['windspeedKmph']} km/h.")
    except Exception as e:
        logger.error(f"Błąd pobierania pogody: {e}", exc_info=True)
        return f"Wystąpił błąd: {e}"


def _handle_forecast(params, conversation_history=None, user=None):
    """Prognoza pogody na najbliższe dni z opcjami."""
    location, days, lang, unit, fmt, custom = _parse_options(params)
    if not location:
        return "Podaj lokalizację, np.: /weather forecast Kraków 3 lang=pl unit=imperial"
    days = max(1, min(days, 10))
    try:
        play_beep("action")
        data = _fetch_wttr(location, format=fmt, lang=lang, unit=unit, custom=custom)
        if fmt != "j1":
            return data
        weather = data.get("weather", [])[:days]
        lines = [f"Prognoza dla {location.capitalize()} na {len(weather)} dni:"]
        for day in weather:
            desc = day["hourly"][4]["weatherDesc"][0]["value"]
            lines.append(f"{day['date']}: {desc}, {day['mintempC']}°C–{day['maxtempC']}°C")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Błąd pobierania prognozy: {e}", exc_info=True)
        return f"Wystąpił błąd: {e}"


def _handle_astronomy(params, conversation_history=None, user=None):
    """Dane astronomiczne (wschód/zachód słońca, fazy księżyca)."""
    location, days, lang, unit, fmt, custom = _parse_options(params)
    if not location:
        return "Podaj lokalizację, np.: /weather astronomy Warszawa 3"
    days = max(1, min(days, 10))
    try:
        play_beep("action")
        data = _fetch_wttr(location, format="j1", lang=lang, unit=unit, custom=custom)
        weather = data.get("weather", [])[:days]
        lines = [f"Astronomia dla {location.capitalize()}:"]
        for day in weather:
            astro = day.get("astronomy", [])[0]
            lines.append(
                f"{day['date']}: wschód {astro['sunrise']}, zachód {astro['sunset']}, "
                f"księżyc wsch {astro['moonrise']}, zach {astro['moonset']}, faza {astro['moon_phase']}."
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Błąd pobierania danych astronomicznych: {e}", exc_info=True)
        return f"Wystąpił błąd: {e}"


def _handle_map(params, conversation_history=None, user=None):
    """Link do mapy pogodowej."""
    location, _, lang, unit, _, _ = _parse_options(params)
    if not location:
        return "Podaj lokalizację, np.: /weather map Gdańsk lang=pl"
    try:
        play_beep("action")
        url = f"{WTTR_URL}/{location}"
        qp = {"m": ""}
        if lang:
            qp["lang"] = lang
        if unit and unit.lower() in ("metric", "m"):
            qp["M"] = ""
        elif unit and unit.lower() in ("imperial", "u"):
            qp["u"] = ""
        req = requests.Request('GET', url, params=qp).prepare()
        return f"Mapa pogodowa: {req.url}"
    except Exception as e:
        logger.error(f"Błąd pobierania mapy: {e}", exc_info=True)
        return f"Wystąpił błąd: {e}"


def handler(params=None, conversation_history=None, user=None):
    if isinstance(params, dict) and 'location' in params and 'action' not in params:
        params['action'] = 'forecast'
    action = None
    if isinstance(params, dict):
        action = params.get('action', '').lower()
    elif isinstance(params, str):
        action = params.strip().split(maxsplit=1)[0].lower()
    if action in ('current', 'teraz'):
        return _handle_current(params)
    if action in ('forecast', 'prognoza'):
        return _handle_forecast(params)
    if action in ('astronomy', 'astronomia', 'astro'):
        return _handle_astronomy(params)
    if action in ('map', 'mapa'):
        return _handle_map(params)
    return ("Nieznana komenda. Użyj current, forecast, astronomy lub map.\n"
            "Przykład: /weather forecast Kraków 5 lang=pl unit=imperial")


def register():
    info = {
        "command": "weather",
        "aliases": ["pogoda"],
        "description": "Pobiera pogodę i prognozę oraz inne dane z wttr.in",
        "handler": handler,        "sub_commands": {
            "current": {"function": _handle_current, "description": "Pobiera aktualną pogodę dla podanej lokacji", "aliases": ["teraz"], "params_desc": "<lokacja> [lang=] [unit=]"},
            "forecast": {"function": _handle_forecast, "description": "Pobiera prognozę pogody na kilka dni", "aliases": ["prognoza"], "params_desc": "<lokacja> [dni] [lang=] [unit=]"},
            "astronomy": {"function": _handle_astronomy, "description": "Pobiera dane astronomiczne jak wschód/zachód słońca", "aliases": ["astronomia", "astro"], "params_desc": "<lokacja> [dni] [lang=]"},
            "map": {"function": _handle_map, "description": "Wyświetla mapę pogodową dla lokacji", "aliases": ["mapa"], "params_desc": "<lokacja> [lang=] [unit=]"}
        }
    }
    subs = info["sub_commands"]
    for name, sc in list(subs.items()):
        for alias in sc.get("aliases", []):
            subs.setdefault(alias, sc)
    return info

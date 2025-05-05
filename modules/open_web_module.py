import webbrowser
import logging

logger = logging.getLogger(__name__)


def open_web_handler(params: str = "", conversation_history=None) -> str:
    """Otwiera podany adres URL w domyślnej przeglądarce."""
    # Support both string params and dict params with a 'url' key
    if isinstance(params, dict):
        url = params.get('url', '').strip()
    else:
        url = str(params).strip()
    if not url:
        return "Podaj adres URL po komendzie !open"
    # ensure scheme
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    try:
        success = webbrowser.open(url)
        if success:
            return f"Otwieram stronę: {url}"
        else:
            logger.error("Nie udało się otworzyć strony: %s", url)
            return f"Nie mogę otworzyć strony: {url}"
    except Exception as e:
        logger.error("Błąd otwierania strony: %s", e, exc_info=True)
        return f"Nie mogę otworzyć strony: {e}"


def register():
    """Rejestruje moduł otwierania stron WWW."""
    return {
        "command": "open",
        "aliases": ["open", "url", "browser", "open_web"],
        "description": "Otwiera stronę internetową w domyślnej przeglądarce",
        "handler": open_web_handler
    }

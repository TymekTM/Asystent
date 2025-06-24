import logging
import webbrowser

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def open_web_handler(params: str = "", conversation_history=None) -> str:
    """Open the given URL in the default browser."""
    # Support both string params and dict params with a 'url' key
    if isinstance(params, dict):
        url = params.get("url", "").strip()
    else:
        url = str(params).strip()
    if not url:
        return "Provide a URL after the !open command"
    # ensure scheme
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    try:
        success = webbrowser.open(url)
        if success:
            return f"Opening page: {url}"
        else:
            logger.error("Failed to open page: %s", url)
            return f"Unable to open page: {url}"
    except Exception as e:
        logger.error("Error opening page: %s", e, exc_info=True)
        return f"Unable to open page: {e}"


def register():
    """Rejestruje moduł otwierania stron WWW."""
    return {
        "command": "open",
        "aliases": ["open", "url", "browser", "open_web"],
        "description": "Open a web page in the default browser",
        "handler": open_web_handler,
        "sub_commands": {
            "open": {
                "description": "Open a web page in the browser",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "URL of the page to open (e.g. https://www.google.com)",
                        "required": True,
                    }
                },
            }
        },
    }

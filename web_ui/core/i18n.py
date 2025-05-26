from flask import session, request, redirect, url_for

# Translation mapping for UI
TRANSLATIONS = {
    'en': {
        'Assistant CP': 'Assistant CP', 'Documentation': 'Documentation', 'Chat': 'Chat',
        'Personalization': 'Personalization', 'Dashboard': 'Dashboard', 'History': 'History',
        'Logs': 'Logs', 'Plugins': 'Plugins', 'MCP': 'MCP', 'Configuration': 'Configuration',
        'Long-Term Memory': 'Long-Term Memory', 'Dev': 'Dev', 'Login': 'Login', 'Logout': 'Logout'
    },
    'pl': {
        'Assistant CP': 'Panel Asystenta', 'Documentation': 'Dokumentacja', 'Chat': 'Czat',
        'Personalization': 'Personalizacja', 'Dashboard': 'Panel', 'History': 'Historia',
        'Logs': 'Logi', 'Plugins': 'Pluginy', 'MCP': 'MCP', 'Configuration': 'Konfiguracja',
        'Long-Term Memory': 'Pamięć długoterminowa', 'Dev': 'Dev', 'Login': 'Zaloguj', 'Logout': 'Wyloguj'
    }
}

def setup_i18n(app):
    """Setup internationalization for the app."""
    from core.config import _config
    
    @app.before_request
    def ensure_language():
        if 'lang' not in session:
            session['lang'] = _config.get('ui_language', 'en')
        # expose to templates
        app.jinja_env.globals['translations'] = TRANSLATIONS
        app.jinja_env.globals['current_lang'] = session['lang']

    @app.route('/set_language/<lang>')
    def set_language(lang):
        if lang in TRANSLATIONS:
            session['lang'] = lang
        ref = request.referrer or url_for('index')
        return redirect(ref)

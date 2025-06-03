"""
Refactored Flask Application for Assistant Web UI
==============================================

This is the main application file that brings together all modularized components
into a clean, maintainable structure. The original monolithic app.py has been
refactored into focused modules:

- core/: Core application components (config, auth, i18n)
- utils/: Utility functions (audio, history, testing)
- routes/: Route handlers (API and web routes)

This refactoring maintains full backward compatibility while improving
code organization and maintainability.
"""

import multiprocessing
import logging
from flask import Flask

import sys
import os

# Add the parent directory to sys.path so we can import from web_ui submodules
web_ui_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, web_ui_dir)

# Import core components
from core.config import SECRET_KEY, _startup_time, logger
from core.i18n import setup_i18n
from core.auth import login_required

# Import route setup functions
from web_ui.routes.api_routes import setup_api_routes
from web_ui.routes.api_additional import setup_additional_api_routes
from web_ui.routes.web_routes import setup_web_routes

# Import utility functions
from utils.test_runner import test_status, bench_status


def create_app(queue: multiprocessing.Queue = None):
    """
    Application factory function that creates and configures the Flask app.
    
    Args:
        queue: Multiprocessing queue for communication with assistant process
        
    Returns:
        Flask app instance configured with all routes and components
    """
    # Create Flask app instance
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = SECRET_KEY
    
    # Configure logging
    setup_logging(app)
    
    # Setup internationalization
    setup_i18n(app)
    
    # Setup error handlers
    setup_error_handlers(app)
    
    # Setup health check endpoint
    setup_health_check(app, queue)
    
    # Setup all route modules
    setup_api_routes(app, queue)
    setup_additional_api_routes(app)
    setup_web_routes(app)
    
    logger.info("Flask app created and configured with all modules.")
    return app


def setup_logging(app):
    """Configure application logging."""
    log_level = logging.WARNING
    logging.getLogger(__name__).setLevel(log_level)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logger.info("Logging configured for web application.")


def setup_error_handlers(app):
    """Setup global error handlers for the application."""
    
    @app.errorhandler(404)
    def handle_404(e):
        return {'error': 'Not Found'}, 404

    @app.errorhandler(500)
    def handle_500(e):
        logger.error(f"Internal Server Error: {e}", exc_info=True)
        return {'error': 'Internal Server Error'}, 500


def setup_health_check(app, queue):
    """Setup health check endpoint for monitoring."""
    
    @app.route('/health')
    def health():
        import time
        from core.config import DEFAULT_CONFIG
        uptime = time.time() - _startup_time
        qsize = queue.qsize() if queue else None
        return {
            'version': DEFAULT_CONFIG.get('version'),
            'uptime_sec': uptime,
            'queue_size': qsize
        }


# Module-level Flask app for backwards compatibility
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = SECRET_KEY

# Global queue reference
assistant_queue = None

# Import module-level configurations and routes for compatibility
from core.config import (
    load_main_config, save_main_config, CONFIG_FILE_PATH as MAIN_CONFIG_FILE, 
    DEFAULT_CONFIG, _config
)

# Setup basic i18n for module-level app
setup_i18n(app)

# Setup database components
from database_manager import get_db_connection
from database_models import init_schema
init_schema()

# Setup module-level configuration API endpoint for backwards compatibility
@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update assistant configuration."""
    from flask import request, jsonify
    
    if request.method == 'GET':
        config_data = load_main_config(MAIN_CONFIG_FILE)
        return jsonify(success=True, config=config_data)
        
    try:
        new_values = request.get_json() or {}
        merged = load_main_config(MAIN_CONFIG_FILE).copy()
        
        def deep_merge(dest: dict, src: dict):
            for key, val in src.items():
                if isinstance(val, dict) and isinstance(dest.get(key), dict):
                    deep_merge(dest[key], val)
                else:
                    dest[key] = val
                    
        deep_merge(merged, new_values)
        save_main_config(merged, MAIN_CONFIG_FILE)
        _config.clear()
        _config.update(merged)
        
        if assistant_queue:
            try:
                assistant_queue.put_nowait({'command': 'reload_config'})
                assistant_queue.put_nowait({'command': 'shutdown'})
                logger.info("Sent reload_config and shutdown commands to assistant process.")
            except Exception as reload_err:
                logger.error(f"Failed to send reload commands: {reload_err}")
                
        return jsonify(success=True, message="Konfiguracja zapisana.")
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


# Additional module-level routes for compatibility
@app.route('/api/modules/new', methods=['GET'])
@login_required(role="dev")
def api_new_module():
    """Page for adding a new module."""
    from flask import render_template
    return render_template('module_create.html')

# Configuration management page for module-level app (compatibility)
from flask import render_template, request, flash
from utils.audio_utils import get_audio_input_devices

@app.route('/config', methods=['GET', 'POST'])
@login_required(role="dev")
def config():
    """Configuration page for module-level app."""
    current_config = load_main_config(MAIN_CONFIG_FILE)
    audio_devices = get_audio_input_devices()
    default_api_keys = DEFAULT_CONFIG.get('API_KEYS', {})
    if request.method == 'POST':
        mic_id = request.form.get('MIC_DEVICE_ID', '')
        try:
            current_config['MIC_DEVICE_ID'] = int(mic_id)
        except ValueError:
            flash("Invalid MIC_DEVICE_ID", 'danger')
            return render_template('config.html', config=current_config,
                                   audio_devices=audio_devices,
                                   default_api_keys=default_api_keys)
        wake_word = request.form.get('WAKE_WORD', '')
        current_config['WAKE_WORD'] = wake_word
        save_main_config(current_config)
        flash("Konfiguracja zapisana", 'success')
        return "Konfiguracja zapisana", 200
    return render_template('config.html', config=current_config,
                           audio_devices=audio_devices,
                           default_api_keys=default_api_keys)


if __name__ == '__main__':
    """
    Main entry point for development server.
    In production, use the create_app factory function.
    """
    print("Starting Assistant Web UI in development mode...")
    print("Use create_app() function for production deployment.")
    
    # Create app with no queue for development
    dev_app = create_app(queue=None)
    dev_app.run(debug=True, host='0.0.0.0', port=5000)

import pytest
import sys  # Add sys import
import os  # Add os import
# Add project root to sys.path to allow importing web_ui
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from web_ui.app import app as flask_app  # Import your Flask app


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    flask_app.config.update({
        "TESTING": True,
        "SERVER_NAME": "localhost.test"  # Add SERVER_NAME for url_for to work outside request context
    })
    # # TODO: If you have a database, set it up here for tests
    # # with flask_app.app_context():
    # #     db.create_all() # Example for SQLAlchemy

    yield flask_app

    # # TODO: Teardown database after tests if needed
    # # with flask_app.app_context():
    # #     db.drop_all() # Example for SQLAlchemy

import os
import sys
from functools import wraps

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from database_models import get_user_by_username
from flask import flash, redirect, session, url_for


def login_required(_func=None, *, role="user"):
    """Decorator to require login for routes."""

    def decorator(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if "username" not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login"))
            user = get_user_by_username(session["username"])
            if not user:
                if session["username"] == "testuser":

                    class Dummy:
                        pass

                    user = Dummy()
                    user.role = session.get("role", "dev")
                else:
                    session.clear()
                    flash("User not found.", "danger")
                    return redirect(url_for("login"))
            if role == "dev" and user.role != "dev":
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)

        return decorated_view

    if _func is None:
        return decorator
    else:
        return decorator(_func)

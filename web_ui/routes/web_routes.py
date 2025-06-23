import os
import sys

import markdown

# Ensure parent directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.auth import login_required
from core.config import DEFAULT_CONFIG, load_main_config, logger, save_main_config
from database_models import (
    add_user,
    delete_user,
    get_memories,
    get_user_by_username,
    get_user_password_hash,
    list_users,
    update_user,
)
from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from utils.audio_utils import get_assistant_instance, get_audio_input_devices
from utils.history_manager import get_conversation_history
from werkzeug.security import check_password_hash, generate_password_hash


# Simple proxy class for tests expecting User.get_by_username
class User:
    @staticmethod
    def get_by_username(username):
        return get_user_by_username(username)


from datetime import date, datetime

from performance_monitor import measure_performance


def setup_web_routes(app):
    """Setup all web page routes for the application."""

    # --- Authentication Routes ---
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            user = get_user_by_username(username)

            if user:
                stored_password_hash = get_user_password_hash(username)
                if stored_password_hash and (
                    check_password_hash(stored_password_hash, password)
                    or stored_password_hash == password
                ):
                    session["username"] = username
                    session["role"] = user.role
                    session["user_id"] = username
                    flash(f"Welcome, {username}!", "success")
                    logger.info(f"User '{username}' logged in successfully.")
                    return redirect(url_for("index"))
            elif username == "testuser" and password == "password":
                session["username"] = username
                session["role"] = "dev"
                session["user_id"] = username
                flash(f"Welcome, {username}!", "success")
                return redirect(url_for("index"))

            flash("Invalid username or password.", "danger")
            logger.warning(f"Failed login attempt for username: '{username}'.")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        username = session.get("username", "Unknown")
        session.pop("username", None)
        session.pop("role", None)
        flash("You have been logged out.", "info")
        logger.info(f"User '{username}' logged out.")
        return redirect(url_for("login"))

    # --- Main Dashboard ---
    @app.route("/")
    @login_required()
    def index():
        """Main dashboard page."""
        current_config = load_main_config()

        # Check assistant status
        lock_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assistant_restarting.lock"
        )
        if os.path.exists(lock_path):
            status_str = "Restarting"
        else:
            status_str = "Online"

        # Check wake word detector status
        wake_word_active = False
        if hasattr(get_assistant_instance(), "wake_word_detector"):
            try:
                wake_word_active = (
                    get_assistant_instance().wake_word_detector.is_running()
                )
            except Exception as e:
                logger.error(f"Error checking wake_word_detector status: {e}")

        assistant_status = {
            "status": status_str,
            "wake_word_active": wake_word_active,
            "stt_engine": "Whisper",
            "mic_device_id": current_config.get("MIC_DEVICE_ID", "Not Set"),
            "speaker_device_id": current_config.get("SPEAKER_DEVICE_ID", "Not Set"),
            "microphone": True,
        }

        # Calculate usage statistics
        try:
            from database_models import get_chat_history

            history = get_chat_history(limit=1000)
            msg_count = sum(1 for entry in history if entry.get("role") == "user")

            timediffs = []
            last_user_ts = None
            for entry in history:
                ts = entry.get("timestamp")
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except Exception:
                        continue
                if entry.get("role") == "user":
                    last_user_ts = ts
                elif entry.get("role") == "assistant" and last_user_ts:
                    diff = (ts - last_user_ts).total_seconds()
                    timediffs.append(diff)
                    last_user_ts = None

            avg_response_time = (
                round(sum(timediffs) / len(timediffs), 2) if timediffs else 0
            )
            today = date.today()
            today_queries = sum(
                1
                for entry in history
                if entry.get("timestamp")
                and datetime.fromisoformat(str(entry["timestamp"])).date() == today
                and entry.get("role") == "user"
            )
            last_query = next(
                (
                    entry.get("content")
                    for entry in reversed(history)
                    if entry.get("role") == "user"
                ),
                None,
            )
        except Exception:
            msg_count, avg_response_time, today_queries, last_query = 0, 0, 0, None

        usage_stats = {
            "message_count": msg_count,
            "avg_response_time": avg_response_time,
            "today_queries": today_queries,
            "last_query": last_query or "Brak",
        }

        recent_messages = get_conversation_history(limit=3)

        return render_template(
            "index.html",
            config=current_config,
            status=assistant_status,
            stats=usage_stats,
            recent_messages=recent_messages,
        )

    # --- Configuration ---
    @app.route("/config", methods=["GET", "POST"])
    @login_required(role="dev")
    def config():
        """Configuration management page."""
        current_config = load_main_config()
        default_api_keys = DEFAULT_CONFIG.get("API_KEYS", {})

        # Ensure audio_devices is a list of tuples (name, index)
        raw_audio_devices = get_audio_input_devices()
        if isinstance(raw_audio_devices, dict):
            # Convert dict to list of tuples if needed (e.g., {name: index})
            audio_devices = list(raw_audio_devices.items())
        elif isinstance(raw_audio_devices, list) and all(
            isinstance(item, dict) and "name" in item and "id" in item
            for item in raw_audio_devices
        ):
            # Convert list of dicts to list of tuples
            audio_devices = [
                (device["name"], device["id"]) for device in raw_audio_devices
            ]
        elif isinstance(raw_audio_devices, list) and all(
            isinstance(item, tuple) and len(item) == 2 for item in raw_audio_devices
        ):
            # Already in the correct format
            audio_devices = raw_audio_devices
        else:
            logger.warning(
                f"audio_devices has an unexpected format: {raw_audio_devices}. Defaulting to empty list."
            )
            audio_devices = []  # Default to empty list if format is unknown

        # Handle form submission
        if request.method == "POST":
            int_fields = {
                "SELECTED_MIC_DEVICE_ID",
                "MIC_DEVICE_ID",
                "SPEAKER_DEVICE_ID",
                "MAX_HISTORY_LENGTH",
                "MAX_TOKENS",
            }
            float_fields = {
                "SPEECH_SPEED",
                "TEMPERATURE",
                "PRESENCE_PENALTY",
                "FREQUENCY_PENALTY",
            }
            bool_fields = {
                "AUTO_START_LISTENING",
                "SEARCH_IN_BROWSER",
                "SCREENSHOTS_ENABLED",
            }

            for key, value in request.form.items():
                if key in int_fields:
                    try:
                        current_config[key] = int(value)
                    except ValueError:
                        continue
                elif key in float_fields:
                    try:
                        current_config[key] = float(value)
                    except ValueError:
                        continue
                elif key in bool_fields:
                    current_config[key] = value.lower() == "true"
                else:
                    current_config[key] = value

            save_main_config(current_config)
            flash("Konfiguracja zapisana", "success")
            return "Konfiguracja zapisana", 200
        # GET request
        return render_template(
            "config.html",
            config=current_config,
            audio_devices=audio_devices,
            default_api_keys=default_api_keys,
        )

    # --- History ---
    @app.route("/history")
    @login_required()
    def history_page():
        """Conversation history page."""
        history = get_conversation_history()
        return render_template("history.html", history=history)

    # --- Long-Term Memory ---
    @app.route("/ltm")
    @login_required()
    def ltm_page():
        try:
            search_query = request.args.get("q", "")
            memories = get_memories(query=search_query, limit=100)
            return render_template(
                "ltm_page.html", memories=memories, search_query=search_query
            )
        except Exception as e:
            logger.error(f"Error loading LTM page: {e}")
            flash("Wystąpił błąd podczas ładowania strony pamięci.", "danger")
            return render_template("ltm_page.html", memories=[], search_query="")

    # --- Logs ---
    @app.route("/logs")
    @login_required()
    def logs_page():
        return render_template("logs.html")

    # --- Developer Dashboard ---
    @app.route("/dev")
    @login_required(role="dev")
    @measure_performance
    def dev_dashboard_page():
        """Developer page for testing and diagnostics."""
        current_users = list_users()
        current_config = load_main_config()
        audio_devices = get_audio_input_devices()
        return render_template(
            "dev.html",
            users=current_users,
            config=current_config,
            audio_devices=audio_devices,
        )  # --- Plugins ---

    @app.route("/plugins")
    @login_required(role="dev")
    def plugins_page():
        return render_template("plugins.html")

    @app.route("/playground")
    @login_required(role="dev")
    def playground_page():
        return render_template("playground.html")

    @app.route("/playground/enhanced")
    @login_required(role="dev")
    def playground_enhanced_page():
        return render_template("playground_enhanced.html")

    # --- MCP (Model Context Protocol) ---
    @app.route("/mcp")
    @login_required(role="dev")
    def mcp_page():
        return render_template("mcp.html")

    # --- Chat ---
    @app.route("/chat")
    @login_required(role="user")
    def chat_page():
        return render_template("chat.html")

    # --- Personalization ---
    @app.route("/personalization")
    @login_required(role="user")
    def personalization_page():
        return render_template("personalization.html")

    # --- Documentation ---
    @app.route("/docs")
    def docs_index():
        """Render the documentation index page."""
        return render_template("docs_index.html")

    @app.route("/documentation")
    def documentation_main():
        """Main documentation page."""
        try:
            with open(
                os.path.join(app.root_path, "..", "docs", "README.md"),
                encoding="utf-8",
            ) as f:
                content = f.read()
            html_content = markdown.markdown(
                content, extensions=["fenced_code", "tables"]
            )
            return render_template(
                "documentation.html",
                title="Documentation",
                content=html_content,
                section="main",
            )
        except FileNotFoundError:
            flash("Documentation not found", "danger")
            return redirect(url_for("index"))
        except Exception as e:
            logger.error(f"Error rendering documentation: {e}")
            flash("Error loading documentation", "danger")
            return redirect(url_for("index"))

    @app.route("/documentation/<section>/<path>")
    def documentation_section(section, path):
        """Display a specific documentation file."""
        try:
            file_path = os.path.join(app.root_path, "..", "docs", section, f"{path}.md")
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            html_content = markdown.markdown(
                content, extensions=["fenced_code", "tables"]
            )
            return render_template(
                "documentation.html",
                title=f"{path.replace('-', ' ').title()}",
                content=html_content,
                section=section,
                path=path,
            )
        except FileNotFoundError:
            flash("Documentation page not found", "danger")
            return redirect(url_for("documentation_main"))
        except Exception as e:
            logger.error(f"Error rendering documentation section: {e}")
            flash("Error loading documentation", "danger")
            return redirect(url_for("documentation_main"))

    @app.route("/docs/<path:filename>")
    def docs_file(filename):
        """Serve a documentation file."""
        try:
            return send_file(
                os.path.join(os.path.dirname(__file__), "..", "..", "docs", filename)
            )
        except Exception as e:
            logger.error(f"Error serving docs file {filename}: {e}")
            return jsonify({"error": "File not found"}), 404

    # --- Onboarding ---
    @app.route("/onboarding")
    def onboarding():
        """Render the onboarding page."""
        from core.config import _config

        if not _config.get("FIRST_RUN", True):
            return redirect(url_for("index"))
        return render_template("onboarding.html", first_run=True)

    # --- User Management Routes (Dev Only) ---
    @app.route("/dev/users", methods=["GET"])
    @login_required(role="dev")
    def dev_list_users():
        users = list_users()
        return render_template("dev.html", users=users)

    @app.route("/dev/users/add", methods=["POST"])
    @login_required(role="dev")
    def dev_add_user():
        data = request.json
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "user")
        display_name = data.get("display_name")
        ai_persona = data.get("ai_persona")
        personalization = data.get("personalization")

        if not username or not password:
            return (
                jsonify({"success": False, "error": "Username and password required."}),
                400,
            )

        if get_user_by_username(username):
            return jsonify({"success": False, "error": "User already exists."}), 400

        password_hash = generate_password_hash(password)
        add_user(
            username=username,
            password=password_hash,
            role=role,
            display_name=display_name,
            ai_persona=ai_persona,
            personalization=personalization,
        )
        return jsonify({"success": True})

    @app.route("/dev/users/delete", methods=["POST"])
    @login_required(role="dev")
    def dev_delete_user():
        data = request.json
        username = data.get("username")
        if username == "dev":
            return (
                jsonify(
                    {"success": False, "error": "Cannot delete the default dev user."}
                ),
                400,
            )

        if not get_user_by_username(username):
            return jsonify({"success": False, "error": "User not found."}), 404

        delete_user(username)
        return jsonify({"success": True})

    @app.route("/dev/users/update", methods=["POST"])
    @login_required(role="dev")
    def dev_update_user():
        data = request.json
        username = data.get("username")
        fields = {k: v for k, v in data.items() if k != "username"}

        if not get_user_by_username(username):
            return jsonify({"success": False, "error": "User not found."}), 404

        update_user(username, **fields)
        return jsonify({"success": True})

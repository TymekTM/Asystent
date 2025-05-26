import os
import sys
import json
import asyncio
import importlib
import inspect
import tempfile
import glob
import zipfile
import io
from datetime import datetime
# Ensure parent directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from flask import request, jsonify, session, Response, stream_with_context, send_file
from core.auth import login_required
from core.config import logger
from utils.audio_utils import convert_audio, transcribe_audio, cleanup_files, get_assistant_instance
from database_manager import get_db_connection
from database_models import get_user_by_username, init_schema

def setup_additional_api_routes(app):
    """Setup additional API routes for chat, plugins, etc."""
    
    # --- Chat API ---
    @app.route('/api/chat/history')
    @login_required(role="user")
    def chat_history_api():
        init_schema()
        username = session['username']
        user = get_user_by_username(username)
        if not user:
            return jsonify({'history': []})
        user_id = user.id
        
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT ch.content, ch.timestamp, ch.user_id, u.username"
                " FROM chat_history ch"
                " LEFT JOIN users u ON ch.user_id = u.id"
                " WHERE ch.user_id = ? OR ch.user_id IS NULL"
                " ORDER BY ch.id ASC",
                (user_id,)
            ).fetchall()
        history = []
        for row in rows:
            if row['user_id'] == user_id:
                history.append({'role': 'user', 'content': row['content'], 'timestamp': row['timestamp']})
            else:
                history.append({'role': 'assistant', 'content': row['content'], 'timestamp': row['timestamp']})
        return jsonify({'history': history})

    @app.route('/api/chat/send', methods=['POST'])
    @login_required(role="user")
    def chat_send_api():
        from ai_module import chat_with_providers
        from config import MAIN_MODEL
        from prompts import SYSTEM_PROMPT
        
        data = request.get_json()
        message = data.get('message', '').strip()
        if not message:
            return jsonify({'reply': ''})
        
        username = session['username']
        user = get_user_by_username(username)
        if not user:
            return jsonify({'reply': '(Błąd użytkownika)'}), 400
        user_id = user['id']
        
        # Save user message to chat_history
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (role, content, user_id, timestamp) VALUES (?, ?, ?, ?) ",
                ('user', message, user_id, datetime.utcnow())
            )
        
        # Get chat history
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT ch.content, ch.timestamp, ch.user_id, u.username"
                " FROM chat_history ch"
                " LEFT JOIN users u ON ch.user_id = u.id"
                " WHERE ch.user_id = ? OR ch.user_id IS NULL"
                " ORDER BY ch.id ASC",
                (user_id,)
            ).fetchall()
        
        chat_msgs = []
        for row in rows:
            if row['user_id'] == user_id:
                chat_msgs.append({'role': 'user', 'content': row['content']})
            else:
                chat_msgs.append({'role': 'assistant', 'content': row['content']})
        
        chat_msgs.insert(0, {'role': 'system', 'content': SYSTEM_PROMPT + '\nYou are now in a text chat with the user.'})

        # AI Response processing
        ai_response = chat_with_providers(MAIN_MODEL, chat_msgs)
        ai_content = ai_response["message"]["content"].strip() if ai_response and ai_response.get("message", {}).get("content") else None
        reply = ""
        
        if ai_content:
            try:
                parsed = None
                try:
                    parsed = json.loads(ai_content)
                except Exception:
                    pass
                
                if isinstance(parsed, dict) and (parsed.get('command') or parsed.get('tool')):
                    # Tool call detected
                    ai_command = parsed.get('command') or parsed.get('tool')
                    ai_params = parsed.get('params', '')
                    ai_text = parsed.get('text', '')
                    reply = ai_text or ''
                    
                    # Dynamic tool handler loading
                    tool_modules = ['modules.search_module', 'modules.memory_module', 'modules.api_module', 
                                   'modules.deepseek_module', 'modules.see_screen_module', 'modules.open_web_module']
                    handler = None
                    for mod_name in tool_modules:
                        try:
                            mod = importlib.import_module(mod_name)
                            if hasattr(mod, 'register'):
                                reg = mod.register()
                                if reg.get('command') == ai_command or ai_command in reg.get('aliases', []):
                                    handler = reg.get('handler')
                                    break
                        except Exception:
                            continue
                    
                    if handler:
                        sig = inspect.signature(handler)
                        args_to_pass = {}
                        if 'params' in sig.parameters:
                            args_to_pass['params'] = ai_params
                        if 'conversation_history' in sig.parameters:
                            args_to_pass['conversation_history'] = chat_msgs
                        if 'user_lang' in sig.parameters:
                            args_to_pass['user_lang'] = None
                        if 'user' in sig.parameters:
                            args_to_pass['user'] = username
                        
                        try:
                            if inspect.iscoroutinefunction(handler):
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                tool_result = loop.run_until_complete(handler(**args_to_pass))
                                loop.close()
                            else:
                                tool_result = handler(**args_to_pass)
                        except Exception as e:
                            tool_result = f"Błąd podczas wywołania funkcji '{ai_command}': {e}"
                        
                        if isinstance(tool_result, tuple):
                            reply = str(tool_result[0])
                        elif tool_result is not None:
                            reply = str(tool_result)
                        else:
                            reply = ai_text or f"(Brak odpowiedzi narzędzia {ai_command})"
                    else:
                        reply = ai_text or f"(Nie znaleziono handlera dla komendy {ai_command})"
                elif isinstance(parsed, dict) and 'text' in parsed:
                    reply = parsed['text']
                else:
                    reply = ai_content
            except Exception as e:
                reply = f"(Błąd AI: {e})"
        else:
            reply = "(Brak odpowiedzi AI)"
        
        # Save AI response to chat_history
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO chat_history (role, content, user_id, timestamp) VALUES (?, ?, ?, ?)",
                ('assistant', reply, None, datetime.utcnow())
            )
        
        return jsonify({'reply': reply})

    @app.route('/api/chat/clear', methods=['POST'])
    @login_required(role="user")
    def chat_clear_api():
        username = session['username']
        user = get_user_by_username(username)
        if not user:
            return jsonify({'success': False})
        user_id = user.id
        
        with get_db_connection() as conn:
            conn.execute(
                "DELETE FROM chat_history WHERE user_id = ?",
                (user_id,)
            )
        return jsonify({'success': True})

    # --- Plugin Management API ---
    @app.route('/api/plugins', methods=['GET'])
    @login_required(role="dev")
    def api_plugins():
        """API endpoint for plugin list and status."""
        from config import BASE_DIR
        plugins_file = os.path.join(BASE_DIR, 'plugins_state.json')
        modules_dir = os.path.join(BASE_DIR, 'modules')
        plugins = {}
        try:
            if os.path.exists(plugins_file):
                with open(plugins_file, 'r', encoding='utf-8') as f:
                    plugins_data = json.load(f)
                    if 'plugins' in plugins_data:
                        plugins = plugins_data['plugins']
                    else:
                        plugins = plugins_data
            
            if os.path.exists(modules_dir):
                for fname in os.listdir(modules_dir):
                    if fname.endswith('_module.py'):
                        name = fname[:-3]
                        if name not in plugins:
                            plugins[name] = {'enabled': True}
            return jsonify(plugins)
        except Exception as e:
            logger.error(f"Failed to load plugins: {e}", exc_info=True)
            return jsonify({})

    @app.route('/api/plugins/<name>/enable', methods=['POST'])
    @login_required(role="dev")
    def api_plugin_enable(name):
        """Enable a plugin by name."""
        plugins_file = os.path.join(os.path.dirname(__file__), '..', '..', 'plugins_state.json')
        try:
            state = {}
            if os.path.exists(plugins_file):
                with open(plugins_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            plugins = state.get('plugins', {})
            plugins.setdefault(name, {})
            plugins[name]['enabled'] = True
            state['plugins'] = plugins
            with open(plugins_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            try:
                get_assistant_instance().load_plugins()
            except Exception:
                pass
            return jsonify({"status": "enabled"}), 200
        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route('/api/plugins/<name>/disable', methods=['POST'])
    @login_required(role="dev")
    def api_plugin_disable(name):
        """Disable a plugin by name."""
        plugins_file = os.path.join(os.path.dirname(__file__), '..', '..', 'plugins_state.json')
        try:
            state = {}
            if os.path.exists(plugins_file):
                with open(plugins_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            plugins = state.get('plugins', {})
            plugins.setdefault(name, {})
            plugins[name]['enabled'] = False
            state['plugins'] = plugins
            with open(plugins_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            try:
                get_assistant_instance().load_plugins()
            except Exception:
                pass
            return jsonify({"status": "disabled"}), 200
        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    # --- Voice Upload API ---
    @app.route('/api/voice_upload', methods=['POST'])
    def voice_upload():
        """Handle audio file upload from web UI."""
        if 'audio' not in request.files:
            return jsonify({'error': 'Brak pliku audio.'}), 400
        
        audio_file = request.files['audio']
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
            temp_path = tmp.name
        audio_file.save(temp_path)
        
        try:
            wav_path = convert_audio(temp_path)
            text = transcribe_audio(wav_path)
        except Exception:
            text = ''
        finally:
            cleanup_files(temp_path, locals().get('wav_path', ''))
        
        return jsonify({'text': text})

    # --- Logs API ---
    @app.route('/api/logs')
    @login_required()
    def api_logs():
        level = request.args.get('level', 'ALL')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 100))
        log_path = os.path.join(os.path.dirname(__file__), '..', '..', 'user_data', 'assistant.log')
        
        try:
            if not os.path.exists(log_path):
                logger.warning(f"Log file not found at {log_path}")
                return jsonify({
                    'logs': ["Log file not found. A new log file will be created when new events occur."],
                    'page': 1, 
                    'total_pages': 1, 
                    'total_lines': 1
                })
            
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                with open(log_path, 'r', encoding='latin-1', errors='ignore') as f:
                    lines = f.readlines()
            
            if level != 'ALL':
                lines = [l for l in lines if f'- {level} -' in l]
            
            total_lines = len(lines)
            total_pages = max(1, (total_lines + page_size - 1) // page_size)
            page = max(1, min(page, total_pages))
            start = (page - 1) * page_size
            end = min(start + page_size, total_lines)
            
            logs = lines[start:end] if start < total_lines else []
            
            cleaned_logs = []
            for line in logs:
                if isinstance(line, bytes):
                    try:
                        line = line.decode('utf-8', errors='ignore')
                    except:
                        line = str(line)
                line = ''.join(c if c.isprintable() or c in '\n\r\t' else ' ' for c in line)
                cleaned_logs.append(line)
                
            return jsonify({
                'logs': cleaned_logs, 
                'page': page, 
                'total_pages': total_pages, 
                'total_lines': total_lines
            })
            
        except Exception as e:
            logger.error(f"Error reading logs: {e}", exc_info=True)
            return jsonify({
                'logs': [f"Error reading logs: {str(e)}"], 
                'page': 1, 
                'total_pages': 1, 
                'total_lines': 1
            }), 500

    @app.route('/api/logs/download')
    @login_required()
    def download_logs():
        """Download the current and rotated log files as a zip archive."""
        log_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        log_files = glob.glob(os.path.join(log_dir, 'user_data', 'assistant.log*'))
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for log_file in log_files:
                arcname = os.path.basename(log_file)
                zf.write(log_file, arcname)
        mem_zip.seek(0)
        return send_file(mem_zip, mimetype='application/zip', as_attachment=True, download_name='logs.zip')

    # --- Analytics API ---
    @app.route('/api/analytics', methods=['GET'])
    @login_required()
    def api_analytics():
        """API endpoint for usage statistics (dashboard)."""
        try:
            from utils.history_manager import get_conversation_history
            history = get_conversation_history()
            msg_count = len(history)
            unique_users = list({entry.get('user', 'unknown') for entry in history})
            avg_response_time = sum(entry.get('response_time', 0) for entry in history if entry.get('response_time')) / msg_count if msg_count else 0
            last_query_time = max((entry.get('timestamp', 0) for entry in history), default=None)
            
            from datetime import date
            today = date.today()
            today_queries = sum(1 for entry in history
                                if entry.get('timestamp')
                                and datetime.fromisoformat(str(entry['timestamp'])).date() == today)
            last_query = next((entry.get('content') for entry in reversed(history)
                                if entry.get('role') == 'user'), None)
            return jsonify({
                'msg_count': msg_count,
                'unique_users': unique_users,
                'avg_response_time': avg_response_time,
                'last_query_time': last_query_time,
                'today_queries': today_queries,
                'last_query': last_query
            })
        except Exception as e:
            logger.error(f"Failed to calculate analytics: {e}", exc_info=True)
            return jsonify({
                'msg_count': 0,
                'unique_users': [],
                'avg_response_time': 0,
                'last_query_time': None,
                'today_queries': 0,
                'last_query': None
            })

import os
import sys
import json
import time
import asyncio
import platform
import subprocess
import threading
from datetime import datetime
# Ensure parent directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from flask import request, jsonify, session, current_app, Response
from core.auth import login_required
from core.config import load_main_config, save_main_config, MAIN_CONFIG_FILE, DEFAULT_CONFIG, _config, logger
from utils.history_manager import get_conversation_history, clear_conversation_history, load_ltm, save_ltm
from utils.audio_utils import get_audio_input_devices, get_assistant_instance
from server.database_models import (
    get_user_by_username,
    get_user_password_hash,
    list_users,
    add_user,
    delete_user,
    update_user,
    get_memories,
    add_memory,
    delete_memory,
)
from server.performance_monitor import (
    get_average_times,
    measure_performance,
    clear_performance_stats,
)
# Import benchmark manager
from utils.benchmark_manager import run_assistant_benchmarks as start_benchmarks, get_benchmark_status
# Import onboarding module for completion handling

def setup_api_routes(app, assistant_queue):
    """Setup all API routes for the application."""
    
    # --- Configuration API ---
    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        """Get or update assistant configuration."""
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
            _config.clear(); _config.update(merged)
            
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

    # --- Audio Devices API ---
    @app.route('/api/audio/devices', methods=['GET'])
    @login_required
    def api_audio_devices():
        """API endpoint to get the list of audio input devices."""
        devices = get_audio_input_devices()
        return jsonify(devices)

    @app.route('/api/audio/microphones', methods=['GET'])
    def api_microphones():
        """Return list of available microphone devices."""
        try:
            import sounddevice as sd
            devices = [
                {
                    "id": idx,
                    "name": dev["name"],
                    "is_default": idx == sd.default.device[0],
                }
                for idx, dev in enumerate(sd.query_devices())
                if dev.get("max_input_channels", 0) > 0
            ]
            return jsonify(devices)
        except Exception as e:
            logger.error(f"Error fetching microphones: {e}", exc_info=True)
            return jsonify([{"id": "-1", "name": f"Error retrieving devices: {e}", "is_default": False}]), 500

    # --- User Management API ---
    @app.route('/api/users', methods=['GET', 'POST'])
    @login_required(role="dev")
    def api_users():
        """API endpoint to list and add users."""
        if request.method == 'POST':
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
                role = data.get('role', 'user')
                display_name = data.get('display_name', '')
                ai_persona = data.get('ai_persona', '')
                personalization = data.get('personalization', '')
                
                if not username or not password:
                    return jsonify({"error": "Username and password are required"}), 400
                
                if get_user_by_username(username):
                    return jsonify({"error": "User already exists"}), 400
                
                add_user(
                    username=username,
                    password=password,
                    role=role,
                    display_name=display_name,
                    ai_persona=ai_persona,
                    personalization=personalization
                )
                logger.info(f"User created: {username}")
                return jsonify({"success": True})
            except Exception as e:
                logger.error(f"Error adding user: {str(e)}")
                return jsonify({"error": str(e)}), 500
        else:  # GET
            try:
                users = list_users()
                return jsonify(users)
            except Exception as e:
                logger.error(f"Error listing users: {str(e)}")
                return jsonify({"error": str(e)}), 500
    
    @app.route('/api/users/<username>', methods=['DELETE'])
    @login_required(role="dev")
    def api_user_delete(username):
        """API endpoint to delete a user."""
        try:
            if username == 'dev':
                return jsonify({"error": "Cannot delete dev user"}), 400
            
            if not get_user_by_username(username):
                return jsonify({"error": "User not found"}), 404
            
            delete_user(username)
            logger.info(f"User deleted: {username}")
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # --- History API ---
    @app.route('/api/history', methods=['GET', 'DELETE'])
    @login_required()
    def api_history():
        """API endpoint for getting and clearing conversation history."""
        if request.method == 'DELETE':
            logger.warning(f"Request to clear history received from user '{session.get('username')}'.")
            try:
                if clear_conversation_history():
                    logger.info("Conversation history cleared successfully.")
                    return jsonify({"message": "Conversation history cleared and archived."}), 200
                else:
                    logger.error("Failed to clear conversation history.")
                    return jsonify({"error": "Failed to clear history."}), 500
            except Exception as e:
                logger.error(f"Unexpected error during history clearing: {e}", exc_info=True)
                return jsonify({"error": "An unexpected server error occurred."}), 500
        else:  # GET
            logger.info(f"History requested by user '{session.get('username')}'.")
            history = get_conversation_history()
            return jsonify(history)

    # --- Assistant Control API ---
    @app.route('/api/activate', methods=['POST'])
    @login_required()
    def api_activate():
        """API endpoint to manually trigger voice listening (bypass wake word)."""
        logger.info(f"Manual activation requested via Web UI.")
        if assistant_queue:
            try:
                assistant_queue.put({"type": "trigger_listen"})
                logger.info("Sent 'trigger_listen' command to assistant process.")
                return jsonify({"message": "Activation request sent to assistant."}), 202
            except Exception as e:
                logger.error(f"Error sending 'trigger_listen' command via queue: {e}")
                return jsonify({"error": f"Failed to send activation command: {e}"}), 500
        logger.warning("Cannot trigger manual listen: Assistant queue not available.")
        return jsonify({"error": "Assistant connection not available."}), 503

    @app.route('/api/status', methods=['GET'])
    # @login_required() # Removed for Tauri overlay access
    def api_status():
        """API endpoint for assistant status (for dashboard polling)."""
        lock_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assistant_restarting.lock')
        if os.path.exists(lock_path):
            status_str = "Restarting"
        else:
            status_str = "Online"
        current_config = load_main_config()
        assistant = get_assistant_instance()
        status = {
            "status": status_str,
            "wake_word": current_config.get('WAKE_WORD', 'N/A'),
            "stt_engine": "Whisper",
            "mic_device_id": current_config.get('MIC_DEVICE_ID', 'Not Set'),
            "is_listening": getattr(assistant, 'is_listening', False),
            "is_speaking": getattr(assistant, 'is_speaking', False),
            "text": getattr(assistant, 'last_tts_text', "")
        }
        return jsonify(status)

    # --- System Control API ---
    @app.route('/api/restart/assistant', methods=['POST'])
    @login_required()
    def restart_assistant():
        """Endpoint to restart the assistant process."""
        logger.warning("[WEB] Restart assistant requested via dashboard API.")
        lock_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assistant_restarting.lock')
        with open(lock_path, 'w') as f:
            f.write('restarting')
        if platform.system() == 'Windows':
            subprocess.Popen(['powershell.exe', '-Command', 'Start-Process', 'python', 'main.py', '-WindowStyle', 'Hidden'])
        else:
            subprocess.Popen(['nohup', 'python3', 'main.py', '&'])
        logger.warning("[WEB] Attempted to start new assistant process.")
        return jsonify({"message": "Restarting assistant..."}), 202

    @app.route('/api/restart/web', methods=['POST'])
    @login_required()
    def restart_web():
        logger.warning("[WEB] Restart web panel requested via dashboard API.")
        lock_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assistant_restarting.lock')
        with open(lock_path, 'w') as f:
            f.write('restarting')
        os._exit(3)
        return jsonify({"message": "Restarting web panel..."}), 202

    @app.route('/api/stop/assistant', methods=['POST'])
    @login_required()
    def stop_assistant():
        logger.warning("[WEB] Stop assistant requested via dashboard API.")
        lock_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assistant_stop.lock')
        with open(lock_path, 'w') as f:
            f.write('stop')
        return jsonify({"message": "Wysłano żądanie zatrzymania asystenta."}), 202

    # --- Long-Term Memory API ---
    @app.route('/api/long_term_memory', methods=['GET', 'POST', 'DELETE'])
    @login_required(role="dev")
    def api_long_term_memory():
        """API endpoint for long-term memory management."""
        logger.info(f"LTM API endpoint accessed (Method: {request.method}) by user '{session.get('username')}'.")
        if request.method == 'POST':
            entry = request.json
            if not isinstance(entry, dict) or not entry.get('content'):
                return jsonify({"error": "Invalid LTM entry format."}), 400
            ltm = load_ltm()
            ltm.append({"content": entry['content'], "timestamp": time.time()})
            if save_ltm(ltm):
                return jsonify({"message": "LTM entry added."}), 200
            else:
                return jsonify({"error": "Failed to save LTM."}), 500
        elif request.method == 'DELETE':
            if save_ltm([]):
                return jsonify({"message": "LTM cleared."}), 200
            else:
                return jsonify({"error": "Failed to clear LTM."}), 500
        else:  # GET
            ltm = load_ltm()
            return jsonify(ltm)

    @app.route('/api/ltm/get', methods=['GET'])
    @login_required()
    def get_memories_api():
        query = request.args.get('query', request.args.get('q', ''))
        limit = request.args.get('limit', default=50, type=int)
        try:
            memories = get_memories(query=query, limit=limit)
            memories_list = [
                {
                    "id": mem.id,
                    "content": mem.content,
                    "user": mem.user,
                    "timestamp": mem.timestamp.isoformat()
                }
                for mem in memories
            ]
            return jsonify(memories_list)
        except Exception as e:
            logger.error(f"Error fetching memories via API: {e}")
            return jsonify({"error": "Failed to fetch memories"}), 500

    @app.route('/api/ltm/add', methods=['POST'])
    @login_required()
    def add_memory_api():
        data = request.json
        content = data.get('content')
        user = session.get('username', 'unknown')
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        try:
            memory_id = add_memory(content=content, user=user)
            logger.info(f"Memory added via API by {user}: ID {memory_id}")
            return jsonify({'success': True, 'id': memory_id}), 201
        except Exception as e:
            logger.error(f"Error adding memory via API: {e}")
            return jsonify({'error': 'Failed to add memory'}), 500

    @app.route('/api/ltm/delete/<int:memory_id>', methods=['DELETE'])
    @login_required()
    def delete_memory_api(memory_id):
        try:
            success = delete_memory(memory_id)
            if success:
                logger.info(f"Memory {memory_id} deleted via API by {session.get('username')}")
                return jsonify({'success': True})
            else:
                logger.warning(f"Attempt to delete non-existent memory {memory_id} via API")
                return jsonify({'error': 'Memory not found'}), 404
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id} via API: {e}")
            return jsonify({'error': 'Failed to delete memory'}), 500

    # --- Performance Stats API ---
    @app.route('/api/performance_stats', methods=['GET', 'DELETE'])
    @login_required
    @measure_performance
    def api_performance_stats():
        """API endpoint to get or clear performance statistics."""
        if request.method == 'DELETE':
            if 'username' in session and session.get('role') == 'dev':
                if clear_performance_stats():
                    logger.info(f"Performance stats cleared by user '{session['username']}'.")
                    return jsonify({"message": "Performance stats cleared successfully."}), 200
                else:
                    logger.error("Failed to clear performance stats.")
                    return jsonify({"error": "Failed to clear performance stats."}), 500
            else:
                return jsonify({"error": "Unauthorized to clear stats."}), 403
        else:  # GET
            stats = get_average_times()
            return jsonify(stats)

    # --- Benchmark API ---
    @app.route('/api/run_benchmarks', methods=['POST'])
    @login_required(role="dev")
    def api_run_benchmarks():
        """API endpoint to start assistant benchmarks."""
        try:
            logger.info(f"Benchmark requested by user '{session.get('username')}'.")
              # Start benchmarks in background thread
            result = start_benchmarks()
            
            return jsonify({"status": "started", "message": "Benchmarks started successfully."}), 200
            
        except Exception as e:
            logger.error(f"Error starting benchmarks: {e}", exc_info=True)
            return jsonify({"error": f"Failed to start benchmarks: {str(e)}"}), 500

    @app.route('/api/benchmark_status', methods=['GET'])
    @login_required(role="dev")  
    def api_benchmark_status():
        """API endpoint to get current benchmark status."""
        try:
            status = get_benchmark_status()
            return jsonify(status), 200
        except Exception as e:
            logger.error(f"Error getting benchmark status: {e}", exc_info=True)
            return jsonify({"error": f"Failed to get benchmark status: {str(e)}"}), 500

    @app.route('/api/bench_status', methods=['GET'])
    @login_required(role="dev")  
    def api_bench_status():
        """API endpoint to get current benchmark status (alias)."""
        try:
            status = get_benchmark_status()
            return jsonify(status), 200
        except Exception as e:
            logger.error(f"Error getting benchmark status: {e}", exc_info=True)
            return jsonify({"error": f"Failed to get benchmark status: {str(e)}"}), 500

    # --- Test Management API ---
    @app.route('/api/run_tests', methods=['POST'])
    @login_required(role="dev")
    def api_run_tests():
        """API endpoint to run assistant tests."""
        try:
            logger.info(f"Tests requested by user '{session.get('username')}'.")
            
            # For now, run the benchmark system for testing (can be expanded later)            # Start tests (using benchmarks for now)
            result = start_benchmarks()
            
            return jsonify({"status": "started", "message": "Tests started successfully."}), 200
            
        except Exception as e:
            logger.error(f"Error starting tests: {e}", exc_info=True)
            return jsonify({"error": f"Failed to start tests: {str(e)}"}), 500

    @app.route('/api/test_status', methods=['GET'])
    @login_required(role="dev")
    def api_test_status():
        """API endpoint to get current test status."""
        try:
            # Use the same benchmark status for tests (can be separated later)
            status = get_benchmark_status()
            return jsonify(status), 200
        except Exception as e:
            logger.error(f"Error getting test status: {e}", exc_info=True)
            return jsonify({"error": f"Failed to get test status: {str(e)}"}), 500

    # --- Schedule Status API ---
    @app.route('/api/schedule_status', methods=['GET'])
    @login_required(role="dev")
    def api_schedule_status():
        """API endpoint to get scheduled task status."""
        try:
            # For now, return a simple schedule status
            # This can be expanded to include actual scheduling system later
            status = {
                "active": False,
                "interval": None,
                "next_run": None,
                "last_run": None,
                "type": "benchmark"
            }
            
            # Check if there's a configuration for scheduling
            config = load_main_config()
            if config.get('BENCHMARK_SCHEDULE', {}).get('enabled', False):
                status.update({
                    "active": True,
                    "interval": config['BENCHMARK_SCHEDULE'].get('interval_minutes', 60),
                    "type": config['BENCHMARK_SCHEDULE'].get('type', 'benchmark')
                })
            
            return jsonify(status), 200
            
        except Exception as e:
            logger.error(f"Error getting schedule status: {e}", exc_info=True)
            return jsonify({"error": f"Failed to get schedule status: {str(e)}"}), 500    @app.route('/api/test_history', methods=['GET'])
    @login_required(role="dev")
    def api_test_history():
        """API endpoint to get test history."""
        try:
            # For now, return empty history - can be implemented later with actual storage
            history = []
            return jsonify(history), 200
        except Exception as e:
            logger.error(f"Error getting test history: {e}", exc_info=True)
            return jsonify({"error": f"Failed to get test history: {str(e)}"}), 500

    # --- Onboarding API ---
    @app.route('/api/complete-onboarding', methods=['POST'])
    def api_complete_onboarding():
        """API endpoint to mark onboarding as complete."""
        try:
            # Legacy onboarding module removed; assume success
            success = True
            
            if success:
                # Auto-login the dev user after onboarding completion
                session['username'] = 'dev'
                session.permanent = True
                
                logger.info("Onboarding completed successfully via API, dev user auto-logged in")
                return jsonify({"success": True, "message": "Onboarding completed successfully"}), 200
            else:
                logger.error("Failed to mark onboarding as complete")
                return jsonify({"success": False, "error": "Failed to mark onboarding as complete"}), 500
                
        except Exception as e:
            logger.error(f"Error completing onboarding: {e}", exc_info=True)
            return jsonify({"success": False, "error": f"Failed to complete onboarding: {str(e)}"}), 500

    # --- SSE Status Stream ---
    @app.route('/status/stream')
    def status_stream():
        """Server-Sent Events endpoint for real-time status updates."""
        def generate():
            import time
            import json
            # Simplified status retrieval without shared_state module
            def load_assistant_state():
                return {}
            
            # Debug logging
            import logging
            sse_logger = logging.getLogger('sse_endpoint')
            
            last_status = {}
            
            while True:
                try:
                    lock_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assistant_restarting.lock')
                    if os.path.exists(lock_path):
                        status_str = "Restarting"
                    else:
                        status_str = "Online"
                    
                    current_config = load_main_config()
                    
                    # Try to read state from shared file first
                    shared_state = load_assistant_state()
                    sse_logger.debug(f"SSE: Loaded shared state: {shared_state}")
                    
                    if shared_state:
                        is_listening = shared_state.get('is_listening', False)
                        is_speaking = shared_state.get('is_speaking', False)
                        last_text = shared_state.get('last_tts_text', "")
                        wake_word_detected = shared_state.get('wake_word_detected', False)
                    else:
                        # Fallback to assistant instance if shared state fails
                        assistant = get_assistant_instance()
                        is_listening = getattr(assistant, 'is_listening', False) if assistant else False
                        is_speaking = getattr(assistant, 'is_speaking', False) if assistant else False
                        last_text = getattr(assistant, 'last_tts_text', "") if assistant else ""
                        wake_word_detected = getattr(assistant, 'wake_word_detected', False) if assistant else False
                    
                    current_status = {
                        "status": status_str,
                        "wake_word": current_config.get('WAKE_WORD', 'N/A'),
                        "stt_engine": "Whisper",
                        "mic_device_id": current_config.get('MIC_DEVICE_ID', 'Not Set'),
                        "is_listening": is_listening,
                        "is_speaking": is_speaking,
                        "text": last_text,
                        "wake_word_detected": wake_word_detected
                    }
                      # Send initial status or when changed
                    if current_status != last_status or not last_status:
                        data = json.dumps(current_status)
                        yield f"data: {data}\n\n"
                        last_status = current_status.copy()
                        # Only log significant state changes
                        if current_status.get('is_listening') or current_status.get('is_speaking') or current_status.get('wake_word_detected'):
                            logger.info(f"SSE sent: {current_status}")
                            sse_logger.info(f"Status update: {current_status}")  # Debug log
                    
                    time.sleep(0.1)  # Check every 100ms for changes
                    
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    time.sleep(1)
        
        return Response(generate(), mimetype='text/event-stream',
                       headers={'Cache-Control': 'no-cache',
                               'Connection': 'keep-alive',
                               'Access-Control-Allow-Origin': '*',
                               'Access-Control-Allow-Headers': 'Content-Type',
                               'Access-Control-Allow-Methods': 'GET'})

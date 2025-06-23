#!/usr/bin/env python3
"""
GAJA Assistant - Overlay Debug Tools
Simple Windows UI for testing all overlay functions individually.

Following AGENTS.md guidelines:
- Async-first architecture
- Comprehensive test coverage
- Clear logging and error handling
- Modular design
"""

import asyncio
import ctypes
import ctypes.wintypes as wintypes
import json
import logging
import threading
import tkinter as tk
from ctypes import wintypes
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk
from typing import Optional

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Add Windows API functions for overlay visibility fix
def fix_overlay_transparency():
    """Fix overlay window transparency if it's invisible due to alpha=0."""
    try:
        # Find Gaja Overlay window
        def enum_windows_callback(hwnd, lParam):
            window_text = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, window_text, 512)
            window_title = window_text.value

            if "gaja overlay" in window_title.lower():
                windows.append(hwnd)
            return True

        windows = []
        enum_windows_proc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
        )
        ctypes.windll.user32.EnumWindows(enum_windows_proc(enum_windows_callback), 0)

        if not windows:
            return "❌ Nie znaleziono okna Gaja Overlay"

        hwnd = windows[0]  # First found window

        # Check current alpha
        alpha = ctypes.c_ubyte()
        layered = ctypes.windll.user32.GetLayeredWindowAttributes(
            hwnd, None, ctypes.byref(alpha), None
        )

        if layered and alpha.value == 0:
            # Fix transparency - set to full opacity
            ctypes.windll.user32.SetLayeredWindowAttributes(
                hwnd, 0, 255, 2
            )  # LWA_ALPHA

            # Also ensure window is shown and topmost
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
            ctypes.windll.user32.SetWindowPos(
                hwnd, -1, 0, 0, 0, 0, 0x0003 | 0x0040
            )  # SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW

            return f"✅ Naprawiono przezroczystość overlay (było: {alpha.value}/255, teraz: 255/255)"
        elif layered:
            return f"✅ Overlay ma poprawną przezroczystość: {alpha.value}/255"
        else:
            return "✅ Overlay nie ma warstwy przezroczystości (OK)"

    except Exception as e:
        return f"❌ Błąd naprawy przezroczystości: {e}"


class OverlayDebugToolsGUI:
    """Main GUI class for overlay debug tools.

    Provides comprehensive testing interface for all overlay functions.
    """

    def __init__(self):
        """Initialize the debug tools GUI."""
        self.root = tk.Tk()
        self.root.title("GAJA Overlay Debug Tools")
        self.root.geometry("800x900")

        # State variables for tracking overlay status
        self.current_status = {
            "visible": False,
            "status": "Offline",
            "text": "",
            "is_listening": False,
            "is_speaking": False,
            "wake_word_detected": False,
        }

        # Configuration
        self.server_port = "5001"  # Default dev port
        self.base_url = f"http://localhost:{self.server_port}"

        # HTTP session for async requests
        self.session: Optional[aiohttp.ClientSession] = None

        # Setup UI components
        self._setup_ui()

        # Start async event loop in background thread
        self.loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()

        logger.info("Overlay Debug Tools initialized")

    def _run_async_loop(self) -> None:
        """Run async event loop in background thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _setup_ui(self) -> None:
        """Setup the main UI components."""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Status Control
        self._setup_status_tab(notebook)

        # Tab 2: Text Testing
        self._setup_text_tab(notebook)

        # Tab 3: Animation Testing
        self._setup_animation_tab(notebook)

        # Tab 4: System Testing
        self._setup_system_tab(notebook)

        # Tab 5: Log Viewer
        self._setup_log_tab(notebook)

        # Status bar at bottom
        self._setup_status_bar()

    def _setup_status_tab(self, notebook: ttk.Notebook) -> None:
        """Setup the status control tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Status Control")

        # Current Status Display
        status_group = ttk.LabelFrame(frame, text="Current Overlay Status")
        status_group.pack(fill="x", padx=10, pady=5)

        self.status_display = tk.Text(status_group, height=6, width=80)
        self.status_display.pack(padx=10, pady=10)

        # Basic Controls
        controls_group = ttk.LabelFrame(frame, text="Basic Controls")
        controls_group.pack(fill="x", padx=10, pady=5)

        btn_frame = ttk.Frame(controls_group)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame,
            text="Show Overlay",
            command=self._safe_async_call(self._show_overlay),
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame,
            text="Hide Overlay",
            command=self._safe_async_call(self._hide_overlay),
        ).pack(side="left", padx=5)
        ttk.Button(
            btn_frame,
            text="Get Status",
            command=self._safe_async_call(self._get_status),
        ).pack(side="left", padx=5)

        # Status State Controls
        state_group = ttk.LabelFrame(frame, text="Status State Testing")
        state_group.pack(fill="x", padx=10, pady=5)

        # State buttons in grid layout
        state_frame = ttk.Frame(state_group)
        state_frame.pack(pady=10)

        # Row 1: Individual states
        ttk.Button(
            state_frame,
            text="Set Listening",
            command=self._safe_async_call(
                lambda: self._set_status_state(is_listening=True)
            ),
        ).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(
            state_frame,
            text="Set Speaking",
            command=self._safe_async_call(
                lambda: self._set_status_state(is_speaking=True)
            ),
        ).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(
            state_frame,
            text="Set Wake Word",
            command=self._safe_async_call(
                lambda: self._set_status_state(wake_word_detected=True)
            ),
        ).grid(row=0, column=2, padx=5, pady=2)

        # Row 2: Combined states
        ttk.Button(
            state_frame,
            text="Listening + Text",
            command=self._safe_async_call(
                lambda: self._set_status_state(
                    is_listening=True, text="Listening for command..."
                )
            ),
        ).grid(row=1, column=0, padx=5, pady=2)
        ttk.Button(
            state_frame,
            text="Speaking + Text",
            command=self._safe_async_call(
                lambda: self._set_status_state(
                    is_speaking=True, text="Hello! I'm responding to your query."
                )
            ),
        ).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(
            state_frame,
            text="Clear All States",
            command=self._safe_async_call(lambda: self._set_status_state()),
        ).grid(row=1, column=2, padx=5, pady=2)

        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame,
            text="Auto-refresh status every 2 seconds",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh,
        ).pack(pady=5)

    def _setup_text_tab(self, notebook: ttk.Notebook) -> None:
        """Setup the text testing tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Text Testing")

        # Text Input
        input_group = ttk.LabelFrame(frame, text="Text Content Testing")
        input_group.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(input_group, text="Enter text to display in overlay:").pack(
            anchor="w", padx=10, pady=5
        )

        self.text_input = scrolledtext.ScrolledText(input_group, height=8, width=80)
        self.text_input.pack(fill="both", expand=True, padx=10, pady=5)

        # Preset text buttons
        presets_frame = ttk.Frame(input_group)
        presets_frame.pack(fill="x", padx=10, pady=5)

        # Text length presets
        ttk.Button(
            presets_frame,
            text="Short Text",
            command=lambda: self._insert_preset_text("Hello!"),
        ).pack(side="left", padx=2)
        ttk.Button(
            presets_frame,
            text="Medium Text",
            command=lambda: self._insert_preset_text(
                "This is a medium length message to test text display capabilities."
            ),
        ).pack(side="left", padx=2)
        ttk.Button(
            presets_frame,
            text="Long Text",
            command=lambda: self._insert_preset_text(
                "This is a very long message that should test the overlay's ability to handle extended text content. It includes multiple sentences and should demonstrate text wrapping and sizing behavior in the overlay interface."
            ),
        ).pack(side="left", padx=2)
        ttk.Button(
            presets_frame,
            text="Very Long Text",
            command=lambda: self._insert_preset_text(
                "This is an extremely long message designed to test the maximum text handling capabilities of the overlay system. "
                * 3
            ),
        ).pack(side="left", padx=2)

        # Special character presets
        special_frame = ttk.Frame(input_group)
        special_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            special_frame,
            text="Polish Text",
            command=lambda: self._insert_preset_text(
                "Cześć! Jak się masz? Testujemy polskie znaki: ąćęłńóśźż"
            ),
        ).pack(side="left", padx=2)
        ttk.Button(
            special_frame,
            text="Unicode Emoji",
            command=lambda: self._insert_preset_text("Testing emojis: 🚀 🎯 ✨ 🔥 💡 🎉"),
        ).pack(side="left", padx=2)
        ttk.Button(
            special_frame,
            text="Numbers & Symbols",
            command=lambda: self._insert_preset_text("Testing: 123 $%& @#! ()[]{}"),
        ).pack(side="left", padx=2)

        # Action buttons
        action_frame = ttk.Frame(input_group)
        action_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(
            action_frame,
            text="Send Text to Overlay",
            command=self._safe_async_call(self._send_text_to_overlay),
        ).pack(side="left", padx=5)
        ttk.Button(
            action_frame,
            text="Clear Text",
            command=lambda: self.text_input.delete("1.0", tk.END),
        ).pack(side="left", padx=5)
        ttk.Button(
            action_frame,
            text="Clear Overlay Text",
            command=self._safe_async_call(lambda: self._send_text_to_overlay("")),
        ).pack(side="left", padx=5)

    def _setup_animation_tab(self, notebook: ttk.Notebook) -> None:
        """Setup the animation testing tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Animation Testing")

        # Animation Controls
        anim_group = ttk.LabelFrame(frame, text="Animation Testing")
        anim_group.pack(fill="x", padx=10, pady=5)

        # Ball animation tests
        ball_frame = ttk.Frame(anim_group)
        ball_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(ball_frame, text="Ball Animation Tests:").pack(anchor="w")

        ball_btn_frame = ttk.Frame(ball_frame)
        ball_btn_frame.pack(fill="x", pady=5)

        ttk.Button(
            ball_btn_frame,
            text="Show Ball (Listening)",
            command=self._safe_async_call(lambda: self._test_animation("listening")),
        ).pack(side="left", padx=5)
        ttk.Button(
            ball_btn_frame,
            text="Show Ball (Speaking)",
            command=self._safe_async_call(lambda: self._test_animation("speaking")),
        ).pack(side="left", padx=5)
        ttk.Button(
            ball_btn_frame,
            text="Show Ball (Wake Word)",
            command=self._safe_async_call(lambda: self._test_animation("wake_word")),
        ).pack(side="left", padx=5)
        ttk.Button(
            ball_btn_frame,
            text="Hide Ball",
            command=self._safe_async_call(lambda: self._test_animation("idle")),
        ).pack(side="left", padx=5)

        # Status text animation tests
        status_frame = ttk.Frame(anim_group)
        status_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(status_frame, text="Status Text Animation Tests:").pack(anchor="w")

        status_btn_frame = ttk.Frame(status_frame)
        status_btn_frame.pack(fill="x", pady=5)

        ttk.Button(
            status_btn_frame,
            text="Słucham...",
            command=self._safe_async_call(
                lambda: self._set_status_state(is_listening=True)
            ),
        ).pack(side="left", padx=5)
        ttk.Button(
            status_btn_frame,
            text="Odpowiadam...",
            command=self._safe_async_call(
                lambda: self._set_status_state(is_speaking=True)
            ),
        ).pack(side="left", padx=5)
        ttk.Button(
            status_btn_frame,
            text="Przetwarzam...",
            command=self._safe_async_call(
                lambda: self._set_status_state(wake_word_detected=True)
            ),
        ).pack(side="left", padx=5)

        # Sequence testing
        sequence_group = ttk.LabelFrame(frame, text="Animation Sequences")
        sequence_group.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            sequence_group,
            text="Full Interaction Sequence",
            command=self._safe_async_call(self._test_full_sequence),
        ).pack(pady=10)

        # Timing controls
        timing_frame = ttk.Frame(sequence_group)
        timing_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(timing_frame, text="Sequence Timing (seconds):").pack(side="left")
        self.sequence_timing = tk.StringVar(value="2.0")
        ttk.Entry(timing_frame, textvariable=self.sequence_timing, width=10).pack(
            side="left", padx=5
        )

    def _setup_system_tab(self, notebook: ttk.Notebook) -> None:
        """Setup the system testing tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="System Testing")

        # Connection Testing
        conn_group = ttk.LabelFrame(frame, text="Connection Testing")
        conn_group.pack(fill="x", padx=10, pady=5)

        # Port configuration
        port_frame = ttk.Frame(conn_group)
        port_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(port_frame, text="Server Port:").pack(side="left")
        self.port_var = tk.StringVar(value=self.server_port)
        port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10)
        port_entry.pack(side="left", padx=5)

        ttk.Button(port_frame, text="Update Port", command=self._update_port).pack(
            side="left", padx=5
        )

        # Connection tests
        conn_btn_frame = ttk.Frame(conn_group)
        conn_btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(
            conn_btn_frame,
            text="Test Connection",
            command=self._safe_async_call(self._test_connection),
        ).pack(side="left", padx=5)
        ttk.Button(
            conn_btn_frame,
            text="Test API Endpoints",
            command=self._safe_async_call(self._test_api_endpoints),
        ).pack(side="left", padx=5)
        ttk.Button(
            conn_btn_frame,
            text="Test SSE Stream",
            command=self._safe_async_call(self._test_sse_stream),
        ).pack(side="left", padx=5)

        # Performance Testing
        perf_group = ttk.LabelFrame(frame, text="Performance Testing")
        perf_group.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            perf_group,
            text="Rapid State Changes",
            command=self._safe_async_call(self._test_rapid_changes),
        ).pack(side="left", padx=5)
        ttk.Button(
            perf_group,
            text="Large Text Stress Test",
            command=self._safe_async_call(self._test_large_text),
        ).pack(side="left", padx=5)

        # Error Testing
        error_group = ttk.LabelFrame(frame, text="Error Handling Testing")
        error_group.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            error_group,
            text="Test Invalid JSON",
            command=self._safe_async_call(self._test_invalid_json),
        ).pack(side="left", padx=5)
        ttk.Button(
            error_group,
            text="Test Connection Loss",
            command=self._safe_async_call(self._test_connection_loss),
        ).pack(side="left", padx=5)
        # Add input fix buttons
        fix_frame = tk.Frame(frame)
        fix_frame.pack(fill=tk.X, padx=5, pady=5)

        self.fix_transparency_btn = tk.Button(
            fix_frame,
            text="🔧 Napraw przezroczystość overlay",
            command=self.fix_transparency,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.fix_transparency_btn.pack(side=tk.LEFT, padx=5)

        self.fix_input_btn = tk.Button(
            fix_frame,
            text="🚀 Napraw blokowanie wejścia",
            command=self._safe_async_call(self._fix_input_blocking),
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.fix_input_btn.pack(side=tk.LEFT, padx=5)

        self.test_click_through_btn = tk.Button(
            fix_frame,
            text="🔍 Testuj click-through",
            command=self._safe_async_call(self._test_click_through),
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.test_click_through_btn.pack(side=tk.LEFT, padx=5)

        self.fix_visibility_btn = tk.Button(
            fix_frame,
            text="👁️ Napraw widoczność overlay",
            command=self._safe_async_call(self._fix_overlay_visibility),
            bg="#9C27B0",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.fix_visibility_btn.pack(side=tk.LEFT, padx=5)

        # Opacity control
        opacity_frame = tk.Frame(frame)
        opacity_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(opacity_frame, text="Przezroczystość:").pack(side=tk.LEFT, padx=5)

        self.opacity_var = tk.StringVar(value="80")
        opacity_entry = tk.Entry(opacity_frame, textvariable=self.opacity_var, width=5)
        opacity_entry.pack(side=tk.LEFT, padx=2)

        tk.Label(opacity_frame, text="%").pack(side=tk.LEFT)

        opacity_btn = tk.Button(
            opacity_frame,
            text="Ustaw przezroczystość",
            command=self._safe_async_call(self._adjust_opacity),
            bg="#607D8B",
            fg="white",
            font=("Arial", 9),
        )
        opacity_btn.pack(side=tk.LEFT, padx=5)

        # Second row of fix buttons
        fix_frame2 = tk.Frame(frame)
        fix_frame2.pack(fill=tk.X, padx=5, pady=5)

        self.fix_taskbar_btn = tk.Button(
            fix_frame2,
            text="🖥️ Napraw pasek zadań Windows",
            command=self._safe_async_call(self._fix_taskbar_interference),
            bg="#F44336",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.fix_taskbar_btn.pack(side=tk.LEFT, padx=5)

        self.test_taskbar_btn = tk.Button(
            fix_frame2,
            text="🔬 Testuj kompatybilność z paskiem",
            command=self._safe_async_call(self._test_taskbar_compatibility),
            bg="#795548",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.test_taskbar_btn.pack(side=tk.LEFT, padx=5)

        self.rebuild_overlay_btn = tk.Button(
            fix_frame2,
            text="⚡ Przebuduj overlay od nowa",
            command=self._safe_async_call(self._rebuild_overlay_complete),
            bg="#E91E63",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.rebuild_overlay_btn.pack(side=tk.LEFT, padx=5)

    def _setup_log_tab(self, notebook: ttk.Notebook) -> None:
        """Setup the log viewer tab."""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Log Viewer")

        # Log display
        self.log_display = scrolledtext.ScrolledText(frame, height=25, width=100)
        self.log_display.pack(fill="both", expand=True, padx=10, pady=10)

        # Log controls
        log_controls = ttk.Frame(frame)
        log_controls.pack(fill="x", padx=10, pady=5)

        ttk.Button(log_controls, text="Clear Logs", command=self._clear_logs).pack(
            side="left", padx=5
        )
        ttk.Button(log_controls, text="Export Logs", command=self._export_logs).pack(
            side="left", padx=5
        )

        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            log_controls, text="Auto-scroll", variable=self.auto_scroll_var
        ).pack(side="left", padx=10)

    def _setup_status_bar(self) -> None:
        """Setup the status bar at the bottom."""
        self.status_bar = ttk.Label(self.root, text="Ready", relief="sunken")
        self.status_bar.pack(side="bottom", fill="x")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Add message to log display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"

        # Add to log display
        self.log_display.insert(tk.END, log_entry)

        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.log_display.see(tk.END)

        # Update status bar
        self.status_bar.config(text=message)

        # Also log to Python logger
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)

    def _safe_async_call(self, async_func):
        """Safely call async function from sync context."""

        def wrapper():
            if self.loop and not self.loop.is_closed():
                asyncio.run_coroutine_threadsafe(async_func(), self.loop)
            else:
                self._log("Async loop not available", "ERROR")

        return wrapper

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            # Create session with proper connector settings to avoid connection issues
            connector = aiohttp.TCPConnector(
                limit=10,  # Limit concurrent connections
                limit_per_host=5,  # Limit per host
                keepalive_timeout=30,  # Keep connections alive
                enable_cleanup_closed=True,  # Clean up closed connections
            )

            timeout = aiohttp.ClientTimeout(total=10, connect=5)

            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session

    async def _show_overlay(self) -> None:
        """Show the overlay."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/overlay/show") as response:
                if response.status == 200:
                    self._log("Overlay shown successfully")
                    await self._get_status()
                else:
                    self._log(f"Failed to show overlay: {response.status}", "ERROR")
        except Exception as e:
            self._log(f"Error showing overlay: {e}", "ERROR")

    async def _hide_overlay(self) -> None:
        """Hide the overlay."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/overlay/hide") as response:
                if response.status == 200:
                    self._log("Overlay hidden successfully")
                    await self._get_status()
                else:
                    self._log(f"Failed to hide overlay: {response.status}", "ERROR")
        except Exception as e:
            self._log(f"Error hiding overlay: {e}", "ERROR")

    async def _get_status(self) -> None:
        """Get current overlay status."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/status") as response:
                if response.status == 200:
                    data = await response.json()
                    self.current_status.update(data)
                    self._update_status_display()
                    self._log("Status retrieved successfully")
                else:
                    self._log(f"Failed to get status: {response.status}", "ERROR")
        except Exception as e:
            self._log(f"Error getting status: {e}", "ERROR")

    async def _set_status_state(self, **kwargs) -> None:
        """Set overlay status state."""
        # Since there's no direct update endpoint, we'll use available endpoints
        # to simulate different states

        try:
            session = await self._get_session()

            # If we just want to clear states, hide overlay
            if not any(kwargs.values()):
                await self._hide_overlay()
                return

            # If we want to show text, we can trigger a test wakeword with custom text
            if kwargs.get("text"):
                # First show overlay
                await self._show_overlay()

                # Then trigger test wakeword with the text as query
                test_url = f"{self.base_url}/api/test/wakeword?query={kwargs['text']}"
                async with session.get(test_url) as response:
                    if response.status == 200:
                        self._log(f"Status updated with text: {kwargs['text']}")
                    else:
                        self._log(
                            f"Failed to update with text: {response.status}", "WARNING"
                        )

            # For other states, we can show overlay and log what we're testing
            elif (
                kwargs.get("is_listening")
                or kwargs.get("is_speaking")
                or kwargs.get("wake_word_detected")
            ):
                await self._show_overlay()

                state_desc = []
                if kwargs.get("is_listening"):
                    state_desc.append("listening")
                if kwargs.get("is_speaking"):
                    state_desc.append("speaking")
                if kwargs.get("wake_word_detected"):
                    state_desc.append("wake word detected")

                self._log(f"Overlay shown - simulating state: {', '.join(state_desc)}")

            # Refresh status after changes
            await asyncio.sleep(0.5)  # Brief delay for state to update
            await self._get_status()

        except Exception as e:
            self._log(f"Error updating status: {e}", "ERROR")

    def _update_status_display(self) -> None:
        """Update the status display."""
        status_text = json.dumps(self.current_status, indent=2)
        self.status_display.delete("1.0", tk.END)
        self.status_display.insert("1.0", status_text)

    def _insert_preset_text(self, text: str) -> None:
        """Insert preset text into text input."""
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", text)

    async def _send_text_to_overlay(self, text: str = None) -> None:
        """Send text to overlay."""
        if text is None:
            text = self.text_input.get("1.0", tk.END).strip()

        await self._set_status_state(text=text)

    async def _test_animation(self, anim_type: str) -> None:
        """Test specific animation type."""
        animations = {
            "listening": {"is_listening": True, "text": "Słucham..."},
            "speaking": {"is_speaking": True, "text": "Odpowiadam..."},
            "wake_word": {"wake_word_detected": True, "text": "Przetwarzam..."},
            "idle": {"text": ""},
        }

        if anim_type in animations:
            await self._set_status_state(**animations[anim_type])
            self._log(f"Animation test: {anim_type}")

    async def _test_full_sequence(self) -> None:
        """Test full interaction sequence."""
        try:
            timing = float(self.sequence_timing.get())
        except ValueError:
            timing = 2.0

        sequence = [
            (
                "Wake word detected",
                {"wake_word_detected": True, "text": "Przetwarzam..."},
            ),
            ("Listening", {"is_listening": True, "text": "Słucham..."}),
            ("Processing", {"text": "Analizuję polecenie..."}),
            (
                "Speaking",
                {"is_speaking": True, "text": "Oto odpowiedź na Twoje pytanie."},
            ),
            ("Idle", {"text": ""}),
        ]

        self._log("Starting full interaction sequence")

        for step_name, state in sequence:
            self._log(f"Sequence step: {step_name}")
            await self._set_status_state(**state)
            await asyncio.sleep(timing)

        self._log("Full sequence completed")

    def _update_port(self) -> None:
        """Update server port."""
        self.server_port = self.port_var.get()
        self.base_url = f"http://localhost:{self.server_port}"
        self._log(f"Server port updated to: {self.server_port}")

    async def _test_connection(self) -> None:
        """Test connection to server."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/status", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    self._log("✅ Connection successful")
                else:
                    self._log(f"❌ Connection failed: {response.status}", "ERROR")
        except asyncio.TimeoutError:
            self._log("❌ Connection timeout", "ERROR")
        except Exception as e:
            self._log(f"❌ Connection error: {e}", "ERROR")

    async def _test_api_endpoints(self) -> None:
        """Test all API endpoints."""
        endpoints = [
            ("GET", "/api/status"),
            ("GET", "/api/overlay/show"),
            ("GET", "/api/overlay/hide"),
            ("GET", "/api/overlay/status"),
            ("GET", "/api/test/wakeword?query=test"),
            ("GET", "/status/stream"),  # This will timeout, which is expected
        ]

        session = await self._get_session()

        for method, endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"

                if endpoint == "/status/stream":
                    # Special handling for SSE endpoint - use short timeout
                    timeout = aiohttp.ClientTimeout(total=2)
                    try:
                        async with session.get(url, timeout=timeout) as response:
                            status = "✅" if response.status < 400 else "❌"
                            self._log(
                                f"{status} {method} {endpoint}: {response.status}"
                            )
                    except asyncio.TimeoutError:
                        self._log(
                            f"✅ {method} {endpoint}: SSE stream started (timeout expected)"
                        )
                else:
                    async with session.get(url) as response:
                        status = "✅" if response.status < 400 else "❌"
                        self._log(f"{status} {method} {endpoint}: {response.status}")

            except Exception as e:
                self._log(f"❌ {method} {endpoint}: {e}", "ERROR")

    async def _test_sse_stream(self) -> None:
        """Test SSE stream connection."""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/status/stream"

            self._log("Testing SSE stream connection...")

            timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout for test
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    self._log("✅ SSE stream connected")

                    # Read a few events to test
                    count = 0
                    async for line in response.content:
                        if count >= 3:  # Just test first few events
                            break
                        line_str = line.decode().strip()
                        if line_str.startswith("data:"):
                            self._log(f"SSE data: {line_str[:50]}...")
                            count += 1
                        elif line_str:  # Log other non-empty lines too
                            self._log(f"SSE line: {line_str[:30]}...")
                else:
                    self._log(f"❌ SSE stream failed: {response.status}", "ERROR")
        except asyncio.TimeoutError:
            self._log("❌ SSE stream timeout - this is normal for testing", "WARNING")
        except Exception as e:
            self._log(f"❌ SSE stream error: {e}", "ERROR")

    async def _test_rapid_changes(self) -> None:
        """Test rapid state changes."""
        self._log("Testing rapid state changes...")

        states = [
            {"is_listening": True},
            {"is_speaking": True},
            {"wake_word_detected": True},
            {"text": "Quick test"},
            {},  # Clear all
        ]

        for i, state in enumerate(states):
            await self._set_status_state(**state)
            await asyncio.sleep(0.5)  # Rapid changes

        self._log("Rapid changes test completed")

    async def _test_large_text(self) -> None:
        """Test large text handling."""
        large_text = "This is a stress test with very long text content. " * 50
        self._log(f"Testing large text ({len(large_text)} characters)")
        await self._set_status_state(text=large_text)

    async def _test_invalid_json(self) -> None:
        """Test invalid JSON handling."""
        try:
            session = await self._get_session()
            # Send invalid JSON
            async with session.post(
                f"{self.base_url}/overlay/update",
                data="invalid json content",
                headers={"Content-Type": "application/json"},
            ) as response:
                self._log(f"Invalid JSON test response: {response.status}")
        except Exception as e:
            self._log(f"Invalid JSON test error: {e}")

    async def _test_connection_loss(self) -> None:
        """Test connection loss scenario."""
        # Try connecting to non-existent port
        old_port = self.server_port
        self.server_port = "9999"  # Non-existent port
        self.base_url = f"http://localhost:{self.server_port}"

        try:
            await self._test_connection()
        finally:
            # Restore original port
            self.server_port = old_port
            self.base_url = f"http://localhost:{self.server_port}"

    def _toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh of status."""
        if self.auto_refresh_var.get():
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()

    def _start_auto_refresh(self) -> None:
        """Start auto-refresh timer."""

        def refresh():
            if self.auto_refresh_var.get():
                asyncio.run_coroutine_threadsafe(self._get_status(), self.loop)
                self.root.after(2000, refresh)  # Refresh every 2 seconds

        refresh()

    def _stop_auto_refresh(self) -> None:
        """Stop auto-refresh timer."""
        # Auto-refresh is controlled by the checkbox, so no action needed
        pass

    def _clear_logs(self) -> None:
        """Clear log display."""
        self.log_display.delete("1.0", tk.END)
        self._log("Logs cleared")

    def _export_logs(self) -> None:
        """Export logs to file."""
        try:
            logs = self.log_display.get("1.0", tk.END)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"overlay_debug_logs_{timestamp}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(logs)

            self._log(f"Logs exported to: {filename}")
            messagebox.showinfo("Export Success", f"Logs exported to:\n{filename}")
        except Exception as e:
            self._log(f"Export failed: {e}", "ERROR")
            messagebox.showerror("Export Error", f"Failed to export logs:\n{e}")

    def run(self) -> None:
        """Run the GUI application."""
        self._log("Overlay Debug Tools started")

        # Start auto-refresh if enabled
        if self.auto_refresh_var.get():
            self._start_auto_refresh()

        try:
            self.root.mainloop()
        finally:
            # Cleanup
            self._log("Shutting down debug tools...")

            # Close HTTP session properly
            if self.session and not self.session.closed:
                # Create a new event loop for cleanup if current one is not running
                try:
                    if self.loop and not self.loop.is_closed():
                        future = asyncio.run_coroutine_threadsafe(
                            self.session.close(), self.loop
                        )
                        future.result(timeout=5)  # Wait max 5 seconds for cleanup
                except Exception as e:
                    self._log(f"Error during session cleanup: {e}", "WARNING")

            # Stop async loop
            if self.loop and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.loop.stop)

            self._log("Debug tools shutdown complete")

    async def _fix_input_blocking(self) -> None:
        """Fix overlay input blocking by applying proper click-through settings."""
        try:
            # Import and use the overlay input fix
            from overlay_input_fix import fix_overlay_input_blocking

            self._log("Applying overlay input blocking fix...")
            result = await fix_overlay_input_blocking()

            if result.get("success"):
                self._log("✅ Overlay input fix completed successfully")
                self._log(f"Fix result: {result.get('force_fix_result', 'N/A')}")

                # Log diagnostics
                diagnostics = result.get("diagnostics", {})
                self._log(f"Window found: {diagnostics.get('overlay_found', False)}")
                self._log(f"Window handle: {diagnostics.get('window_handle', 'N/A')}")

                window_props = diagnostics.get("window_properties", {})
                if window_props:
                    self._log(
                        f"Transparent: {window_props.get('has_transparent', False)}"
                    )
                    self._log(f"Layered: {window_props.get('has_layered', False)}")
                    self._log(
                        f"No-activate: {window_props.get('has_noactivate', False)}"
                    )

            else:
                error_msg = result.get("error", "Unknown error")
                self._log(f"❌ Overlay input fix failed: {error_msg}", "ERROR")

        except ImportError:
            self._log("❌ overlay_input_fix module not found", "ERROR")
        except Exception as e:
            self._log(f"❌ Error applying input fix: {e}", "ERROR")

    async def _test_click_through(self) -> None:
        """Test overlay click-through behavior."""
        try:
            from overlay_input_fix import OverlayInputManager

            self._log("Testing overlay click-through behavior...")

            manager = OverlayInputManager()
            if await manager.initialize():
                # Run diagnostics
                diagnostics = await manager.test_overlay_behavior()

                self._log("=== CLICK-THROUGH TEST RESULTS ===")
                self._log(f"Overlay found: {diagnostics.get('overlay_found', False)}")
                self._log(f"Window handle: {diagnostics.get('window_handle', 'N/A')}")
                self._log(
                    f"Interactive mode: {diagnostics.get('interactive_mode', False)}"
                )
                self._log(f"API status: {diagnostics.get('overlay_api_status', 'N/A')}")

                window_props = diagnostics.get("window_properties", {})
                if window_props:
                    self._log("--- Window Properties ---")
                    self._log(
                        f"Has WS_EX_TRANSPARENT: {window_props.get('has_transparent', False)}"
                    )
                    self._log(
                        f"Has WS_EX_LAYERED: {window_props.get('has_layered', False)}"
                    )
                    self._log(
                        f"Has WS_EX_NOACTIVATE: {window_props.get('has_noactivate', False)}"
                    )
                    self._log(
                        f"Has WS_EX_TOOLWINDOW: {window_props.get('has_toolwindow', False)}"
                    )
                    self._log(f"Raw style: {window_props.get('raw_style', 'N/A')}")

                # Test force click-through
                fix_result = await manager.force_click_through()
                self._log(f"Force click-through result: {fix_result}")

                await manager.cleanup()
            else:
                self._log("❌ Failed to initialize overlay manager for testing", "ERROR")

        except ImportError:
            self._log("❌ overlay_input_fix module not found", "ERROR")
        except Exception as e:
            self._log(f"❌ Error testing click-through: {e}", "ERROR")

    def fix_transparency(self):
        """Fix overlay window transparency if it's invisible due to alpha=0."""
        try:
            result = fix_overlay_transparency()
            self._log(result)
        except Exception as e:
            self._log(f"❌ Błąd naprawy przezroczystości: {e}", "ERROR")

    async def _fix_overlay_visibility(self) -> None:
        """Fix overlay visibility issues while maintaining click-through."""
        try:
            from overlay_visibility_fix import fix_overlay_visibility

            self._log("Applying overlay visibility fix...")
            result = await fix_overlay_visibility()

            if result.get("success"):
                self._log("✅ Overlay visibility fix completed successfully")
                self._log(
                    f"Visibility result: {result.get('visibility_fix_result', 'N/A')}"
                )
                self._log(
                    f"Force show result: {result.get('force_show_result', 'N/A')}"
                )

                # Log diagnostics
                diagnostics = result.get("diagnostics", {})
                self._log(f"Window found: {diagnostics.get('overlay_found', False)}")
                self._log(
                    f"Window visible: {diagnostics.get('visibility_tests', {}).get('is_visible', False)}"
                )
                self._log(f"Current alpha: {diagnostics.get('current_alpha', 'N/A')}")

                # Log window rectangle
                rect = diagnostics.get("visibility_tests", {}).get("window_rect")
                if rect:
                    self._log(
                        f"Window size: {rect.get('width', 0)}x{rect.get('height', 0)}"
                    )

                # Log API status
                api_status = diagnostics.get("api_status", "unknown")
                self._log(f"Overlay API status: {api_status}")

                if api_status == 200:
                    api_data = diagnostics.get("api_data", {})
                    self._log(f"Overlay status: {api_data.get('status', 'N/A')}")
                    self._log(
                        f"Overlay visible flag: {api_data.get('overlay_visible', False)}"
                    )

            else:
                error_msg = result.get("error", "Unknown error")
                self._log(f"❌ Overlay visibility fix failed: {error_msg}", "ERROR")

        except ImportError:
            self._log("❌ overlay_visibility_fix module not found", "ERROR")
        except Exception as e:
            self._log(f"❌ Error applying visibility fix: {e}", "ERROR")

    async def _adjust_opacity(self) -> None:
        """Adjust overlay opacity."""
        try:
            from overlay_visibility_fix import adjust_overlay_opacity

            opacity_str = self.opacity_var.get().strip()
            if not opacity_str:
                self._log("❌ Please enter opacity value (1-100)", "ERROR")
                return

            try:
                opacity = int(opacity_str)
                if opacity < 1 or opacity > 100:
                    self._log("❌ Opacity must be between 1-100", "ERROR")
                    return
            except ValueError:
                self._log("❌ Opacity must be a number", "ERROR")
                return

            self._log(f"Setting overlay opacity to {opacity}%...")
            result = await adjust_overlay_opacity(opacity)

            if result.get("success"):
                self._log(f"✅ {result.get('result', 'Opacity adjusted')}")

                # Log diagnostics
                diagnostics = result.get("diagnostics", {})
                alpha = diagnostics.get("current_alpha", "N/A")
                visible = diagnostics.get("visibility_tests", {}).get(
                    "is_visible", False
                )
                self._log(f"Current alpha: {alpha}, Visible: {visible}")

            else:
                error_msg = result.get("error", "Unknown error")
                self._log(f"❌ Failed to adjust opacity: {error_msg}", "ERROR")

        except ImportError:
            self._log("❌ overlay_visibility_fix module not found", "ERROR")
        except Exception as e:
            self._log(f"❌ Error adjusting opacity: {e}", "ERROR")

    async def _fix_taskbar_interference(self) -> None:
        """Fix Windows taskbar interference by overlay."""
        try:
            from overlay_taskbar_fix import rebuild_overlay_for_taskbar

            self._log("Fixing Windows taskbar interference...")
            result = await rebuild_overlay_for_taskbar()

            if result.get("success"):
                self._log("✅ Taskbar interference fix completed successfully")
                self._log(f"Rebuild result: {result.get('rebuild_result', 'N/A')}")

                # Log post-test results
                post_test = result.get("post_test", {})
                taskbar_status = post_test.get("taskbar_status", "unknown")
                self._log(f"Taskbar status: {taskbar_status}")

                overlay_windows = post_test.get("overlay_windows", [])
                taskbar_friendly_count = sum(
                    1 for w in overlay_windows if w.get("taskbar_friendly", False)
                )
                self._log(
                    f"Taskbar-friendly windows: {taskbar_friendly_count}/{len(overlay_windows)}"
                )

                recommendations = post_test.get("recommendations", [])
                if recommendations:
                    for rec in recommendations:
                        self._log(f"⚠️ {rec}")
                else:
                    self._log("✅ No taskbar compatibility issues found")

            else:
                error_msg = result.get("error", "Unknown error")
                self._log(f"❌ Taskbar fix failed: {error_msg}", "ERROR")

        except ImportError:
            self._log("❌ overlay_taskbar_fix module not found", "ERROR")
        except Exception as e:
            self._log(f"❌ Error fixing taskbar interference: {e}", "ERROR")

    async def _test_taskbar_compatibility(self) -> None:
        """Test overlay compatibility with Windows taskbar."""
        try:
            from overlay_taskbar_fix import OverlayTaskbarFix

            self._log("Testing overlay compatibility with Windows taskbar...")

            manager = OverlayTaskbarFix()
            if await manager.initialize():
                test_results = await manager.test_overlay_configuration()

                self._log("=== TASKBAR COMPATIBILITY TEST ===")

                # Taskbar status
                taskbar_status = test_results.get("taskbar_status", "unknown")
                if "OK" in taskbar_status:
                    self._log(f"✅ Taskbar status: {taskbar_status}")
                else:
                    self._log(f"⚠️ Taskbar status: {taskbar_status}")

                # Overlay windows analysis
                overlay_windows = test_results.get("overlay_windows", [])
                self._log(f"Found {len(overlay_windows)} overlay windows:")

                for i, window in enumerate(overlay_windows):
                    handle = window.get("handle", "N/A")
                    visible = window.get("visible", False)
                    taskbar_friendly = window.get("taskbar_friendly", False)

                    self._log(f"  Window {i+1} (Handle: {handle}):")
                    self._log(f"    Visible: {visible}")
                    self._log(f"    Taskbar-friendly: {taskbar_friendly}")

                    # Position info
                    position = window.get("position", {})
                    if position:
                        width = position.get("width", 0)
                        height = position.get("height", 0)
                        bottom = position.get("bottom", 0)
                        self._log(f"    Size: {width}x{height}, Bottom: {bottom}")

                    # Style info
                    styles = window.get("styles", {})
                    self._log(
                        f"    Has toolwindow: {styles.get('has_toolwindow', False)}"
                    )
                    self._log(
                        f"    Has transparent: {styles.get('has_transparent', False)}"
                    )
                    self._log(f"    Has layered: {styles.get('has_layered', False)}")
                    self._log(f"    Is popup: {styles.get('is_popup', False)}")

                # Recommendations
                recommendations = test_results.get("recommendations", [])
                if recommendations:
                    self._log("--- Recommendations ---")
                    for rec in recommendations:
                        self._log(f"⚠️ {rec}")
                else:
                    self._log("✅ No issues found with taskbar compatibility")

                await manager.cleanup()
            else:
                self._log("❌ Failed to initialize taskbar test manager", "ERROR")

        except ImportError:
            self._log("❌ overlay_taskbar_fix module not found", "ERROR")
        except Exception as e:
            self._log(f"❌ Error testing taskbar compatibility: {e}", "ERROR")

    async def _rebuild_overlay_complete(self) -> None:
        """Completely rebuild overlay from scratch."""
        try:
            self._log("Starting complete overlay rebuild...")

            # First apply taskbar fix
            await self._fix_taskbar_interference()

            # Wait a moment
            await asyncio.sleep(1)

            # Then apply visibility fix
            await self._fix_overlay_visibility()

            # Wait a moment
            await asyncio.sleep(1)

            # Finally apply input fix
            await self._fix_input_blocking()

            self._log("✅ Complete overlay rebuild finished!")
            self._log(
                "Overlay should now be visible, click-through, and taskbar-friendly"
            )

        except Exception as e:
            self._log(f"❌ Error during complete rebuild: {e}", "ERROR")


if __name__ == "__main__":
    app = OverlayDebugToolsGUI()
    app.root.mainloop()

"""
Simple overlay module for GAJA Assistant Client
Provides basic UI overlay for displaying AI responses and status.
"""

import asyncio
import json
import os
import sys
from typing import Optional, Dict, Any, Callable
from loguru import logger

# Try to import tkinter for simple GUI
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    logger.warning("tkinter not available - overlay disabled")


class SimpleOverlay:
    """Simple overlay using tkinter."""
    
    def __init__(self, config: dict):
        self.config = config
        self.position = config.get('position', 'top-right')
        self.enabled = config.get('enabled', True)
        self.auto_hide_delay = config.get('auto_hide_delay', 5)  # seconds
        
        self.window = None
        self.text_widget = None
        self.status_label = None
        self.running = False
        self.hide_timer = None
        
        if not TKINTER_AVAILABLE:
            self.enabled = False
            logger.warning("Overlay disabled - tkinter not available")
    
    def create_window(self):
        """Create overlay window."""
        if not self.enabled or not TKINTER_AVAILABLE:
            return
        
        try:
            # Create main window
            self.window = tk.Tk()
            self.window.title("GAJA Assistant")
            self.window.configure(bg='#2c3e50')
            
            # Window properties
            self.window.attributes('-topmost', True)  # Always on top
            self.window.overrideredirect(True)  # Remove window decorations
            self.window.geometry("400x300")
            
            # Position window
            self._position_window()
            
            # Create widgets
            self._create_widgets()
            
            # Bind events
            self.window.bind('<Button-1>', self._on_click)
            self.window.bind('<B1-Motion>', self._on_drag)
            
            logger.info("Overlay window created")
            
        except Exception as e:
            logger.error(f"Failed to create overlay window: {e}")
            self.enabled = False
    
    def _position_window(self):
        """Position window based on config."""
        if not self.window:
            return
        
        # Ensure this runs in the Tkinter thread
        def _task():
            # Get screen dimensions
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            
            # Window dimensions
            window_width = 400
            window_height = 300
            
            # Calculate position
            if self.position == 'top-right':
                x = screen_width - window_width - 20
                y = 20
            elif self.position == 'top-left':
                x = 20
                y = 20
            elif self.position == 'bottom-right':
                x = screen_width - window_width - 20
                y = screen_height - window_height - 20
            elif self.position == 'bottom-left':
                x = 20
                y = screen_height - window_height - 20
            else:  # center
                x = (screen_width - window_width) // 2
                y = (screen_height - window_height) // 2
            
            self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        if self.window.winfo_exists(): # Check if window exists before scheduling
             self.window.after(0, _task)


    def _create_widgets(self):
        """Create UI widgets."""
        # Ensure this runs in the Tkinter thread
        # This is typically called during initialization, so it should be fine if called
        # before the mainloop starts in its own thread.
        # However, to be safe, or if it could be called later:
        # if self.window:
        #     self.window.after(0, self._do_create_widgets)
        # else:
        #     self._do_create_widgets()
        # For now, assuming it's called safely during init in the main Tk thread context.

        # Main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="GAJA Assistant - Ready",
            font=('Arial', 10, 'bold'),
            background='#34495e',
            foreground='#ecf0f1'
        )
        self.status_label.pack(fill=tk.X, pady=(0, 5))
        
        # Text display area
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text widget with scrollbar
        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=('Arial', 9),
            bg='#34495e',
            fg='#ecf0f1',
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Hide button
        hide_btn = ttk.Button(
            button_frame,
            text="Hide",
            command=self.hide
        )
        hide_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Clear button
        clear_btn = ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_text
        )
        clear_btn.pack(side=tk.RIGHT)
    
    def _on_click(self, event):
        """Handle mouse click for dragging."""
        self.last_x = event.x
        self.last_y = event.y
    
    def _on_drag(self, event):
        """Handle window dragging."""
        x = self.window.winfo_x() + (event.x - self.last_x)
        y = self.window.winfo_y() + (event.y - self.last_y)
        self.window.geometry(f"+{x}+{y}")
    
    def show(self):
        """Show overlay."""
        if not self.enabled or not self.window:
            return
        
        def _task():
            try:
                self.window.deiconify()
                self.window.lift()
                self.window.attributes('-topmost', True)
                
                # Cancel hide timer if running
                if self.hide_timer:
                    self.window.after_cancel(self.hide_timer)
                    self.hide_timer = None
                
                logger.debug("Overlay shown")
                
            except Exception as e:
                logger.error(f"Error showing overlay: {e}")

        if self.window.winfo_exists():
            self.window.after(0, _task)

    def hide(self):
        """Hide overlay."""
        if not self.enabled or not self.window:
            return

        def _task():
            try:
                self.window.withdraw()
                logger.debug("Overlay hidden")
                
            except Exception as e:
                logger.error(f"Error hiding overlay: {e}")
        
        if self.window.winfo_exists():
            self.window.after(0, _task)

    def update_status(self, status: str):
        """Update status text."""
        if not self.enabled or not self.status_label:
            return
        
        def _task():
            try:
                self.status_label.config(text=f"GAJA Assistant - {status}")
                logger.debug(f"Status updated: {status}")
                
            except Exception as e:
                logger.error(f"Error updating status: {e}")

        if self.window and self.window.winfo_exists() and self.status_label.winfo_exists():
             self.window.after(0, _task)

    def add_message(self, message: str, message_type: str = "info"):
        """Add message to display."""
        if not self.enabled or not self.text_widget:
            return

        def _task():
            try:
                # Timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Format message
                if message_type == "user":
                    formatted_msg = f"[{timestamp}] You: {message}\\n"
                    # color = "#3498db" # Direct color application per line is complex in Text widget
                elif message_type == "ai":
                    formatted_msg = f"[{timestamp}] AI: {message}\\n"
                    # color = "#2ecc71"
                elif message_type == "system":
                    formatted_msg = f"[{timestamp}] System: {message}\\n"
                    # color = "#f39c12"
                elif message_type == "error":
                    formatted_msg = f"[{timestamp}] Error: {message}\\n"
                    # color = "#e74c3c"
                else:
                    formatted_msg = f"[{timestamp}] {message}\\n"
                    # color = "#ecf0f1"
                
                # Add message to text widget
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.insert(tk.END, formatted_msg)
                # Consider adding tags for coloring here if needed
                self.text_widget.config(state=tk.DISABLED)
                
                # Auto-scroll to bottom
                self.text_widget.see(tk.END)
                
                # Show overlay and set auto-hide timer (show itself uses .after)
                self.show() # This will schedule the show task
                self._set_auto_hide() # This will schedule the hide task
                
                logger.debug(f"Message added: {message_type}")
                
            except Exception as e:
                logger.error(f"Error adding message: {e}")

        if self.window and self.window.winfo_exists() and self.text_widget.winfo_exists():
            self.window.after(0, _task)

    def clear_text(self):
        """Clear text display."""
        if not self.enabled or not self.text_widget:
            return

        def _task():
            try:
                self.text_widget.config(state=tk.NORMAL)
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.config(state=tk.DISABLED)
                
                logger.debug("Text cleared")
                
            except Exception as e:
                logger.error(f"Error clearing text: {e}")
        
        if self.window and self.window.winfo_exists() and self.text_widget.winfo_exists():
            self.window.after(0, _task)

    def _set_auto_hide(self):
        """Set auto-hide timer."""
        if not self.auto_hide_delay or not self.window:
            return
        
        def _task():
            # Cancel existing timer
            if self.hide_timer:
                try: # Add try-except for after_cancel
                    self.window.after_cancel(self.hide_timer)
                except Exception as e:
                    logger.warning(f"Could not cancel hide_timer: {e}")
                self.hide_timer = None
            
            # Set new timer
            self.hide_timer = self.window.after(
                self.auto_hide_delay * 1000,
                self.hide # hide() itself uses .after, so this is fine
            )
        if self.window.winfo_exists():
            self.window.after(0, _task)
    
    def start(self):
        """Start overlay (non-blocking)."""
        if not self.enabled:
            logger.info("Overlay disabled")
            return
        
        self.running = True
        self.create_window()
        
        if self.window:
            # Run in separate thread to avoid blocking
            import threading
            
            def run_mainloop():
                try:
                    # Ensure Tk() is created in this thread if not already
                    if not self.window:
                         logger.error("Window not created before starting mainloop thread.")
                         # Attempt to create it here, though ideally it's done before starting thread
                         # self.create_window() # This might be problematic if create_window expects main thread
                         return

                    self.window.mainloop()
                except RuntimeError as e: # Catch specific Tcl errors
                    if "main thread is not in main loop" in str(e):
                        logger.warning(f"Tkinter mainloop issue: {e}. Overlay may not function correctly.")
                    else:
                        logger.error(f"Overlay mainloop error: {e}")
                except Exception as e:
                    logger.error(f"Overlay mainloop error: {e}")
                finally:
                    self.running = False
            
            thread = threading.Thread(target=run_mainloop, daemon=True)
            thread.start()
            
            logger.info("Overlay started")
    
    def stop(self):
        """Stop overlay."""
        self.running = False
        
        def _task():
            if self.window:
                try:
                    if self.hide_timer: # Cancel timer before destroying window
                        try:
                            self.window.after_cancel(self.hide_timer)
                        except: # Ignore errors if timer or window is already gone
                            pass
                        self.hide_timer = None
                    self.window.quit() # Stops mainloop
                    self.window.destroy() # Destroys window
                    self.window = None # Clear reference
                except Exception as e:
                    logger.error(f"Error stopping overlay window: {e}")
        
        if self.window and TKINTER_AVAILABLE : # Check if window ever existed
             # Schedule the task. If window is already destroyed, after() might fail.
            try:
                if self.window.winfo_exists():
                    self.window.after(0, _task)
                else: # If window doesn't exist, just log
                    logger.info("Overlay window already destroyed or not created.")
            except tk.TclError: # Window might be in process of being destroyed
                logger.info("Overlay window likely already destroyed (TclError).")
            except Exception as e: # Catch any other unexpected errors
                logger.error(f"Error scheduling overlay stop: {e}")
        
        logger.info("Overlay stop sequence initiated")


class ConsoleOverlay:
    """Simple console-based overlay for systems without GUI."""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('enabled', True)
        
    def show(self):
        """Show overlay (no-op for console)."""
        pass
    
    def hide(self):
        """Hide overlay (no-op for console)."""
        pass
    
    def update_status(self, status: str):
        """Update status."""
        if self.enabled:
            print(f"\r[GAJA] Status: {status}", end="", flush=True)
    
    def add_message(self, message: str, message_type: str = "info"):
        """Add message to console."""
        if not self.enabled:
            return
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        prefix = {
            "user": "YOU",
            "ai": "AI",
            "system": "SYS",
            "error": "ERR"
        }.get(message_type, "INFO")
        
        print(f"\n[{timestamp}] {prefix}: {message}")
    
    def clear_text(self):
        """Clear console (limited)."""
        if self.enabled:
            os.system('cls' if os.name == 'nt' else 'clear')
    
    def start(self):
        """Start console overlay."""
        if self.enabled:
            print("GAJA Assistant Console Overlay Started")
    
    def stop(self):
        """Stop console overlay."""
        if self.enabled:
            print("\nGAJA Assistant Console Overlay Stopped")


# Factory function
def create_overlay(config: dict) -> Any:
    """Create appropriate overlay based on available components."""
    if TKINTER_AVAILABLE and config.get('enabled', True):
        return SimpleOverlay(config)
    else:
        return ConsoleOverlay(config)

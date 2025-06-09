#!/usr/bin/env python3
"""
GAJA Assistant Setup Wizard
Simple GUI setup wizard for configuring the GAJA Assistant.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
import logging
import threading
import subprocess
import sounddevice as sd
import requests
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GAJA Assistant - Setup Wizard")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Configuration storage
        self.config = {
            "user_name": "",
            "openai_api_key": "",
            "wakeword": {
                "enabled": True,
                "sensitivity": 0.6,
                "keyword": "gaja",
                "device_id": None
            },
            "whisper": {
                "model": "base",
                "language": "pl",
                "device_id": None
            },
            "audio": {
                "input_device": None,
                "output_device": None,
                "sample_rate": 16000
            },
            "server": {
                "host": "localhost",
                "port": 8001
            }
        }
        
        self.current_step = 0
        self.steps = [
            ("Welcome", self.create_welcome_step),
            ("User Info", self.create_user_info_step), 
            ("API Keys", self.create_api_keys_step),
            ("Audio Devices", self.create_audio_step),
            ("Wakeword Setup", self.create_wakeword_step),
            ("Server Setup", self.create_server_step),
            ("Complete", self.create_complete_step)
        ]
        
        self.setup_ui()
        self.show_current_step()
        
    def setup_ui(self):
        """Setup the main UI layout."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="GAJA Assistant Setup", 
                               font=("Arial", 20, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Progress bar
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, 
                                          variable=self.progress_var, 
                                          maximum=len(self.steps))
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.progress_frame.columnconfigure(0, weight=1)
        
        # Step label
        self.step_label = ttk.Label(main_frame, text="", font=("Arial", 14))
        self.step_label.grid(row=2, column=0, pady=(0, 20))
        
        # Content frame
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(3, weight=1)
        self.content_frame.columnconfigure(0, weight=1)
        
        # Navigation buttons
        nav_frame = ttk.Frame(main_frame)
        nav_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(20, 0))
        
        self.back_button = ttk.Button(nav_frame, text="Back", command=self.previous_step)
        self.back_button.grid(row=0, column=0)
        
        self.next_button = ttk.Button(nav_frame, text="Next", command=self.next_step)
        self.next_button.grid(row=0, column=2)
        
        # Add some space in the middle
        nav_frame.columnconfigure(1, weight=1)
        
    def show_current_step(self):
        """Display the current step."""
        # Update progress
        self.progress_var.set(self.current_step + 1)
        
        # Update step label
        step_name, step_func = self.steps[self.current_step]
        self.step_label.config(text=f"Step {self.current_step + 1}: {step_name}")
        
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Create step content
        step_func()
        
        # Update navigation buttons
        self.back_button.config(state="normal" if self.current_step > 0 else "disabled")
        self.next_button.config(text="Finish" if self.current_step == len(self.steps) - 1 else "Next")
        
    def next_step(self):
        """Go to next step."""
        if self.current_step < len(self.steps) - 1:
            if self.validate_current_step():
                self.current_step += 1
                self.show_current_step()
        else:
            # Finish setup
            self.finish_setup()
            
    def previous_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_current_step()
            
    def validate_current_step(self):
        """Validate current step data."""
        return True  # Basic validation for now
        
    def create_welcome_step(self):
        """Create welcome step."""
        welcome_text = """
Welcome to GAJA Assistant Setup!

This wizard will help you configure your voice assistant:

• Set up your personal information
• Configure OpenAI API access
• Select audio devices for microphone and speakers
• Set up wakeword detection
• Configure server connection

Click Next to begin setup.
        """
        
        label = ttk.Label(self.content_frame, text=welcome_text, 
                         font=("Arial", 12), justify=tk.LEFT)
        label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=50, pady=50)
        
    def create_user_info_step(self):
        """Create user info step."""
        ttk.Label(self.content_frame, text="Enter your name:", 
                 font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.name_var = tk.StringVar(value=self.config.get("user_name", ""))
        name_entry = ttk.Entry(self.content_frame, textvariable=self.name_var, 
                              font=("Arial", 12), width=40)
        name_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(self.content_frame, text="This name will be used to personalize your experience.", 
                 font=("Arial", 10), foreground="gray").grid(row=2, column=0, sticky=tk.W)
        
        # Update config when text changes
        def update_name(*args):
            self.config["user_name"] = self.name_var.get()
        self.name_var.trace('w', update_name)
        
    def create_api_keys_step(self):
        """Create API keys step."""
        ttk.Label(self.content_frame, text="OpenAI API Key:", 
                 font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.api_key_var = tk.StringVar(value=self.config.get("openai_api_key", ""))
        api_entry = ttk.Entry(self.content_frame, textvariable=self.api_key_var, 
                             show="*", font=("Arial", 12), width=60)
        api_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(self.content_frame, text="Test API Key", 
                  command=self.test_api_key).grid(row=2, column=0, sticky=tk.W, pady=(0, 20))
        
        help_text = """
You need an OpenAI API key to use the AI features.
Get one at: https://platform.openai.com/api-keys

The key should start with 'sk-' and be about 50 characters long.
        """
        ttk.Label(self.content_frame, text=help_text, 
                 font=("Arial", 10), foreground="gray").grid(row=3, column=0, sticky=tk.W)
        
        def update_api_key(*args):
            self.config["openai_api_key"] = self.api_key_var.get()
        self.api_key_var.trace('w', update_api_key)
        
    def test_api_key(self):
        """Test the OpenAI API key."""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Warning", "Please enter an API key first.")
            return
            
        try:
            # Simple test request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Test with a simple models list request
            response = requests.get("https://api.openai.com/v1/models", 
                                  headers=headers, timeout=10)
            
            if response.status_code == 200:
                messagebox.showinfo("Success", "API key is valid!")
            else:
                messagebox.showerror("Error", f"API key test failed: {response.status_code}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to test API key: {str(e)}")
            
    def create_audio_step(self):
        """Create audio devices step."""
        # Get available audio devices
        try:
            devices = sd.query_devices()
            input_devices = [(i, d['name']) for i, d in enumerate(devices) 
                           if d['max_input_channels'] > 0]
            output_devices = [(i, d['name']) for i, d in enumerate(devices) 
                            if d['max_output_channels'] > 0]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get audio devices: {e}")
            input_devices = output_devices = []
            
        # Input device selection
        ttk.Label(self.content_frame, text="Select Microphone:", 
                 font=("Arial", 12)).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.input_device_var = tk.StringVar()
        input_combo = ttk.Combobox(self.content_frame, textvariable=self.input_device_var,
                                  values=[f"{i}: {name}" for i, name in input_devices],
                                  state="readonly", width=60)
        input_combo.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Output device selection
        ttk.Label(self.content_frame, text="Select Speakers:", 
                 font=("Arial", 12)).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        self.output_device_var = tk.StringVar()
        output_combo = ttk.Combobox(self.content_frame, textvariable=self.output_device_var,
                                   values=[f"{i}: {name}" for i, name in output_devices],
                                   state="readonly", width=60)
        output_combo.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Test buttons
        test_frame = ttk.Frame(self.content_frame)
        test_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Button(test_frame, text="Test Microphone", 
                  command=self.test_microphone).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(test_frame, text="Test Speakers", 
                  command=self.test_speakers).grid(row=0, column=1)
        
        def update_input_device(*args):
            selection = self.input_device_var.get()
            if selection:
                device_id = int(selection.split(':')[0])
                self.config["audio"]["input_device"] = device_id
                self.config["wakeword"]["device_id"] = device_id
                self.config["whisper"]["device_id"] = device_id
                
        def update_output_device(*args):
            selection = self.output_device_var.get()
            if selection:
                device_id = int(selection.split(':')[0])
                self.config["audio"]["output_device"] = device_id
                
        self.input_device_var.trace('w', update_input_device)
        self.output_device_var.trace('w', update_output_device)
        
    def test_microphone(self):
        """Test microphone recording."""
        try:
            messagebox.showinfo("Microphone Test", 
                              "Recording for 3 seconds... Speak into your microphone!")
            
            device_id = self.config["audio"]["input_device"]
            duration = 3
            
            recording = sd.rec(int(duration * 16000), samplerate=16000, 
                             channels=1, device=device_id)
            sd.wait()
            
            # Play back the recording
            messagebox.showinfo("Microphone Test", "Playing back your recording...")
            sd.play(recording, samplerate=16000)
            sd.wait()
            
            messagebox.showinfo("Success", "Microphone test completed!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Microphone test failed: {e}")
            
    def test_speakers(self):
        """Test speaker output."""
        try:
            import numpy as np
            
            # Generate a simple test tone
            duration = 2  # seconds
            frequency = 440  # Hz (A note)
            sample_rate = 16000
            
            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            device_id = self.config["audio"]["output_device"]
            
            messagebox.showinfo("Speaker Test", "Playing test tone...")
            sd.play(tone, samplerate=sample_rate, device=device_id)
            sd.wait()
            
            messagebox.showinfo("Success", "Speaker test completed!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Speaker test failed: {e}")
        
    def create_wakeword_step(self):
        """Create wakeword setup step."""
        ttk.Label(self.content_frame, text="Wakeword Configuration", 
                 font=("Arial", 14, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 20))
        
        # Enable/disable wakeword
        self.wakeword_enabled_var = tk.BooleanVar(value=self.config["wakeword"]["enabled"])
        ttk.Checkbutton(self.content_frame, text="Enable wakeword detection", 
                       variable=self.wakeword_enabled_var).grid(row=1, column=0, sticky=tk.W, pady=(0, 20))
        
        # Keyword selection
        ttk.Label(self.content_frame, text="Wakeword:", 
                 font=("Arial", 12)).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        self.keyword_var = tk.StringVar(value=self.config["wakeword"]["keyword"])
        keyword_combo = ttk.Combobox(self.content_frame, textvariable=self.keyword_var,
                                    values=["gaja", "hey_jarvis", "alexa", "computer"],
                                    width=20)
        keyword_combo.grid(row=3, column=0, sticky=tk.W, pady=(0, 20))
        
        # Sensitivity
        ttk.Label(self.content_frame, text="Sensitivity (higher = more sensitive):", 
                 font=("Arial", 12)).grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        
        self.sensitivity_var = tk.DoubleVar(value=self.config["wakeword"]["sensitivity"])
        sensitivity_scale = ttk.Scale(self.content_frame, from_=0.1, to=1.0, 
                                     variable=self.sensitivity_var, orient=tk.HORIZONTAL, length=200)
        sensitivity_scale.grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        self.sensitivity_label = ttk.Label(self.content_frame, text="")
        self.sensitivity_label.grid(row=6, column=0, sticky=tk.W, pady=(0, 20))
        
        def update_sensitivity_label(*args):
            value = self.sensitivity_var.get()
            self.sensitivity_label.config(text=f"Current: {value:.1f}")
            
        self.sensitivity_var.trace('w', update_sensitivity_label)
        update_sensitivity_label()
        
        # Test button
        ttk.Button(self.content_frame, text="Test Wakeword Detection", 
                  command=self.test_wakeword).grid(row=7, column=0, sticky=tk.W)
        
        def update_wakeword_config(*args):
            self.config["wakeword"]["enabled"] = self.wakeword_enabled_var.get()
            self.config["wakeword"]["keyword"] = self.keyword_var.get()
            self.config["wakeword"]["sensitivity"] = self.sensitivity_var.get()
            
        self.wakeword_enabled_var.trace('w', update_wakeword_config)
        self.keyword_var.trace('w', update_wakeword_config)
        self.sensitivity_var.trace('w', update_wakeword_config)
        
    def test_wakeword(self):
        """Test wakeword detection."""
        messagebox.showinfo("Wakeword Test", 
                          f"Say '{self.keyword_var.get()}' to test detection.\n"
                          "This is a basic test - the real system uses more advanced detection.")
        
    def create_server_step(self):
        """Create server setup step."""
        ttk.Label(self.content_frame, text="Server Configuration", 
                 font=("Arial", 14, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 20))
        
        # Server host
        ttk.Label(self.content_frame, text="Server Host:", 
                 font=("Arial", 12)).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        self.host_var = tk.StringVar(value=self.config["server"]["host"])
        host_entry = ttk.Entry(self.content_frame, textvariable=self.host_var, width=30)
        host_entry.grid(row=2, column=0, sticky=tk.W, pady=(0, 20))
        
        # Server port
        ttk.Label(self.content_frame, text="Server Port:", 
                 font=("Arial", 12)).grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        
        self.port_var = tk.StringVar(value=str(self.config["server"]["port"]))
        port_entry = ttk.Entry(self.content_frame, textvariable=self.port_var, width=10)
        port_entry.grid(row=4, column=0, sticky=tk.W, pady=(0, 20))
        
        # Test connection button
        ttk.Button(self.content_frame, text="Test Server Connection", 
                  command=self.test_server_connection).grid(row=5, column=0, sticky=tk.W)
        
        def update_server_config(*args):
            self.config["server"]["host"] = self.host_var.get()
            try:
                self.config["server"]["port"] = int(self.port_var.get())
            except ValueError:
                pass
                
        self.host_var.trace('w', update_server_config)
        self.port_var.trace('w', update_server_config)
        
    def test_server_connection(self):
        """Test server connection."""
        host = self.host_var.get()
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return
            
        # Try to connect to server
        try:
            url = f"http://{host}:{port}/health"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Server connection successful!")
            else:
                messagebox.showwarning("Warning", f"Server responded with status {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to server: {e}")
            
    def create_complete_step(self):
        """Create completion step."""
        complete_text = f"""
Setup Complete!

Configuration Summary:
• User Name: {self.config.get('user_name', 'Not set')}
• API Key: {'Set' if self.config.get('openai_api_key') else 'Not set'}
• Wakeword: {self.config['wakeword']['keyword']} ({'Enabled' if self.config['wakeword']['enabled'] else 'Disabled'})
• Server: {self.config['server']['host']}:{self.config['server']['port']}

Your configuration will be saved and the assistant will be ready to use.

Click Finish to complete setup.
        """
        
        label = ttk.Label(self.content_frame, text=complete_text, 
                         font=("Arial", 12), justify=tk.LEFT)
        label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=50, pady=50)
        
    def finish_setup(self):
        """Finish setup and save configuration."""
        try:
            # Save client config
            client_config_path = Path("client/client_config.json")
            if client_config_path.exists():
                with open(client_config_path, 'r') as f:
                    client_config = json.load(f)
            else:
                client_config = {}
                
            # Update client config
            client_config.update({
                "wakeword": self.config["wakeword"],
                "whisper": self.config["whisper"],
                "audio": self.config["audio"],
                "server_url": f"ws://{self.config['server']['host']}:{self.config['server']['port']}/ws/client1"
            })
            
            # Save client config
            client_config_path.parent.mkdir(exist_ok=True)
            with open(client_config_path, 'w') as f:
                json.dump(client_config, f, indent=2)
                
            # Save server config
            server_config_path = Path("server/server_config.json")
            if server_config_path.exists():
                with open(server_config_path, 'r') as f:
                    server_config = json.load(f)
            else:
                server_config = {}
                
            # Update server config
            if self.config.get("openai_api_key"):
                server_config["openai_api_key"] = self.config["openai_api_key"]
                
            server_config["host"] = self.config["server"]["host"]
            server_config["port"] = self.config["server"]["port"]
            
            # Save server config
            server_config_path.parent.mkdir(exist_ok=True)
            with open(server_config_path, 'w') as f:
                json.dump(server_config, f, indent=2)
                
            # Mark setup as complete
            setup_complete_path = Path("setup_complete.flag")
            setup_complete_path.touch()
            
            messagebox.showinfo("Success", 
                              "Setup completed successfully!\n\n"
                              "You can now start the GAJA Assistant:\n"
                              "1. Start the server: python server/server_main.py\n"
                              "2. Start the client: python client/client_main.py")
            
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            
    def run(self):
        """Run the setup wizard."""
        self.root.mainloop()


def main():
    """Main entry point."""
    # Check if setup was already completed
    if Path("setup_complete.flag").exists():
        response = messagebox.askyesno("Setup Complete", 
                                     "Setup was already completed. Run setup again?")
        if not response:
            return
            
    # Run setup wizard
    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()

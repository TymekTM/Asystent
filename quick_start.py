#!/usr/bin/env python3
"""
GAJA Assistant Quick Start
Quick launcher that checks configuration and starts the assistant.
"""

import os
import sys
import json
import subprocess
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_setup():
    """Check if setup is complete."""
    setup_flag = Path("setup_complete.flag")
    return setup_flag.exists()

def run_setup():
    """Run the setup wizard."""
    logger.info("Running setup wizard...")
    try:
        subprocess.run([sys.executable, "setup_wizard.py"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Setup failed: {e}")
        return False
    except FileNotFoundError:
        logger.error("setup_wizard.py not found")
        return False

def check_config_files():
    """Check if required config files exist."""
    client_config = Path("client/client_config.json")
    server_config = Path("server/server_config.json")
    
    missing = []
    if not client_config.exists():
        missing.append("client/client_config.json")
    if not server_config.exists():
        missing.append("server/server_config.json")
    
    if missing:
        logger.warning(f"Missing config files: {', '.join(missing)}")
        return False
    
    return True

def create_default_configs():
    """Create default configuration files."""
    logger.info("Creating default configuration files...")
    
    # Default client config
    client_config = {
        "user_id": "1",
        "server_url": "ws://localhost:8001/ws/client1",
        "client_version": "1.0.0",
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
        "overlay": {
            "enabled": True,
            "position": "top-right",
            "size": {
                "width": 400,
                "height": 300
            },
            "transparency": 0.9
        },
        "audio": {
            "input_device": None,
            "output_device": None,
            "sample_rate": 16000
        },
        "logging": {
            "level": "INFO",
            "file": "logs/client.log"
        }
    }
    
    # Default server config
    server_config = {
        "host": "localhost",
        "port": 8001,
        "database_url": "sqlite:///server/gaja_assistant.db",
        "ai_model": "gpt-4.1-nano",
        "openai_api_key": "",
        "logging": {
            "level": "INFO",
            "file": "logs/server.log"
        },
        "plugins": {
            "enabled": True,
            "auto_load": True,
            "directories": ["modules"]
        }
    }
    
    # Create directories
    Path("client").mkdir(exist_ok=True)
    Path("server").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Save configs
    with open("client/client_config.json", 'w') as f:
        json.dump(client_config, f, indent=2)
    
    with open("server/server_config.json", 'w') as f:
        json.dump(server_config, f, indent=2)
    
    logger.info("Default configuration files created")

def start_server():
    """Start the server."""
    logger.info("Starting GAJA Assistant Server...")
    
    try:
        # Start server in background
        process = subprocess.Popen(
            [sys.executable, "server/server_main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give server time to start
        time.sleep(3)
        
        # Check if server is still running
        if process.poll() is None:
            logger.info("Server started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            logger.error(f"Server failed to start: {stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return None

def start_client():
    """Start the client."""
    logger.info("Starting GAJA Assistant Client...")
    
    try:
        # Start client
        process = subprocess.Popen(
            [sys.executable, "client/client_main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give client time to start
        time.sleep(2)
        
        # Check if client is still running
        if process.poll() is None:
            logger.info("Client started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            logger.error(f"Client failed to start: {stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        return None

def main():
    """Main entry point."""
    print("🤖 GAJA Assistant Quick Start")
    print("=" * 40)
    
    # Check if setup is complete
    if not check_setup():
        print("\n⚠️  Setup not completed. Running setup wizard...")
        if not run_setup():
            print("❌ Setup failed. Please check the errors above.")
            return
    
    # Check config files
    if not check_config_files():
        print("\n⚠️  Configuration files missing. Creating defaults...")
        create_default_configs()
        print("✅ Default configuration files created.")
        print("💡 You may want to edit the config files to add your OpenAI API key.")
    
    # Start server
    print("\n🚀 Starting server...")
    server_process = start_server()
    if not server_process:
        print("❌ Failed to start server")
        return
    
    # Start client
    print("🚀 Starting client...")
    client_process = start_client()
    if not client_process:
        print("❌ Failed to start client")
        if server_process:
            server_process.terminate()
        return
    
    print("\n✅ GAJA Assistant is running!")
    print("🎤 Say 'gaja' to activate the assistant")
    print("📋 Check the logs in the 'logs' directory for details")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        # Wait for processes to finish or user interruption
        while True:
            # Check if processes are still running
            if server_process.poll() is not None:
                print("⚠️  Server process stopped")
                break
            if client_process.poll() is not None:
                print("⚠️  Client process stopped")
                break
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping GAJA Assistant...")
        
        # Stop processes
        if client_process and client_process.poll() is None:
            client_process.terminate()
            print("✅ Client stopped")
            
        if server_process and server_process.poll() is None:
            server_process.terminate()
            print("✅ Server stopped")
    
    print("👋 Goodbye!")

if __name__ == "__main__":
    main()

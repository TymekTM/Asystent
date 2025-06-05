# gaja.spec — wersja 2.1.0 - Normalny EXE z automatycznym doinstalowywaniem brakujących pakietów

block_cipher = None
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Helper to collect all files under a directory into datas with relative dest
def collect_dir(src_dir, dest_prefix):
    collected = []
    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for fname in files:
                src = os.path.join(root, fname)
                rel_root = os.path.relpath(root, src_dir)
                dest = os.path.join(dest_prefix, rel_root)
                collected.append((src, dest))
    return collected

# Simplified: No sounddevice bundling - dependency manager handles it
def collect_sounddevice_files():
    """Skip sounddevice bundling - let dependency manager handle it at runtime"""
    binaries = []
    datas = []
    
    # Simple approach: Don't bundle sounddevice - let dependency manager handle it
    # This avoids complex native DLL bundling issues
    print("ℹ️  sounddevice will be auto-downloaded by dependency manager when needed")
    return binaries, datas

datas = []
# Include essential files only (core application)
datas += collect_dir('audio_modules', 'audio_modules')
datas += collect_dir('web_ui', 'web_ui')
datas += collect_dir('web_ui/templates', 'templates')
datas += collect_dir('web_ui/static', 'static')
datas += collect_dir('modules', 'modules')

# Include essential config files
datas += [
    ('config.py', '.'),
    ('database_manager.py', '.'),
    ('database_models.py', '.'),
    ('dependency_manager.py', '.'),  # Menedżer zależności
    ('gaja.ico', '.'),  # Ikona aplikacji
    ('requirements.txt', '.'),  # Lista pakietów (dla informacji)
]

# Include only essential resources
if os.path.exists('resources/sounds'):
    datas += collect_dir('resources/sounds', 'resources/sounds')

# Include overlay executable if it exists
overlay_dest_dir = 'overlay'  # Define destination directory for overlay files
overlay_exe = 'overlay/target/release/Gaja Overlay.exe'
if os.path.exists(overlay_exe):
    datas.append((overlay_exe, overlay_dest_dir))
    # Also include the webview2 loader if it exists
    webview_loader_path = os.path.join(os.path.dirname(overlay_exe), 'WebView2Loader.dll')
    if os.path.exists(webview_loader_path):
        datas.append((webview_loader_path, overlay_dest_dir))
        print(f"Overlay będzie bundled: {overlay_exe} oraz WebView2Loader.dll")
    else:
        print(f"Overlay będzie bundled: {overlay_exe}")
        print(f"OSTRZEŻENIE: Nie znaleziono WebView2Loader.dll obok Gaja Overlay.exe. Upewnij się, że jest on zbędny lub dodaj go ręcznie.")

else:
    print(f"BŁĄD: Nie znaleziono pliku Gaja Overlay.exe w oczekiwanej lokalizacji: {overlay_exe}")
    print("Upewnij się, że overlay został zbudowany przed uruchomieniem PyInstallera.")
    # Możesz zdecydować, czy chcesz przerwać build, jeśli overlay jest krytyczny
    # sys.exit(1)

# Note: sounddevice will be handled by dependency manager - no bundling needed

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],  # No pre-bundled binaries
    datas=datas,
    hiddenimports=[
        # Essential for dependency manager and app startup
        'dependency_manager',
        'subprocess',
        'json',
        'pathlib',
        'logging',
        'shutil',
        'requests',         # Needed for downloading packages
        'colorama',         # For colored console output        # Web UI dependencies (bundled for core functionality)
        'flask',            # Web framework
        'jinja2',           # Template engine
        'werkzeug',         # Flask dependency
        'markupsafe',       # Jinja2 dependency
        'markdown',         # For documentation rendering
        'webbrowser',       # For opening browser
        
        # Web UI app
        'web_ui.app',# Core modules
        'config',
        'database_manager',
        'database_models',
        'assistant',
        'ai_module',
        'performance_monitor',
        'prompt_builder',
        'prompts',
          # Web UI core modules
        'web_ui.core.auth',
        'web_ui.core.config',
        'web_ui.core.i18n',
          # Web UI utils
        'web_ui.utils.audio_utils',
        'web_ui.utils.history_manager',
        'web_ui.utils.test_runner',
        'web_ui.utils.benchmark_manager',
        
        # Web UI routes
        'web_ui.routes.web_routes',
        'web_ui.routes.api_routes',
        'web_ui.routes.api_additional',
        
        # Essential stdlib imports that might be needed
        'timeit',
        'wave',
        'fileinput',
    ],    hookspath=[],  # No custom hooks needed
    runtime_hooks=[],  # No runtime hooks needed
    excludes=[
        # Heavy ML/AI packages - will be auto-downloaded
        'torch',
        'torchvision', 
        'torchaudio',
        'scipy',        'sklearn',
        'scikit_learn',
        'huggingface_hub',
        'transformers', 
        'faster_whisper',
        'openwakeword',
        'whisper',
        'tqdm',
        
        # Audio packages - let dependency manager handle native libs
        'sounddevice',  # Added back to excludes - dependency manager handles it
        '_sounddevice',  # Native module
        
        # Image processing
        'PIL',
        'cv2',
        'matplotlib',
          # Data processing  
        'pandas',
        # 'numpy' removed from excludes - needed for core functionality
    ],win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Tworzenie pojedynczego pliku EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # Dołącz binaries do EXE
    a.zipfiles,  # Dołącz zipfiles do EXE
    a.datas,     # Dołącz datas do EXE
    [],
    name='Gaja',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='gaja.ico'
)

# Pojedynczy plik EXE - brak COLLECT

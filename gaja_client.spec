# gaja_client.spec - Client Build Configuration
# PyInstaller spec file for GAJA Assistant Client

block_cipher = None
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Helper to collect all files under a directory
def collect_dir(src_dir, dest_prefix):
    collected = []
    if os.path.exists(src_dir):
        for root, dirs, files in os.walk(src_dir):
            for fname in files:
                if fname.endswith(('.pyc', '.pyo', '__pycache__')):
                    continue
                src = os.path.join(root, fname)
                rel_root = os.path.relpath(root, src_dir)
                if rel_root == '.':
                    dest = dest_prefix
                else:
                    dest = os.path.join(dest_prefix, rel_root)
                collected.append((src, dest))
    return collected

# Client-specific data files
datas = []

# Include client modules
datas += collect_dir('client', 'client')

# Include client overlay if exists
if os.path.exists('client/overlay'):
    datas += collect_dir('client/overlay', 'overlay')

# Include Rust overlay executable if it exists
overlay_exe = 'overlay/target/release/Asystent Overlay.exe'
if os.path.exists(overlay_exe):
    datas.append((overlay_exe, 'overlay'))
    # Also include the webview2 loader if it exists
    webview_loader_path = os.path.join(os.path.dirname(overlay_exe), 'WebView2Loader.dll')
    if os.path.exists(webview_loader_path):
        datas.append((webview_loader_path, 'overlay'))

# Include shared resources (if any)
if os.path.exists('resources'):
    datas += collect_dir('resources', 'resources')

# Include essential config files
essential_files = [
    ('client_main.py', '.'),
    ('main.py', '.'),
    ('dependency_manager.py', '.'),  # Critical for runtime dependency management
    ('gaja.ico', '.'),
]

for file_path, dest in essential_files:
    if os.path.exists(file_path):
        datas.append((file_path, dest))

# Client dependencies analysis
a = Analysis(
    ['client_main.py'],  # Dedicated client entry point
    pathex=['.', 'client'],
    binaries=[],
    datas=datas,    hiddenimports=[
        # WebSocket communication
        'websockets',
        'websockets.client',

        # Dependency management (critical for runtime)
        'dependency_manager',
        'aiohttp',
        'aiofiles',

        # Core dependencies only
        'loguru',
        'requests',
        'pydantic',
        'psutil',
        'numpy',  # Keep numpy as it's used by many modules

        # GUI/Overlay
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',

        # Client modules
        'client.client_main',
        'client.config',
        'client.shared_state',
        'client.active_window_module',

        # Client audio modules (structure only)
        'client.audio_modules',

        # Essential system modules
        'json',
        'pathlib',
        'logging',
        'asyncio',
        'threading',
        'queue',
        'typing',
        'configparser',
        'urllib.parse',
        'edge_tts',

        # Heavy dependencies - downloaded by dependency_manager at runtime
        # 'sounddevice',     # Downloaded dynamically
        # 'librosa',         # Downloaded dynamically
        # 'whisper',         # Downloaded dynamically
        # 'faster_whisper',  # Downloaded dynamically
        # 'torch',           # Downloaded dynamically
        # 'torchaudio',      # Downloaded dynamically
        # 'openwakeword',    # Downloaded dynamically
        # 'pvporcupine',     # Downloaded dynamically
    ],
    hookspath=[],
    runtime_hooks=[],excludes=[
        # Heavy ML packages - downloaded by dependency_manager at runtime
        'torch',
        'torchvision',
        'torchaudio',
        'torch.nn',
        'torch.optim',
        'torch.cuda',
        'sounddevice',
        'librosa',
        'whisper',
        'openai-whisper',
        'faster_whisper',
        'openwakeword',
        'pvporcupine',

        # Server-specific modules
        'fastapi',
        'uvicorn',
        'flask',
        'flask_cors',
        'sqlalchemy',
        'alembic',
        'anthropic',
        'python_multipart',
        'python_jose',
        'passlib',
        'schedule',
        'beautifulsoup4',
        'watchdog',

        # Heavy packages not needed for basic client
        'scipy',
        'sklearn',
        'matplotlib',
        'cv2',
        'PIL',
        'pandas',
        'jupyter',
        'notebook',
        'ipython',
        'tensorflow',
        'keras',

        # Development tools
        'pytest',
        'black',
        'flake8',
        'mypy',
        'isort',
        'bandit',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GajaClient',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='gaja.ico',
    argv_emulation=False,
)

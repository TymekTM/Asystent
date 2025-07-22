# gaja_server.spec - Server Build Configuration
# PyInstaller spec file for GAJA Assistant Server

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

# Server-specific data files
datas = []

# Include server modules
datas += collect_dir('server', 'server')

# Include shared resources (if any)
if os.path.exists('resources'):
    datas += collect_dir('resources', 'resources')

# Include essential config files
essential_files = [
    ('server_main.py', '.'),
    ('main.py', '.'),
    ('gaja.ico', '.'),
]

for file_path, dest in essential_files:
    if os.path.exists(file_path):
        datas.append((file_path, dest))

# Server dependencies analysis
a = Analysis(
    ['server_main.py'],  # Dedicated server entry point
    pathex=['.', 'server'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # FastAPI and web framework
        'fastapi',
        'uvicorn',
        'uvicorn.main',
        'uvicorn.server',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'websockets',
        'websockets.server',
        'websockets.client',
        'flask',
        'flask_cors',

        # Database
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'alembic',

        # AI providers
        'openai',
        'anthropic',

        # Server modules
        'server.server_main',
        'server.ai_module',
        'server.database_manager',
        'server.database_models',
        'server.config_loader',
        'server.function_calling_system',
        'server.plugin_manager',
        'server.performance_monitor',
        'server.prompt_builder',
        'server.prompts',

        # Server plugins
        'server.modules.weather_module',
        'server.modules.search_module',
        'server.modules.memory_module',
        'server.modules.api_module',

        # Utilities
        'requests',
        'python_multipart',
        'pydantic',
        'python_jose',
        'passlib',
        'loguru',
        'schedule',
        'beautifulsoup4',
        'watchdog',
        'json',
        'pathlib',
        'logging',
        'asyncio',
        'typing',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Client-specific modules
        'sounddevice',
        'librosa',
        'whisper',
        'faster_whisper',
        'torch',
        'torchaudio',
        'openwakeword',
        'pvporcupine',
        'tkinter',
        'edge_tts',

        # Heavy ML packages not needed for server
        'scipy',
        'sklearn',
        'matplotlib',
        'cv2',
        'PIL',
        'pandas',
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
    name='GajaServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='gaja.ico',
    # Add server argument by default
    argv_emulation=False,
)

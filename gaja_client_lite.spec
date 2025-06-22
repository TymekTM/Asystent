# gaja_client_lite.spec - Lightweight Client Build (for testing)
# Minimal client build without heavy audio/ML dependencies

block_cipher = None
import os
import sys
from PyInstaller.utils.hooks import collect_data_files

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

# Minimal client data files
datas = []

# Include essential client config only
datas += [
    ('client_main.py', '.'),
    ('main.py', '.'),
    ('gaja.ico', '.'),
]

# Include minimal client modules
if os.path.exists('client/config.py'):
    datas.append(('client/config.py', 'client'))
if os.path.exists('client/shared_state.py'):
    datas.append(('client/shared_state.py', 'client'))

# Minimal client dependencies analysis
a = Analysis(
    ['client_main.py'],  # Dedicated client entry point
    pathex=['.', 'client'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Core communication only
        'websockets',
        'websockets.client',

        # Basic utilities
        'loguru',
        'requests',
        'pydantic',
        'json',
        'pathlib',
        'logging',
        'asyncio',
        'threading',
        'configparser',

        # Client core
        'client.client_main',
        'client.config',
        'client.shared_state',

        # Basic GUI
        'tkinter',
        'tkinter.ttk',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Exclude ALL heavy dependencies
        'torch',
        'torchvision',
        'torchaudio',
        'whisper',
        'faster_whisper',
        'openai',
        'sounddevice',
        'librosa',
        'numpy',
        'scipy',
        'sklearn',
        'matplotlib',
        'cv2',
        'PIL',
        'pandas',
        'openwakeword',
        'pvporcupine',
        'edge_tts',

        # Server dependencies
        'fastapi',
        'uvicorn',
        'flask',
        'sqlalchemy',
        'anthropic',

        # Development tools
        'pytest',
        'jupyter',
        'notebook',
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
    name='GajaClientLite',
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

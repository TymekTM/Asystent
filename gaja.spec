# gaja.spec — wersja 2.1.0 - Normalny EXE z automatycznym doinstalowywaniem brakujących pakietów

block_cipher = None
import os

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

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,    hiddenimports=[
        # Essential for dependency manager
        'dependency_manager',
        'subprocess',
        'json',
        'pathlib',
        'logging',
        'shutil',
          # Essential stdlib imports
        'timeit',           # Required by openwakeword
        'wave',            # Required by openwakeword
        'fileinput',       # Required by openwakeword
        
        # Remove these heavy imports - they'll be downloaded by dependency manager
        # 'tqdm.auto',         # Will be downloaded
        # 'tqdm.contrib',      # Will be downloaded  
        # 'huggingface_hub',   # Will be downloaded
        # 'transformers',      # Will be downloaded
        # 'whisper',           # Will be downloaded
    ],
    hookspath=[],
    runtime_hooks=[],    excludes=[
        # Exclude all heavy ML/AI libraries - they'll be downloaded by dependency manager
        'tensorflow',
        'torch',
        'torchvision', 
        'torchaudio',
        'scipy',
        'numpy',  # Will be included by dependency if needed
        'matplotlib',
        'cv2',
        'sklearn',
        'scikit_learn',
        'huggingface_hub',
        'transformers', 
        'faster_whisper',
        'openwakeword',
        'whisper',
        'tqdm',
        'sounddevice',
        
        # Other heavy packages
        'pandas',
        'PIL',
        'Pillow',
        'requests',  # Common, but let dependency manager handle it
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,    cipher=block_cipher,
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

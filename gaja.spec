# gaja.spec — wersja 1.1.0

block_cipher = None
import os

# Helper to collect all files under a directory into datas with relative dest
def collect_dir(src_dir, dest_prefix):
    collected = []
    for root, dirs, files in os.walk(src_dir):
        for fname in files:
            src = os.path.join(root, fname)
            rel_root = os.path.relpath(root, src_dir)
            dest = os.path.join(dest_prefix, rel_root)
            collected.append((src, dest))
    return collected

datas = []
# Include all audio module files
datas += collect_dir('audio_modules', 'audio_modules')
# Include web UI code
datas += collect_dir('web_ui', 'web_ui')
# Include templates for Flask
datas += collect_dir('web_ui/templates', 'templates')
# Include static assets for Flask
datas += collect_dir('web_ui/static', 'static')
# Include documentation and resources
datas += collect_dir('docs', 'docs')
datas += collect_dir('resources', 'resources')
# Include dynamic modules
datas += collect_dir('modules', 'modules')

# Dodaj pojedyncze pliki ręcznie
datas += [
    ('config.py', '.'),
    ('database_manager.py', '.'),
    ('database_models.py', '.'),
]

a = Analysis(
    ['main.py'],  # zmień na 'assistant.py' jeśli to punkt wejścia
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['sklearn.feature_extraction.text'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Gaja',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='gaja.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='Gaja'
)

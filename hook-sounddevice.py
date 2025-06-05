# PyInstaller hook for sounddevice package
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules
import os

# Collect all sounddevice data files and submodules
datas = collect_data_files('sounddevice')
binaries = collect_dynamic_libs('sounddevice')
hiddenimports = collect_submodules('sounddevice')

# Ensure the native _sounddevice extension is included
hiddenimports.extend([
    'sounddevice._sounddevice',
    '_sounddevice',
    'cffi',
    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',
])

# Try to manually locate and include the _sounddevice extension
try:
    import sounddevice
    import _sounddevice
    
    sd_path = os.path.dirname(sounddevice.__file__)
    ext_path = _sounddevice.__file__
    
    # Add the extension binary to the collection
    if ext_path and os.path.exists(ext_path):
        binaries.append((ext_path, '.'))
        print(f"hook-sounddevice: Found _sounddevice extension at {ext_path}")
    
    # Look for additional PortAudio DLLs in the sounddevice directory
    portaudio_files = [
        'libportaudio.dll', 'portaudio.dll', 'libportaudio64.dll',
        '_portaudio.pyd', '_portaudio.so', '_portaudio.dll'
    ]
    
    for file_name in portaudio_files:
        file_path = os.path.join(sd_path, file_name)
        if os.path.exists(file_path):
            binaries.append((file_path, '.'))
            print(f"hook-sounddevice: Found PortAudio file at {file_path}")
    
except ImportError as e:
    print(f"hook-sounddevice: Warning - Could not import sounddevice/_sounddevice: {e}")
except Exception as e:
    print(f"hook-sounddevice: Error during collection: {e}")

# Add CFFI-related files if available
try:
    cffi_binaries = collect_dynamic_libs('cffi')
    binaries.extend(cffi_binaries)
    
    # Include CFFI submodules that might be needed
    hiddenimports.extend([
        'cffi.api',
        'cffi.backend_ctypes',
        'cffi.ffibuilder',
        'cffi.setuptools_ext',
    ])
    
    print("hook-sounddevice: Collected CFFI dependencies")
except Exception as e:
    print(f"hook-sounddevice: Could not collect CFFI dependencies: {e}")

print(f"hook-sounddevice: Collected {len(binaries)} binaries, {len(datas)} data files")
print(f"hook-sounddevice: Hidden imports: {hiddenimports}")

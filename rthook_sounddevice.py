# Runtime hook for sounddevice - loads before main application starts
import os
import sys
import ctypes

def setup_sounddevice_runtime():
    """Setup sounddevice runtime environment for PyInstaller"""
    try:
        print("🔧 Setting up sounddevice runtime environment...")
        
        # Add multiple directories to PATH for DLL loading
        if getattr(sys, 'frozen', False):
            # Get the executable directory
            app_dir = os.path.dirname(sys.executable)
            
            # Add executable directory and common subdirectories to PATH
            path_dirs = [
                app_dir,  # Main executable directory
                os.path.join(app_dir, '_internal'),  # PyInstaller internal directory
                os.path.join(app_dir, 'sounddevice'),  # Sounddevice subdirectory
            ]
            
            # Add PyInstaller's temporary directory if available
            if hasattr(sys, '_MEIPASS'):
                path_dirs.extend([
                    sys._MEIPASS,  # PyInstaller extraction directory
                    os.path.join(sys._MEIPASS, '_internal'),
                    os.path.join(sys._MEIPASS, 'sounddevice'),
                ])
            
            current_path = os.environ.get('PATH', '')
            for path_dir in path_dirs:
                if os.path.exists(path_dir) and path_dir not in current_path:
                    os.environ['PATH'] = path_dir + os.pathsep + current_path
                    current_path = os.environ['PATH']
                    print(f"   Added to PATH: {path_dir}")
        
        # Try to preload critical DLLs in order of dependency
        dll_candidates = []
        
        # Determine search locations
        search_paths = []
        if getattr(sys, 'frozen', False):
            search_paths.append(os.path.dirname(sys.executable))
            if hasattr(sys, '_MEIPASS'):
                search_paths.append(sys._MEIPASS)
                search_paths.append(os.path.join(sys._MEIPASS, '_internal'))
        
        # Find all potential DLL files
        dll_names = [
            'libportaudio.dll',    # PortAudio library
            'portaudio.dll',       # Alternative PortAudio name
            'libportaudio64.dll',  # 64-bit PortAudio
            '_portaudio.pyd',      # Python extension for PortAudio
            '_sounddevice.pyd',    # Main sounddevice extension
            '_sounddevice.dll',    # Alternative extension format
        ]
        
        for search_path in search_paths:
            for dll_name in dll_names:
                dll_path = os.path.join(search_path, dll_name)
                if os.path.exists(dll_path):
                    dll_candidates.append((dll_name, dll_path))
        
        # Try to preload DLLs in dependency order
        loaded_dlls = []
        for dll_name, dll_path in dll_candidates:
            try:
                # Try to load the DLL
                handle = ctypes.CDLL(dll_path)
                loaded_dlls.append(dll_name)
                print(f"   ✅ Preloaded: {dll_name}")
            except Exception as e:
                print(f"   ⚠️  Failed to preload {dll_name}: {e}")
        
        if loaded_dlls:
            print(f"   Successfully preloaded {len(loaded_dlls)} DLL(s)")
        
        # Set CFFI debugging if available
        os.environ['CFFI_TMPDIR'] = os.path.join(os.path.dirname(sys.executable), 'cffi_temp')
        
        # Test sounddevice import early with detailed error reporting
        try:
            print("🧪 Testing sounddevice import...")
            import sounddevice as sd
            
            # Try to query devices to verify functionality
            try:
                devices = sd.query_devices()
                device_count = len(devices) if devices else 0
                print(f"   ✅ sounddevice loaded successfully ({device_count} audio devices detected)")
                
                # Verify _sounddevice extension is accessible
                try:
                    import sounddevice._sounddevice
                    print("   ✅ _sounddevice extension accessible")
                except ImportError as ext_err:
                    print(f"   ⚠️  _sounddevice extension not accessible: {ext_err}")
                
            except Exception as query_err:
                print(f"   ⚠️  sounddevice loaded but device query failed: {query_err}")
                
        except ImportError as import_err:
            print(f"   ❌ sounddevice import failed: {import_err}")
            
            # Try alternative import strategies
            print("   🔄 Trying alternative import strategies...")
            
            # Strategy 1: Add current directory to Python path
            current_dir = os.getcwd()
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
                try:
                    import sounddevice as sd
                    print("   ✅ Alternative import successful (current directory)")
                except ImportError:
                    pass
            
            # Strategy 2: Force reload sys.modules
            if 'sounddevice' in sys.modules:
                del sys.modules['sounddevice']
            if '_sounddevice' in sys.modules:
                del sys.modules['_sounddevice']
            
            try:
                import sounddevice as sd
                print("   ✅ Alternative import successful (module reload)")
            except ImportError as final_err:
                print(f"   ❌ All import strategies failed: {final_err}")
                
        except Exception as general_err:
            print(f"   ❌ sounddevice error: {general_err}")
            
    except Exception as setup_err:
        print(f"❌ Runtime hook setup error: {setup_err}")
        import traceback
        traceback.print_exc()

# Execute the setup
setup_sounddevice_runtime()

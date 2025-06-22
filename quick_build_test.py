#!/usr/bin/env python3
"""
GAJA Assistant - Quick Build Test
Test build process without actually building EXE to identify potential issues.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def quick_test():
    """Quick test of build process without full PyInstaller run."""
    print("[TEST] Quick Build System Test")
    print("=" * 40)
    
    # Test 1: Check if PyInstaller is available
    print("[1/5] Checking PyInstaller...")
    try:
        import PyInstaller
        print(f"   ✅ PyInstaller {PyInstaller.__version__} available")
    except ImportError:
        print("   ❌ PyInstaller not installed")
        return False
    
    # Test 2: Check spec file
    print("[2/5] Checking spec file...")
    spec_file = "gaja_client.spec"
    if os.path.exists(spec_file):
        print(f"   ✅ {spec_file} exists")
        
        # Check spec file content
        with open(spec_file, 'r') as f:
            content = f.read()
            if 'client_main.py' in content:
                print("   ✅ Spec file references correct entry point")
            else:
                print("   ⚠️  Spec file might have wrong entry point")
    else:
        print(f"   ❌ {spec_file} missing")
        return False
    
    # Test 3: Check entry point
    print("[3/5] Checking entry point...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import client_main
        print("   ✅ client_main.py imports successfully")
    except Exception as e:
        print(f"   ❌ client_main.py import failed: {e}")
        return False
    
    # Test 4: Check critical dependencies
    print("[4/5] Checking critical client dependencies...")
    critical_deps = ['websockets', 'pydantic', 'loguru']
    for dep in critical_deps:
        try:
            __import__(dep)
            print(f"   ✅ {dep} available")
        except ImportError:
            print(f"   ⚠️  {dep} missing (might be installed during build)")
    
    # Test 5: Simulate PyInstaller analysis (without actual build)
    print("[5/5] Testing PyInstaller analysis...")
    try:
        cmd = [sys.executable, "-m", "PyInstaller", "--help"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("   ✅ PyInstaller command works")
        else:
            print("   ❌ PyInstaller command failed")
            return False
    except subprocess.TimeoutExpired:
        print("   ❌ PyInstaller command timed out")
        return False
    except Exception as e:
        print(f"   ❌ PyInstaller test failed: {e}")
        return False
    
    print("\n[RESULT] Quick test completed successfully!")
    print("Build process should work, but might be slow due to:")
    print("- Large client dependencies (audio, ML models)")
    print("- First-time compilation of dependencies")
    print("- Antivirus scanning during build")
    
    return True

def identify_slow_components():
    """Identify what might be causing slow build."""
    print("\n[ANALYSIS] Potential slow build causes:")
    print("=" * 40)
    
    # Check for heavy dependencies
    heavy_deps = {
        'torch': 'PyTorch (very large)',
        'torchaudio': 'TorchAudio (large)', 
        'whisper': 'OpenAI Whisper (ML models)',
        'faster_whisper': 'Faster Whisper (optimized)',
        'sounddevice': 'Audio processing',
        'librosa': 'Audio analysis',
        'numpy': 'Numerical computing'
    }
    
    for dep, desc in heavy_deps.items():
        try:
            __import__(dep)
            print(f"   📦 {dep} installed - {desc}")
        except ImportError:
            print(f"   ⚪ {dep} not installed")
    
    # Check dist directory size if it exists
    dist_path = Path("dist")
    if dist_path.exists():
        try:
            size = sum(f.stat().st_size for f in dist_path.rglob('*') if f.is_file())
            size_mb = size / (1024 * 1024)
            print(f"\n   📊 Current dist/ size: {size_mb:.1f} MB")
        except:
            print("   📊 Could not calculate dist/ size")

def main():
    """Main test function."""
    start_time = time.time()
    
    success = quick_test()
    identify_slow_components()
    
    elapsed = time.time() - start_time
    print(f"\n[TIME] Test completed in {elapsed:.1f} seconds")
    
    if success:
        print("\n[RECOMMENDATION] Build system appears healthy.")
        print("If build is slow, try:")
        print("1. python build.py --skip-overlay  # Skip Rust overlay")
        print("2. Add --exclude to PyInstaller for unused heavy deps")
        print("3. Use legacy build if needed: python build.py --component legacy")
        return 0
    else:
        print("\n[ERROR] Build system has issues that need fixing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test script to verify the dependency manager and torch guard fixes
"""

import sys
import os
import subprocess
from pathlib import Path

def test_dependency_manager():
    """Test the dependency manager functionality"""
    print("🧪 TESTING DEPENDENCY MANAGER")
    print("=" * 50)
    
    # Import dependency manager
    try:
        from dependency_manager import DependencyManager
        print("✅ dependency_manager import successful")
    except Exception as e:
        print(f"❌ dependency_manager import failed: {e}")
        return False
    
    # Test manager initialization
    try:
        manager = DependencyManager()
        print("✅ DependencyManager initialization successful")
    except Exception as e:
        print(f"❌ DependencyManager initialization failed: {e}")
        return False
    
    # Test package checking
    try:
        missing = manager.check_missing_packages()
        print(f"✅ Package checking successful - Missing: {len(missing)} packages")
        if missing:
            print(f"   Missing packages: {', '.join(missing)}")
    except Exception as e:
        print(f"❌ Package checking failed: {e}")
        return False
    
    return True

def test_torch_guard():
    """Test the torch guard in whisper_asr"""
    print("\n🧪 TESTING TORCH GUARD")
    print("=" * 50)
    
    try:
        # Try to import whisper_asr
        sys.path.insert(0, str(Path(__file__).parent / "audio_modules"))
        from whisper_asr import WhisperASR
        print("✅ whisper_asr import successful")
        
        # Try to create WhisperASR instance
        asr = WhisperASR()
        print("✅ WhisperASR initialization successful")
        print(f"   Available: {asr.available}")
        
        return True
    except Exception as e:
        print(f"❌ WhisperASR test failed: {e}")
        return False

def test_build_size():
    """Check if the built EXE exists and get its size"""
    print("\n🧪 TESTING BUILD SIZE")
    print("=" * 50)
    
    exe_path = Path("release/Gaja.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ Gaja.exe exists")
        print(f"   Size: {size_mb:.1f} MB")
        
        # Check if size is reasonable (< 100 MB)
        if size_mb < 100:
            print(f"✅ Size is reasonable (< 100 MB)")
            return True
        else:
            print(f"⚠️ Size might be too large (> 100 MB)")
            return False
    else:
        print(f"❌ Gaja.exe not found at {exe_path}")
        return False

def main():
    """Run all tests"""
    print("🚀 RUNNING DEPENDENCY AND BUILD TESTS")
    print("=" * 60)
    
    results = []
    
    # Test 1: Dependency Manager
    results.append(test_dependency_manager())
    
    # Test 2: Torch Guard
    results.append(test_torch_guard())
    
    # Test 3: Build Size
    results.append(test_build_size())
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    test_names = ["Dependency Manager", "Torch Guard", "Build Size"]
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The fixes are working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

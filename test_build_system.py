"""
Test skrypt dla systemu automatycznego pobierania zależności
"""

import sys
import os
from pathlib import Path

def test_dependency_manager():
    """Test menedżera zależności bez kompilacji"""
    print("🧪 Test menedżera zależności")
    print("=" * 40)
    
    try:
        from dependency_manager import DependencyManager
        
        manager = DependencyManager()
        
        print(f"📁 Folder aplikacji: {manager.app_dir}")
        print(f"📦 Folder zależności: {manager.deps_dir}")
        print(f"� Folder pakietów: {manager.packages_dir}")
        print(f"� Folder cache: {manager.cache_dir}")
        
        print(f"\n🔍 Status inicjalizacji: {manager.is_initialized()}")
        
        if manager.is_initialized():
            status = manager.get_installation_status()
            print(f"📊 Status instalacji: {status}")
        
        # Test sprawdzania brakujących pakietów
        print(f"\n🔍 Sprawdzanie brakujących pakietów...")
        missing = manager.check_missing_packages()
        print(f"📊 Brakuje pakietów: {len(missing)}")
        
        print("\n✅ Test menedżera zależności przeszedł pomyślnie!")
        return True
        
    except Exception as e:
        print(f"\n❌ Błąd testu: {e}")
        return False

def test_imports():
    """Test importów podstawowych modułów"""
    print("\n🧪 Test importów")
    print("=" * 40)
    
    modules_to_test = [
        'pathlib',
        'json',
        'os',
        'sys',
        'subprocess',
        'zipfile',
        'time'
    ]
    
    success_count = 0
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module}: {e}")
    
    print(f"\n📊 Pomyślne importy: {success_count}/{len(modules_to_test)}")
    
    # Test requests (może nie być dostępny)
    try:
        import requests
        print("✅ requests (dostępny)")
    except ImportError:
        print("⚠️  requests (brak - będzie używany fallback urllib)")
    
    return success_count == len(modules_to_test)

def test_build_config():
    """Test konfiguracji build"""
    print("\n🧪 Test konfiguracji build")
    print("=" * 40)
    
    files_to_check = [
        'gaja.spec',
        'build.py',
        'dependency_manager.py',
        'requirements_build.txt'
    ]
    
    success_count = 0
    
    for file in files_to_check:
        if Path(file).exists():
            print(f"✅ {file}")
            success_count += 1
        else:
            print(f"❌ {file} (brak)")
    
    print(f"\n📊 Pliki gotowe: {success_count}/{len(files_to_check)}")
    return success_count == len(files_to_check)

def main():
    """Główna funkcja testowa"""
    print("🚀 Test systemu automatycznego pobierania zależności")
    print("=" * 60)
    
    results = []
    
    # Test 1: Menedżer zależności
    results.append(test_dependency_manager())
    
    # Test 2: Importy
    results.append(test_imports())
    
    # Test 3: Konfiguracja build
    results.append(test_build_config())
    
    print("\n" + "=" * 60)
    print("📊 PODSUMOWANIE TESTÓW")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Przeszło: {passed}/{total}")
    
    if passed == total:
        print("🎉 Wszystkie testy przeszły pomyślnie!")
        print("🚀 Możesz uruchomić: python build.py")
    else:
        print("❌ Niektóre testy nie przeszły")
        print("🔧 Sprawdź błędy powyżej przed kompilacją")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    print(f"\n{'✅ GOTOWE' if success else '❌ BŁĘDY'}")
    input("Naciśnij Enter aby zamknąć...")

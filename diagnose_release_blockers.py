#!/usr/bin/env python3
"""
Diagnostyka komponentów GAJA - sprawdza co blokuje finalne wydanie
"""

import sys
import os
import traceback
from pathlib import Path

# Dodaj ścieżkę do modułów klienta
sys.path.append(str(Path(__file__).parent / "client"))

def test_imports():
    """Test wszystkich importów audio modułów"""
    print("🔍 TESTOWANIE IMPORTÓW MODUŁÓW AUDIO")
    print("=" * 50)
    
    results = {}
    
    # Test 1: Optimized Wakeword Detector
    try:
        from client.audio_modules.optimized_wakeword_detector import create_wakeword_detector
        print("✅ Optimized Wakeword Detector - import OK")
        results['optimized_wakeword'] = True
    except Exception as e:
        print(f"❌ Optimized Wakeword Detector - BŁĄD: {e}")
        results['optimized_wakeword'] = False
    
    # Test 2: Optimized Whisper ASR
    try:
        from client.audio_modules.optimized_whisper_asr import OptimizedWhisperASR
        print("✅ Optimized Whisper ASR - import OK")
        results['optimized_whisper'] = True
    except Exception as e:
        print(f"❌ Optimized Whisper ASR - BŁĄD: {e}")
        results['optimized_whisper'] = False
    
    # Test 3: TTS Module
    try:
        from client.audio_modules.tts_module import TTSModule
        print("✅ TTS Module - import OK")
        results['tts'] = True
    except Exception as e:
        print(f"❌ TTS Module - BŁĄD: {e}")
        results['tts'] = False
    
    # Test 4: SoundDevice
    try:
        import sounddevice as sd
        print("✅ SoundDevice - import OK")
        results['sounddevice'] = True
    except Exception as e:
        print(f"❌ SoundDevice - BŁĄD: {e}")
        results['sounddevice'] = False
    
    return results

def test_wakeword_models():
    """Test modeli wakeword"""
    print("\n🔍 TESTOWANIE MODELI WAKEWORD")
    print("=" * 50)
    
    model_dir = Path("client/resources/openWakeWord")
    if not model_dir.exists():
        print(f"❌ Katalog modeli nie istnieje: {model_dir}")
        return False
    
    onnx_files = list(model_dir.glob("*.onnx"))
    tflite_files = list(model_dir.glob("*.tflite"))
    
    print(f"📁 Znalezione pliki .onnx: {len(onnx_files)}")
    for f in onnx_files:
        print(f"   - {f.name}")
    
    print(f"📁 Znalezione pliki .tflite: {len(tflite_files)}")
    for f in tflite_files:
        print(f"   - {f.name}")
    
    # Test konfliktów
    if onnx_files and tflite_files:
        print("⚠️  UWAGA: Masz zarówno pliki .onnx jak i .tflite - może powodować konflikty")
    
    # Test OpenWakeWord
    try:
        from openwakeword import Model
        print("✅ OpenWakeWord library dostępna")
        
        # Test ładowania tylko .onnx
        if onnx_files:
            onnx_models = [str(f) for f in onnx_files if not any(x in f.name.lower() for x in ["preprocessor", "embedding", "melspectrogram"])][:2]
            if onnx_models:
                model = Model(wakeword_models=onnx_models, inference_framework="onnx")
                print(f"✅ Załadowano {len(onnx_models)} modeli .onnx")
                del model
            else:
                print("❌ Brak odpowiednich modeli .onnx")
        
    except Exception as e:
        print(f"❌ OpenWakeWord - BŁĄD: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_whisper():
    """Test Whisper ASR"""
    print("\n🔍 TESTOWANIE WHISPER ASR")
    print("=" * 50)
    
    try:
        from faster_whisper import WhisperModel
        print("✅ faster-whisper dostępny")
        
        # Test ładowania małego modelu
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            print("✅ Model 'tiny' załadowany pomyślnie")
            del model
        except Exception as e:
            print(f"❌ Błąd ładowania modelu: {e}")
            return False
            
    except ImportError:
        print("❌ faster-whisper niedostępny")
        return False
    except Exception as e:
        print(f"❌ Whisper - BŁĄD: {e}")
        return False
    
    return True

def test_overlay_communication():
    """Test komunikacji overlay"""
    print("\n🔍 TESTOWANIE KOMUNIKACJI OVERLAY")
    print("=" * 50)
    
    try:
        import asyncio
        import websockets
        import json
        
        async def test_ws():
            try:
                # Test połączenia z serwerem
                async with websockets.connect("ws://localhost:8001/ws/test_diagnostic", timeout=5) as ws:
                    print("✅ Połączenie z serwerem GAJA udane")
                    await ws.send(json.dumps({"type": "test"}))
                    response = await asyncio.wait_for(ws.recv(), timeout=3)
                    print("✅ Komunikacja z serwerem działa")
                    return True
            except Exception as e:
                print(f"❌ Błąd komunikacji z serwerem: {e}")
                return False
        
        result = asyncio.run(test_ws())
        return result
        
    except Exception as e:
        print(f"❌ Overlay communication - BŁĄD: {e}")
        return False

def diagnose_client_startup():
    """Diagnoza problemu z uruchamianiem klienta"""
    print("\n🔍 DIAGNOZA URUCHAMIANIA KLIENTA")
    print("=" * 50)
    
    try:
        # Importuj główną klasę klienta
        from client.client_main import ClientApp
        print("✅ Import ClientApp OK")
        
        # Test inicjalizacji bez uruchamiania
        client = ClientApp()
        print("✅ Inicjalizacja ClientApp OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Błąd inicjalizacji klienta: {e}")
        traceback.print_exc()
        return False

def main():
    """Główna funkcja diagnostyczna"""
    print("🏥 DIAGNOSTYKA KOMPONENTÓW GAJA")
    print("=" * 60)
    print("Sprawdzanie komponentów blokujących finalne wydanie...")
    print()
    
    # Zmień katalog roboczy
    os.chdir(Path(__file__).parent)
    
    results = {
        'imports': test_imports(),
        'wakeword_models': test_wakeword_models(),
        'whisper': test_whisper(),
        'overlay': test_overlay_communication(),
        'client_startup': diagnose_client_startup()
    }
    
    print("\n" + "=" * 60)
    print("📊 PODSUMOWANIE DIAGNOZY")
    print("=" * 60)
    
    all_good = True
    
    # Analiza importów
    import_results = results['imports']
    print("🔧 MODUŁY AUDIO:")
    for module, status in import_results.items():
        print(f"   {'✅' if status else '❌'} {module}")
        if not status:
            all_good = False
    
    # Analiza pozostałych komponentów
    components = {
        'wakeword_models': 'Modele Wakeword',
        'whisper': 'Whisper ASR', 
        'overlay': 'Komunikacja Overlay',
        'client_startup': 'Uruchamianie Klienta'
    }
    
    print("\n🔧 KOMPONENTY SYSTEMU:")
    for key, name in components.items():
        status = results[key]
        print(f"   {'✅' if status else '❌'} {name}")
        if not status:
            all_good = False
    
    print("\n" + "=" * 60)
    if all_good:
        print("🎉 WSZYSTKIE KOMPONENTY DZIAŁAJĄ!")
        print("🚀 Gotowe do finalnego wydania")
    else:
        print("⚠️  ZNALEZIONO PROBLEMY DO NAPRAWY")
        print("🔧 Komponenty wymagają naprawy przed wydaniem")
    print("=" * 60)
    
    return all_good

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Diagnostyka przerwana")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Niespodziewany błąd: {e}")
        traceback.print_exc()
        sys.exit(1)

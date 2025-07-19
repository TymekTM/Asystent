#!/usr/bin/env python3
"""NARZĘDZIE WYKRYWANIA OVERLAY - sprawdza czy overlay jest rzeczywiście widoczny na ekranie."""

import time
import subprocess
import asyncio
import json
import websockets
from pathlib import Path
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import win32process
import psutil
from PIL import ImageGrab, Image
import numpy as np


class OverlayDetector:
    """Wykrywa czy overlay jest widoczny na ekranie."""
    
    def __init__(self):
        self.overlay_process = None
        self.client_process = None
        self.overlay_hwnd = None
        
    def find_overlay_window(self):
        """Znajdź okno overlay."""
        print("🔍 Szukam okna overlay...")
        
        def enum_windows_callback(hwnd, results):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            
            # Szukamy okna Tauri/overlay
            if any(keyword in window_text.lower() for keyword in ['overlay', 'gaja', 'tauri']) or \
               any(keyword in class_name.lower() for keyword in ['tauri', 'webview']):
                results.append((hwnd, window_text, class_name))
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        print(f"   Znaleziono {len(windows)} potencjalnych okien overlay:")
        for hwnd, title, class_name in windows:
            print(f"   - HWND: {hwnd}, Title: '{title}', Class: '{class_name}'")
        
        return windows
    
    def get_window_info(self, hwnd):
        """Pobierz informacje o oknie."""
        try:
            # Pozycja i rozmiar
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            
            # Stan okna - używamy bezpieczniejszych funkcji
            is_visible = win32gui.IsWindowVisible(hwnd)
            is_iconic = win32gui.IsIconic(hwnd)  # minimized
            
            # Sprawdź styl okna zamiast IsZoomed
            try:
                window_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                is_zoomed = bool(window_style & win32con.WS_MAXIMIZE)
            except:
                is_zoomed = False
            
            # Z-order (czy jest na wierzchu)
            is_foreground = win32gui.GetForegroundWindow() == hwnd
            
            # Extended window style (transparency, etc.)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            is_layered = bool(ex_style & win32con.WS_EX_LAYERED)
            is_transparent = bool(ex_style & win32con.WS_EX_TRANSPARENT)
            is_topmost = bool(ex_style & win32con.WS_EX_TOPMOST)
            
            return {
                'rect': rect,
                'size': (width, height),
                'visible': is_visible,
                'minimized': is_iconic,
                'maximized': is_zoomed,
                'foreground': is_foreground,
                'layered': is_layered,
                'transparent': is_transparent,
                'topmost': is_topmost,
                'ex_style': ex_style
            }
        except Exception as e:
            print(f"   ❌ Błąd pobierania informacji o oknie: {e}")
            return None
    
    def capture_screen_area(self, rect):
        """Przechwyć obszar ekranu."""
        try:
            left, top, right, bottom = rect
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            return screenshot
        except Exception as e:
            print(f"   ❌ Błąd przechwytywania ekranu: {e}")
            return None
    
    def analyze_image_content(self, image):
        """Analizuj zawartość obrazu - sprawdź czy nie jest pusty/przezroczysty."""
        if image is None:
            return False
        
        # Konwertuj do numpy array
        img_array = np.array(image)
        
        # Sprawdź czy obraz nie jest całkowicie czarny/biały/przezroczysty
        if len(img_array.shape) == 3:  # RGB
            # Sprawdź różnorodność kolorów
            std_dev = np.std(img_array)
            unique_colors = len(np.unique(img_array.reshape(-1, img_array.shape[2]), axis=0))
            
            print(f"   📊 Analiza obrazu: std_dev={std_dev:.2f}, unique_colors={unique_colors}")
            
            # Jeśli standardowe odchylenie > 10 i więcej niż 5 unikalnych kolorów, prawdopodobnie coś jest widoczne
            return std_dev > 10 and unique_colors > 5
        
        return False
    
    def check_overlay_processes(self):
        """Sprawdź procesy overlay."""
        print("🔍 Sprawdzam procesy overlay...")
        
        overlay_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if 'gaja-overlay' in proc.info['name'] or \
                   (proc.info['exe'] and 'gaja-overlay' in proc.info['exe']):
                    overlay_processes.append(proc)
            except:
                continue
        
        print(f"   Znaleziono {len(overlay_processes)} procesów overlay:")
        for proc in overlay_processes:
            print(f"   - PID: {proc.pid}, Name: {proc.name()}")
        
        return overlay_processes
    
    async def start_client_and_overlay(self):
        """Uruchom klienta i overlay."""
        print("🚀 Uruchamiam klienta...")
        
        # Uruchom klienta
        self.client_process = subprocess.Popen([
            "python", "client/client_main.py"
        ], cwd="f:/Asystent")
        
        # Czekaj na uruchomienie klienta
        await asyncio.sleep(15)
        
        if self.client_process.poll() is not None:
            print("❌ Klient nie uruchomił się")
            return False
        
        print("✅ Klient uruchomiony")
        
        # Overlay powinien uruchomić się automatycznie przez klienta
        await asyncio.sleep(5)
        
        return True
    
    async def test_overlay_visibility(self):
        """Główny test widoczności overlay."""
        print("🔧 TEST WIDOCZNOŚCI OVERLAY")
        print("=" * 50)
        
        # 1. Sprawdź procesy
        processes = self.check_overlay_processes()
        if not processes:
            print("❌ Brak procesów overlay")
            return False
        
        # 2. Znajdź okna overlay
        windows = self.find_overlay_window()
        if not windows:
            print("❌ Nie znaleziono okien overlay")
            return False
        
        # 3. Analizuj każde okno
        for hwnd, title, class_name in windows:
            print(f"\n🔍 Analizuję okno: '{title}' (HWND: {hwnd})")
            
            info = self.get_window_info(hwnd)
            if not info:
                continue
            
            print(f"   📏 Pozycja: {info['rect']}")
            print(f"   📏 Rozmiar: {info['size']}")
            print(f"   👁️ Widoczne: {info['visible']}")
            print(f"   📦 Minimized: {info['minimized']}")
            print(f"   🔝 Topmost: {info['topmost']}")
            print(f"   👻 Transparent: {info['transparent']}")
            print(f"   🎭 Layered: {info['layered']}")
            print(f"   🎯 Foreground: {info['foreground']}")
            
            # Sprawdź czy okno ma sensowny rozmiar
            width, height = info['size']
            if width < 50 or height < 50:
                print("   ⚠️ Okno zbyt małe")
                continue
            
            # Sprawdź czy okno jest na ekranie
            left, top, right, bottom = info['rect']
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            
            if right < 0 or bottom < 0 or left > screen_width or top > screen_height:
                print("   ⚠️ Okno poza ekranem")
                continue
            
            print("   📸 Przechwytywanie zawartości okna...")
            
            # Przechwyć zawartość okna
            screenshot = self.capture_screen_area(info['rect'])
            if screenshot:
                # Zapisz screenshot dla debugowania
                screenshot.save(f"overlay_screenshot_{hwnd}.png")
                print(f"   💾 Screenshot zapisany: overlay_screenshot_{hwnd}.png")
                
                # Analizuj zawartość
                has_content = self.analyze_image_content(screenshot)
                print(f"   🎯 Ma widoczną zawartość: {has_content}")
                
                if has_content:
                    print("   ✅ OVERLAY WIDOCZNY!")
                    self.overlay_hwnd = hwnd
                    return True
                else:
                    print("   ⚠️ Overlay pusty/przezroczysty")
            else:
                print("   ❌ Nie udało się przechwycić zawartości")
        
        print("❌ Żaden overlay nie jest poprawnie widoczny")
        return False
    
    async def test_overlay_responsiveness(self):
        """Test czy overlay reaguje na zmiany stanu."""
        if not self.overlay_hwnd:
            print("❌ Brak wykrytego overlay do testowania")
            return False
        
        print("\n🎭 TEST RESPONSYWNOŚCI OVERLAY")
        print("=" * 50)
        
        try:
            # Połącz się z klientem przez WebSocket
            websocket = await websockets.connect("ws://localhost:6001")
            print("✅ Połączono z klientem WebSocket")
            
            # Wyślij stan testowy
            test_state = {
                "type": "status",
                "data": {
                    "status": "TEST_VISIBILITY",
                    "text": "🔴 TEST WIDOCZNOŚCI - Ten tekst powinien być widoczny!",
                    "is_listening": True,
                    "is_speaking": False,
                    "wake_word_detected": True,
                    "overlay_visible": True,
                    "monitoring": True
                }
            }
            
            print("📤 Wysyłam stan testowy...")
            await websocket.send(json.dumps(test_state))
            
            # Czekaj chwilę na aktualizację
            await asyncio.sleep(3)
            
            # Przechwyć ekran ponownie
            print("📸 Przechwytywanie po zmianie stanu...")
            info = self.get_window_info(self.overlay_hwnd)
            if info:
                screenshot = self.capture_screen_area(info['rect'])
                if screenshot:
                    screenshot.save("overlay_after_update.png")
                    print("💾 Screenshot po aktualizacji: overlay_after_update.png")
                    
                    has_content = self.analyze_image_content(screenshot)
                    print(f"🎯 Ma zawartość po aktualizacji: {has_content}")
                    
                    if has_content:
                        print("✅ OVERLAY REAGUJE NA ZMIANY!")
                        return True
            
            await websocket.close()
            
        except Exception as e:
            print(f"❌ Błąd testu responsywności: {e}")
        
        return False
    
    async def cleanup(self):
        """Wyczyść zasoby."""
        print("\n🧹 Sprzątam...")
        
        if self.client_process and self.client_process.poll() is None:
            self.client_process.terminate()
            await asyncio.sleep(3)
            if self.client_process.poll() is None:
                self.client_process.kill()
            print("🛑 Klient zatrzymany")


async def main():
    """Główna funkcja testu."""
    print("🔧 NARZĘDZIE WYKRYWANIA OVERLAY NA EKRANIE")
    print("=" * 60)
    print("To narzędzie sprawdzi czy overlay jest rzeczywiście")
    print("widoczny na ekranie i czy reaguje na zmiany stanu")
    print("=" * 60)
    
    detector = OverlayDetector()
    
    try:
        # 1. Uruchom klienta i overlay
        started = await detector.start_client_and_overlay()
        if not started:
            return
        
        # Czekaj chwilę na stabilizację
        await asyncio.sleep(5)
        
        # 2. Test widoczności
        visible = await detector.test_overlay_visibility()
        
        # 3. Test responsywności (jeśli overlay jest widoczny)
        if visible:
            responsive = await detector.test_overlay_responsiveness()
        else:
            responsive = False
        
        # 4. Podsumowanie
        print("\n" + "=" * 60)
        print("📊 WYNIKI WYKRYWANIA OVERLAY")
        print("=" * 60)
        print(f"Overlay widoczny na ekranie: {'✅' if visible else '❌'}")
        print(f"Overlay reaguje na zmiany: {'✅' if responsive else '❌'}")
        
        if not visible:
            print("\n❌ PROBLEMY Z OVERLAY:")
            print("1. Overlay może być ukryty za innymi oknami")
            print("2. Overlay może być na innym monitorze") 
            print("3. Overlay może być przezroczysty/pusty")
            print("4. Problem z renderowaniem Tauri")
            print("5. Nieprawidłowe ustawienia okna")
        
        if visible and not responsive:
            print("\n⚠️ OVERLAY WIDOCZNY ALE NIE REAGUJE:")
            print("1. Problem z WebSocket komunikacją")
            print("2. Problem z aktualizowaniem UI")
            print("3. Overlay może być zawieszony")
        
        if visible and responsive:
            print("\n🎉 OVERLAY DZIAŁA POPRAWNIE!")
            print("Sprawdź pliki screenshot*.png w katalogu")
        
    except KeyboardInterrupt:
        print("\n⏸️ Test przerwany")
    except Exception as e:
        print(f"\n❌ Błąd testu: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await detector.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

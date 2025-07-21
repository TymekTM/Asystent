#!/usr/bin/env python3
"""
Test komunikacji WebSocket - serwer i klient w jednym
"""

import asyncio
import json
import logging
import threading
import time

import websockets

# Ustaw logi
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class WebSocketTester:
    def __init__(self):
        self.server = None
        self.server_running = False

    async def handle_client(self, websocket, path):
        """Obsługa połączenia WebSocket."""
        logger.info(f"✅ Klient połączony: {websocket.remote_address}")

        try:
            # Wyślij wiadomość powitalną
            welcome = {
                "type": "welcome",
                "message": "WebSocket serwer działa!",
                "port": 6001,
                "timestamp": time.time(),
            }
            await websocket.send(json.dumps(welcome))
            logger.info("📤 Wysłano wiadomość powitalną")

            # Słuchaj wiadomości
            async for message in websocket:
                logger.info(f"📥 Otrzymano: {message}")
                # Echo odpowiedź
                response = {
                    "type": "echo",
                    "original": message,
                    "timestamp": time.time(),
                }
                await websocket.send(json.dumps(response))
                logger.info("📤 Wysłano echo")

        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 Klient rozłączony")
        except Exception as e:
            logger.error(f"❌ Błąd w obsłudze klienta: {e}")

    async def start_server(self):
        """Uruchom WebSocket serwer."""
        try:
            # Próbuj różne porty
            ports = [6001, 6000, 6002, 8765]

            for port in ports:
                try:
                    self.server = await websockets.serve(
                        self.handle_client, "127.0.0.1", port
                    )
                    logger.info(f"🚀 WebSocket serwer uruchomiony na porcie {port}")
                    logger.info(f"🔗 Adres: ws://localhost:{port}")
                    self.server_running = True
                    break
                except OSError as e:
                    logger.warning(f"⚠️ Port {port} niedostępny: {e}")
                    continue

            if not self.server:
                raise Exception("❌ Nie można uruchomić serwera na żadnym porcie")

            # Czekaj na zatrzymanie
            await self.server.wait_closed()

        except Exception as e:
            logger.error(f"❌ Błąd uruchamiania serwera: {e}")
            self.server_running = False
            raise

    async def test_client_connection(self, port=6001):
        """Test połączenia klienta."""
        uri = f"ws://localhost:{port}"
        logger.info(f"🔍 Testowanie połączenia z {uri}")

        try:
            async with websockets.connect(uri, timeout=10) as websocket:
                logger.info("✅ Połączenie udane!")

                # Wyślij wiadomość testową
                test_message = {
                    "type": "test",
                    "message": "Test z klienta",
                    "timestamp": time.time(),
                }
                await websocket.send(json.dumps(test_message))
                logger.info("📤 Wysłano wiadomość testową")

                # Czekaj na odpowiedź
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    logger.info(f"📥 Otrzymano odpowiedź: {response}")
                    return True
                except TimeoutError:
                    logger.warning("⏰ Timeout na odpowiedź")
                    return False

        except Exception as e:
            logger.error(f"❌ Błąd połączenia: {e}")
            return False

    async def run_full_test(self):
        """Uruchom pełny test."""
        logger.info("🧪 ROZPOCZYNAM PEŁNY TEST WEBSOCKET")
        logger.info("=" * 50)

        # Uruchom serwer w tle
        server_task = asyncio.create_task(self.start_server())

        # Czekaj na uruchomienie serwera
        await asyncio.sleep(2)

        if not self.server_running:
            logger.error("❌ Serwer nie uruchomił się")
            return False

        # Testuj połączenie
        success = await self.test_client_connection()

        # Zatrzymaj serwer
        if self.server:
            self.server.close()

        logger.info("=" * 50)
        logger.info(f"🎯 WYNIK TESTU: {'✅ SUKCES' if success else '❌ BŁĄD'}")

        return success


async def main():
    """Główna funkcja."""
    tester = WebSocketTester()
    try:
        result = await tester.run_full_test()
        return 0 if result else 1
    except KeyboardInterrupt:
        logger.info("🛑 Test przerwany przez użytkownika")
        return 1
    except Exception as e:
        logger.error(f"❌ Błąd krytyczny: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

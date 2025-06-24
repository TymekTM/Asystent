#!/usr/bin/env python3
"""Kompleksowy test systemu pamięci i kontekstu GAJA.

Test sprawdza poprawność działania pamięci krótkoterminowej i długoterminowej.
"""

import asyncio
import logging
import time

import aiohttp

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8001"
TEST_USER_ID = "memory_test_user_2025"


class MemoryContextTester:
    """Kompleksowy tester systemu pamięci i kontekstu."""

    def __init__(self):
        self.session = None
        self.test_results = []

    async def setup(self):
        """Inicjalizacja sesji HTTP."""
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Czyszczenie zasobów."""
        if self.session:
            await self.session.close()

    def log_test_result(
        self, test_name: str, success: bool, message: str, details: str = ""
    ):
        """Logowanie wyników testów."""
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{status} - {test_name}: {message}")
        if details:
            logger.info(f"   Details: {details}")
        self.test_results.append(
            {
                "test": test_name,
                "success": success,
                "message": message,
                "details": details,
                "timestamp": time.time(),
            }
        )

    async def send_ai_query(self, query: str, context: dict = None) -> dict:
        """Wysyła zapytanie AI do serwera."""
        url = f"{BASE_URL}/api/ai_query"
        payload = {"user_id": TEST_USER_ID, "query": query, "context": context or {}}

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"AI query failed: {response.status} - {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Error sending AI query: {e}")
            return {"error": str(e)}

    async def get_user_history(self) -> list[dict]:
        """Pobiera historię użytkownika."""
        url = f"{BASE_URL}/api/get_user_history"
        payload = {"user_id": TEST_USER_ID}

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("history", [])
                else:
                    return []
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []

    async def test_basic_memory_storage(self) -> bool:
        """Test podstawowego przechowywania informacji w pamięci."""
        try:
            # Krok 1: Powiedz AI coś do zapamiętania
            query1 = "Zapamiętaj, że moją ulubioną pizzą jest Margherita z dodatkowymi pomidorami"
            response1 = await self.send_ai_query(query1)

            if "error" in response1:
                self.log_test_result(
                    "Basic Memory Storage",
                    False,
                    f"Error in first query: {response1['error']}",
                )
                return False

            # Krok 2: Sprawdź czy AI odpowiada pozytywnie
            ai_response1 = response1.get("ai_response", "")
            if not any(
                word in ai_response1.lower()
                for word in ["zapamiętam", "zapisuję", "pamiętam", "margherita"]
            ):
                self.log_test_result(
                    "Basic Memory Storage",
                    False,
                    f"AI nie potwierdził zapamiętania informacji: {ai_response1}",
                )
                return False

            # Krótka pauza
            await asyncio.sleep(2)

            # Krok 3: Sprawdź czy informacja została zapisana
            query2 = "Jaka jest moja ulubiona pizza?"
            response2 = await self.send_ai_query(query2)

            if "error" in response2:
                self.log_test_result(
                    "Basic Memory Storage",
                    False,
                    f"Error in recall query: {response2['error']}",
                )
                return False

            ai_response2 = response2.get("ai_response", "")

            # Sprawdź czy AI pamięta informację
            if (
                "margherita" in ai_response2.lower()
                or "pomidor" in ai_response2.lower()
            ):
                self.log_test_result(
                    "Basic Memory Storage",
                    True,
                    "AI poprawnie zapamiętał i odwołał informację o ulubionym jedzeniu",
                    f"Odpowiedź: {ai_response2}",
                )
                return True
            else:
                self.log_test_result(
                    "Basic Memory Storage",
                    False,
                    f"AI nie pamiętał informacji: {ai_response2}",
                )
                return False

        except Exception as e:
            logger.error(f"Error in basic memory test: {e}")
            self.log_test_result("Basic Memory Storage", False, f"Test error: {str(e)}")
            return False

    async def test_conversation_context(self) -> bool:
        """Test kontekstu konwersacji w ramach jednej sesji."""
        try:
            # Rozpocznij konwersację na temat
            query1 = "Opowiedz mi o programowaniu w Pythonie"
            response1 = await self.send_ai_query(query1)

            if "error" in response1:
                self.log_test_result(
                    "Conversation Context",
                    False,
                    f"Error in first query: {response1['error']}",
                )
                return False

            # Krótka pauza
            await asyncio.sleep(1)

            # Zadaj pytanie nawiązujące do poprzedniej odpowiedzi
            query2 = "A jakie są najlepsze praktyki w tym języku?"
            response2 = await self.send_ai_query(query2)

            if "error" in response2:
                self.log_test_result(
                    "Conversation Context",
                    False,
                    f"Error in context query: {response2['error']}",
                )
                return False

            ai_response2 = response2.get("ai_response", "")

            # Sprawdź czy AI rozumie kontekst ("tym języku" = Python)
            if "python" in ai_response2.lower() or "język" in ai_response2.lower():
                self.log_test_result(
                    "Conversation Context",
                    True,
                    "AI poprawnie utrzymał kontekst rozmowy",
                    f"Kontekstowa odpowiedź: {ai_response2[:100]}...",
                )
                return True
            else:
                self.log_test_result(
                    "Conversation Context",
                    False,
                    f"AI nie utrzymał kontekstu rozmowy: {ai_response2[:100]}...",
                )
                return False

        except Exception as e:
            logger.error(f"Error in conversation context test: {e}")
            self.log_test_result("Conversation Context", False, f"Test error: {str(e)}")
            return False

    async def test_multi_turn_memory(self) -> bool:
        """Test pamięci w wieloetapowej konwersacji."""
        try:
            # Etap 1: Ustanów informację osobistą
            query1 = "Nazywam się Jan Kowalski i pracuję jako programista w Warszawie"
            response1 = await self.send_ai_query(query1)

            if "error" in response1:
                return False

            await asyncio.sleep(1)

            # Etap 2: Dodaj więcej informacji
            query2 = "Mam 30 lat i interesuję się sztuczną inteligencją"
            response2 = await self.send_ai_query(query2)

            if "error" in response2:
                return False

            await asyncio.sleep(1)

            # Etap 3: Sprawdź czy pamięta wcześniejsze informacje
            query3 = "Kim jestem i czym się zajmuję?"
            response3 = await self.send_ai_query(query3)

            if "error" in response3:
                return False

            ai_response3 = response3.get("ai_response", "")

            # Sprawdź czy AI pamięta wszystkie informacje
            has_name = (
                "jan" in ai_response3.lower() or "kowalski" in ai_response3.lower()
            )
            has_job = "programista" in ai_response3.lower()
            has_city = "warszaw" in ai_response3.lower()
            _ = (
                "30" in ai_response3 or "trzydzieści" in ai_response3.lower()
            )  # has_age not used

            if has_name and has_job and has_city:
                self.log_test_result(
                    "Multi-turn Memory",
                    True,
                    "AI pamięta informacje z wieloetapowej konwersacji",
                    f"Wszystkie kluczowe informacje odnalezione w: {ai_response3}",
                )
                return True
            else:
                missing = []
                if not has_name:
                    missing.append("imię")
                if not has_job:
                    missing.append("zawód")
                if not has_city:
                    missing.append("miasto")

                self.log_test_result(
                    "Multi-turn Memory",
                    False,
                    f"AI nie pamiętał niektórych informacji: {', '.join(missing)}",
                    f"Odpowiedź: {ai_response3}",
                )
                return False

        except Exception as e:
            logger.error(f"Error in multi-turn memory test: {e}")
            self.log_test_result("Multi-turn Memory", False, f"Test error: {str(e)}")
            return False

    async def test_memory_persistence(self) -> bool:
        """Test trwałości pamięci w bazie danych."""
        try:
            # Sprawdź historię w bazie danych
            history = await self.get_user_history()

            if not history:
                self.log_test_result(
                    "Memory Persistence", False, "Brak historii w bazie danych"
                )
                return False

            # Sprawdź czy ostatnie wiadomości są zapisane
            recent_messages = [msg["content"] for msg in history[-5:]]

            # Sprawdź czy zawierają nasze testowe dane
            found_pizza = any("margherita" in msg.lower() for msg in recent_messages)
            found_name = any("jan kowalski" in msg.lower() for msg in recent_messages)

            if found_pizza or found_name:
                self.log_test_result(
                    "Memory Persistence",
                    True,
                    f"Pamięć została zachowana w bazie danych ({len(history)} wpisów)",
                    f"Ostatnie wiadomości: {recent_messages[-2:]}",
                )
                return True
            else:
                self.log_test_result(
                    "Memory Persistence",
                    False,
                    "Testowe dane nie zostały znalezione w historii",
                    f"Ostatnie wiadomości: {recent_messages}",
                )
                return False

        except Exception as e:
            logger.error(f"Error in persistence test: {e}")
            self.log_test_result("Memory Persistence", False, f"Test error: {str(e)}")
            return False

    async def test_memory_function_calls(self) -> bool:
        """Test funkcji pamięci poprzez function calling."""
        try:
            # Test zapisu przez function calling
            query1 = "Zapamiętaj że moja ulubiona książka to 'Diuna' Franka Herberta"
            response1 = await self.send_ai_query(query1)

            if "error" in response1:
                return False

            await asyncio.sleep(2)

            # Test odczytu
            query2 = "Jaka jest moja ulubiona książka?"
            response2 = await self.send_ai_query(query2)

            if "error" in response2:
                return False

            ai_response2 = response2.get("ai_response", "")

            if "diuna" in ai_response2.lower() or "herbert" in ai_response2.lower():
                self.log_test_result(
                    "Memory Function Calls",
                    True,
                    "System pamięci przez function calling działa",
                    f"Odwołanie: {ai_response2}",
                )
                return True
            else:
                # Sprawdź czy są logi function calls
                function_calls = response1.get("function_calls", [])
                if function_calls:
                    self.log_test_result(
                        "Memory Function Calls",
                        False,
                        "Function calls wykonane ale odwołanie nie działa",
                        f"Calls: {function_calls}",
                    )
                else:
                    self.log_test_result(
                        "Memory Function Calls",
                        False,
                        "Brak function calls dla pamięci",
                        f"Response: {response1}",
                    )
                return False

        except Exception as e:
            logger.error(f"Error in function calls test: {e}")
            self.log_test_result(
                "Memory Function Calls", False, f"Test error: {str(e)}"
            )
            return False

    async def test_openai_api_integration(self) -> bool:
        """Test integracji z prawdziwym OpenAI API."""
        try:
            # Proste zapytanie które powinno działać z prawdziwym API
            query = "Napisz krótki wiersz o programowaniu (maksymalnie 4 linijki)"
            response = await self.send_ai_query(query)

            if "error" in response:
                error_msg = response["error"]
                if "401" in error_msg or "unauthorized" in error_msg.lower():
                    self.log_test_result(
                        "OpenAI API Integration",
                        False,
                        "Problem z autoryzacją OpenAI API",
                        f"Błąd: {error_msg}",
                    )
                elif "429" in error_msg:
                    self.log_test_result(
                        "OpenAI API Integration",
                        False,
                        "Przekroczony limit OpenAI API",
                        f"Błąd: {error_msg}",
                    )
                else:
                    self.log_test_result(
                        "OpenAI API Integration", False, f"Błąd OpenAI API: {error_msg}"
                    )
                return False

            ai_response = response.get("ai_response", "")

            # Sprawdź czy odpowiedź jest sensowna
            if len(ai_response) > 20 and (
                "programowanie" in ai_response.lower()
                or "kod" in ai_response.lower()
                or "komputer" in ai_response.lower()
            ):
                self.log_test_result(
                    "OpenAI API Integration",
                    True,
                    "OpenAI API działa poprawnie",
                    f"Odpowiedź: {ai_response[:100]}...",
                )
                return True
            else:
                self.log_test_result(
                    "OpenAI API Integration",
                    False,
                    "Odpowiedź OpenAI wydaje się nieprawidłowa",
                    f"Odpowiedź: {ai_response}",
                )
                return False

        except Exception as e:
            logger.error(f"Error in OpenAI API test: {e}")
            self.log_test_result(
                "OpenAI API Integration", False, f"Test error: {str(e)}"
            )
            return False

    async def run_all_tests(self):
        """Uruchomienie wszystkich testów."""
        logger.info("🚀 Rozpoczynam kompleksowe testy pamięci i kontekstu GAJA")
        logger.info("=" * 60)

        tests = [
            ("1. OpenAI API Integration", self.test_openai_api_integration),
            ("2. Basic Memory Storage", self.test_basic_memory_storage),
            ("3. Conversation Context", self.test_conversation_context),
            ("4. Multi-turn Memory", self.test_multi_turn_memory),
            ("5. Memory Persistence", self.test_memory_persistence),
            ("6. Memory Function Calls", self.test_memory_function_calls),
        ]

        passed_tests = 0
        total_tests = len(tests)

        for test_name, test_func in tests:
            logger.info(f"\n🧪 Uruchamiam: {test_name}")
            try:
                result = await test_func()
                if result:
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd w teście {test_name}: {e}")
                self.log_test_result(test_name, False, f"Unexpected error: {str(e)}")

            # Krótka pauza między testami
            await asyncio.sleep(1)

        # Podsumowanie
        logger.info("\n" + "=" * 60)
        logger.info("📊 PODSUMOWANIE TESTÓW")
        logger.info("=" * 60)

        success_rate = (passed_tests / total_tests) * 100
        logger.info(
            f"Wyniki: {passed_tests}/{total_tests} testów przeszło pomyślnie ({success_rate:.1f}%)"
        )

        if passed_tests == total_tests:
            logger.info("🎉 Wszystkie testy przeszły pomyślnie!")
        elif passed_tests >= total_tests * 0.8:
            logger.info("✅ Większość testów przeszła pomyślnie - system stabilny")
        else:
            logger.info("⚠️  Wykryto problemy w systemie - wymagana uwaga")

        # Szczegółowe wyniki
        logger.info("\n📋 Szczegółowe wyniki:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            logger.info(f"{status} {result['test']}: {result['message']}")

        return passed_tests, total_tests


async def main():
    """Główna funkcja testowa."""
    tester = MemoryContextTester()

    try:
        await tester.setup()
        passed, total = await tester.run_all_tests()
        return passed == total
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

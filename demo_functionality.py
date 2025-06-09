#!/usr/bin/env python3
"""
GAJA Assistant - Comprehensive Functionality Demo
Demonstruje wszystkie zaimplementowane funkcje architektury klient-serwer.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add server path to Python path
sys.path.insert(0, str(Path(__file__).parent / "server"))

# Import server modules
from plugin_manager import PluginManager
from database_manager import get_database_manager
from ai_module import AIModule

logger = logging.getLogger(__name__)

class FunctionalityDemo:
    """Demonstrator funkcjonalności systemu GAJA."""
    
    def __init__(self):
        self.plugin_manager = None
        self.db_manager = None
        self.ai_module = None
        self.test_user_id = 1
        self.demo_results = []
    
    async def initialize(self):
        """Inicjalizuj komponenty systemu."""
        print("🚀 Inicjalizacja systemu GAJA...")
        
        # Initialize database
        self.db_manager = get_database_manager()
        await self.db_manager.initialize()
        print("✅ Baza danych zainicjalizowana")
        
        # Initialize plugin manager
        self.plugin_manager = PluginManager()
        discovered = await self.plugin_manager.discover_plugins()
        print(f"✅ Wykryto {len(discovered)} pluginów")
        
        # Load all plugins
        for plugin_name in discovered:
            success = await self.plugin_manager.load_plugin(plugin_name)
            if success:
                print(f"  • {plugin_name} załadowany")
                await self.plugin_manager.enable_plugin_for_user(plugin_name, self.test_user_id)
        
        # Initialize AI module
        self.ai_module = AIModule()
        await self.ai_module.initialize()
        print("✅ Moduł AI zainicjalizowany")
        
        print("🎯 System gotowy do demonstracji!")
    
    async def demo_plugin_system(self):
        """Demonstracja systemu pluginów."""
        print("\n🔌 === DEMONSTRACJA SYSTEMU PLUGINÓW ===")
        
        # List all available plugins
        plugins = await self.plugin_manager.list_available_plugins()
        print(f"📋 Dostępne pluginy ({len(plugins)}):")
        for plugin in plugins:
            functions = ", ".join(plugin.get('functions', []))
            print(f"  • {plugin['name']} - {functions}")
        
        # Test each plugin's core functionality
        test_cases = [
            {
                "plugin": "memory_module",
                "function": "save_memory",
                "params": {
                    "memory_type": "personal_info",
                    "key": "favorite_color",
                    "value": "niebieski",
                    "metadata": {"demo": True}
                },
                "description": "Zapisanie preferencji do pamięci"
            },
            {
                "plugin": "memory_module",
                "function": "get_memory",
                "params": {
                    "memory_type": "personal_info",
                    "key": "favorite_color"
                },
                "description": "Odczytanie preferencji z pamięci"
            },
            {
                "plugin": "weather_module",
                "function": "get_weather",
                "params": {
                    "location": "Warszawa",
                    "test_mode": True
                },
                "description": "Sprawdzenie pogody (tryb testowy)"
            },
            {
                "plugin": "search_module",
                "function": "search",
                "params": {
                    "query": "Python programming",
                    "max_results": 3,
                    "test_mode": True
                },
                "description": "Wyszukiwanie informacji (tryb testowy)"
            },
            {
                "plugin": "api_module",
                "function": "make_api_request",
                "params": {
                    "method": "GET",
                    "url": "https://httpbin.org/json",
                    "headers": {"User-Agent": "GAJA-Demo/1.0"}
                },
                "description": "Zapytanie do zewnętrznego API"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}/5: {test_case['description']}")
            
            try:
                result = await self.plugin_manager.call_plugin_function(
                    f"{test_case['plugin']}.{test_case['function']}",
                    test_case['params'],
                    self.test_user_id
                )
                
                if result.get('success', False):
                    print(f"✅ Sukces: {result.get('message', 'OK')}")
                    if 'data' in result and result['data']:
                        # Wyświetl fragment danych
                        data_str = str(result['data'])
                        if len(data_str) > 100:
                            data_str = data_str[:100] + "..."
                        print(f"   Dane: {data_str}")
                else:
                    print(f"❌ Błąd: {result.get('error', 'Unknown error')}")
                
                self.demo_results.append({
                    "test": test_case['description'],
                    "success": result.get('success', False),
                    "plugin": test_case['plugin'],
                    "function": test_case['function']
                })
                
            except Exception as e:
                print(f"❌ Wyjątek: {e}")
                self.demo_results.append({
                    "test": test_case['description'],
                    "success": False,
                    "error": str(e)
                })
            
            # Pauza między testami
            await asyncio.sleep(0.5)
    
    async def demo_ai_processing(self):
        """Demonstracja przetwarzania AI."""
        print("\n🤖 === DEMONSTRACJA PRZETWARZANIA AI ===")
        
        test_queries = [
            {
                "query": "Jaka jest pogoda w Krakowie?",
                "description": "Zapytanie o pogodę (powinno użyć weather plugin)"
            },
            {
                "query": "Zapamiętaj, że lubię kawę rano",
                "description": "Zapisanie informacji do pamięci"
            },
            {
                "query": "Co zapamiętałeś o moich preferencjach?",
                "description": "Odczytanie informacji z pamięci"
            },
            {
                "query": "Wyszukaj informacje o Python",
                "description": "Wyszukiwanie informacji"
            }
        ]
        
        for i, test_query in enumerate(test_queries, 1):
            print(f"\n🧠 Test AI {i}/4: {test_query['description']}")
            print(f"   Zapytanie: \"{test_query['query']}\"")
            
            try:
                # Symuluj context z klienta
                context = {
                    "user_id": self.test_user_id,
                    "input_method": "text",
                    "language": "pl",
                    "demo_mode": True
                }
                
                # Przetwórz przez AI
                response = await self.ai_module.process_query(
                    test_query['query'],
                    context
                )
                
                print(f"✅ Odpowiedź AI: {response[:200]}...")
                
                self.demo_results.append({
                    "test": f"AI: {test_query['description']}",
                    "success": True,
                    "query": test_query['query'],
                    "response_length": len(response)
                })
                
            except Exception as e:
                print(f"❌ Błąd AI: {e}")
                self.demo_results.append({
                    "test": f"AI: {test_query['description']}",
                    "success": False,
                    "error": str(e)
                })
            
            # Pauza między zapytaniami
            await asyncio.sleep(1)
    
    async def demo_database_operations(self):
        """Demonstracja operacji na bazie danych."""
        print("\n💾 === DEMONSTRACJA OPERACJI BAZODANOWYCH ===")
        
        try:
            # Test user operations
            print("👤 Testowanie operacji użytkownika...")
            user = await self.db_manager.get_user(self.test_user_id)
            if user:
                print(f"✅ Użytkownik {user['username']} istnieje")
            else:
                print("❌ Użytkownik nie istnieje")
            
            # Test plugin preferences
            print("\n🔧 Testowanie preferencji pluginów...")
            prefs = await self.db_manager.get_user_plugin_preferences(self.test_user_id)
            enabled_plugins = [p['plugin_name'] for p in prefs if p['enabled']]
            print(f"✅ Włączone pluginy: {', '.join(enabled_plugins)}")
            
            # Test message history
            print("\n📝 Testowanie historii wiadomości...")
            await self.db_manager.log_ai_interaction(
                user_id=self.test_user_id,
                query="Demo query",
                response="Demo response",
                tokens_used=10,
                provider="demo"
            )
            
            history = await self.db_manager.get_user_conversation_history(
                self.test_user_id, limit=5
            )
            print(f"✅ Historia zawiera {len(history)} wiadomości")
            
            # Test memory operations
            print("\n🧠 Testowanie operacji pamięci...")
            memory_count = await self.db_manager.save_memory(
                user_id=self.test_user_id,
                memory_type="demo",
                key="test_key",
                value="test_value",
                metadata={"demo": True}
            )
            print(f"✅ Zapisano wpis do pamięci (ID: {memory_count})")
            
            memory = await self.db_manager.get_memory(
                self.test_user_id, "demo", "test_key"
            )
            if memory:
                print(f"✅ Odczytano z pamięci: {memory['value']}")
            
            self.demo_results.append({
                "test": "Database operations",
                "success": True,
                "operations": ["user", "preferences", "history", "memory"]
            })
            
        except Exception as e:
            print(f"❌ Błąd bazy danych: {e}")
            self.demo_results.append({
                "test": "Database operations",
                "success": False,
                "error": str(e)
            })
    
    async def demo_performance_metrics(self):
        """Demonstracja metryk wydajności."""
        print("\n📊 === METRYKI WYDAJNOŚCI ===")
        
        try:
            # Test response times
            start_time = time.time()
            
            # Quick plugin test
            result = await self.plugin_manager.call_plugin_function(
                "weather_module.get_weather",
                {"location": "Test", "test_mode": True},
                self.test_user_id
            )
            
            plugin_time = time.time() - start_time
            print(f"⚡ Czas odpowiedzi pluginu: {plugin_time:.3f}s")
            
            # Database query test
            start_time = time.time()
            
            user = await self.db_manager.get_user(self.test_user_id)
            
            db_time = time.time() - start_time
            print(f"💾 Czas zapytania do bazy: {db_time:.3f}s")
            
            # Memory usage (approximation)
            import psutil
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # MB
            print(f"🧠 Użycie pamięci: {memory_usage:.1f} MB")
            
            print(f"🔧 Załadowane pluginy: {len(self.plugin_manager.loaded_plugins)}")
            print(f"👥 Aktywni użytkownicy: 1 (demo)")
            
        except Exception as e:
            print(f"⚠️ Błąd metryk: {e}")
    
    def print_summary(self):
        """Wyświetl podsumowanie demonstracji."""
        print("\n📋 === PODSUMOWANIE DEMONSTRACJI ===")
        
        total_tests = len(self.demo_results)
        successful_tests = len([r for r in self.demo_results if r.get('success', False)])
        
        print(f"🎯 Wykonano testów: {total_tests}")
        print(f"✅ Udanych: {successful_tests}")
        print(f"❌ Nieudanych: {total_tests - successful_tests}")
        
        if total_tests > 0:
            success_rate = (successful_tests / total_tests) * 100
            print(f"📈 Wskaźnik sukcesu: {success_rate:.1f}%")
        
        print("\n🏁 Demonstracja zakończona!")
        
        # Detailed results
        print("\n📝 Szczegółowe wyniki:")
        for i, result in enumerate(self.demo_results, 1):
            status = "✅" if result.get('success', False) else "❌"
            print(f"  {i:2d}. {status} {result['test']}")
            if not result.get('success', False) and 'error' in result:
                print(f"      Błąd: {result['error']}")
    
    async def run_full_demo(self):
        """Uruchom pełną demonstrację."""
        print("🎭 GAJA Assistant - Comprehensive Functionality Demo")
        print("=" * 60)
        
        await self.initialize()
        await self.demo_plugin_system()
        await self.demo_ai_processing()
        await self.demo_database_operations()
        await self.demo_performance_metrics()
        self.print_summary()


async def main():
    """Główna funkcja demonstracji."""
    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,  # Reduce log noise during demo
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run demo
    demo = FunctionalityDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Demonstracja przerwana przez użytkownika")
    except Exception as e:
        print(f"\n💥 Błąd demonstracji: {e}")

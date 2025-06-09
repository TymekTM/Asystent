import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import re
from collections import defaultdict

from database_manager import get_database_manager
from database_models import MemoryContext

logger = logging.getLogger(__name__)

# Required plugin functions
def get_functions() -> List[Dict[str, Any]]:
    """Zwraca listę dostępnych funkcji w pluginie."""
    return [
        {
            "name": "save_memory",
            "description": "Zapisuje informację do pamięci użytkownika",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_type": {
                        "type": "string",
                        "description": "Typ pamięci (personal_info, preferences, work_context, habits, goals, relationships, interests, conversation_context, long_term_memory, episodic_memory)"
                    },
                    "key": {
                        "type": "string",
                        "description": "Klucz/identyfikator informacji"
                    },
                    "value": {
                        "type": "string",
                        "description": "Wartość do zapamiętania"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Dodatkowe metadane"
                    }
                },
                "required": ["memory_type", "key", "value"]
            }
        },
        {
            "name": "get_memory",
            "description": "Pobiera informacje z pamięci użytkownika",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_type": {
                        "type": "string",
                        "description": "Typ pamięci"
                    },
                    "key": {
                        "type": "string",
                        "description": "Klucz/identyfikator informacji"
                    }
                },
                "required": ["memory_type", "key"]
            }
        },
        {
            "name": "search_memory",
            "description": "Wyszukuje informacje w pamięci użytkownika",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Zapytanie do wyszukania"
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Typ pamięci (opcjonalne)"
                    }
                },
                "required": ["query"]
            }
        }
    ]

async def execute_function(function_name: str, parameters: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Wykonuje funkcję pluginu."""
    memory_module = MemoryModule()
    
    try:
        if function_name == "save_memory":
            # Support both 'content' and 'value' for backward compatibility
            memory_type = parameters.get("memory_type", "general")  # Default type
            key = parameters.get("key")
            value = parameters.get("value") or parameters.get("content")  # Support both
            metadata = parameters.get("metadata", {})
            
            if not key or not value:
                return {
                    "success": False,
                    "error": "Brak wymaganych parametrów: key i value/content"
                }
            
            success = memory_module.save_memory(user_id, memory_type, key, value, metadata)
            
            if success:
                return {
                    "success": True,
                    "message": f"Zapisano informację: {key}",
                    "data": {
                        "memory_type": memory_type,
                        "key": key
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Nie udało się zapisać informacji"
                }
                
        elif function_name == "get_memory":
            memory_type = parameters.get("memory_type", "general")  # Default type
            key = parameters.get("key")
            
            if not key:
                return {
                    "success": False,
                    "error": "Brak wymaganego parametru: key"
                }
            
            result = memory_module.get_memory(user_id, memory_type, key)
            
            if result:
                return {
                    "success": True,
                    "data": result,
                    "message": f"Pobrano informację: {key}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Nie znaleziono informacji: {key}"
                }
                
        elif function_name == "search_memory":
            query = parameters.get("query")
            memory_type = parameters.get("memory_type")
            
            results = memory_module.search_memory(user_id, query, memory_type)
            
            return {
                "success": True,
                "data": results,
                "message": f"Znaleziono {len(results)} wyników dla zapytania: {query}"
            }
            
        else:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}"
            }
            
    except Exception as e:
        logger.error(f"Error executing {function_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

class MemoryModule:
    """Zaawansowany system pamięci dla asystenta AI."""
    
    def __init__(self):
        self.db_manager = get_database_manager()
        self.memory_types = {
            'personal_info': 'Informacje osobiste użytkownika',
            'preferences': 'Preferencje i ustawienia',
            'work_context': 'Kontekst zawodowy i projekty',
            'habits': 'Nawyki i wzorce zachowań',
            'goals': 'Cele i plany',
            'relationships': 'Relacje i kontakty',
            'interests': 'Zainteresowania i hobby',
            'conversation_context': 'Kontekst bieżącej rozmowy',
            'long_term_memory': 'Długoterminowa pamięć',
            'episodic_memory': 'Pamięć epizodyczna (wydarzenia)'
        }
        
    def save_memory(self, user_id: int, memory_type: str, key: str, 
                   value: str, metadata: Dict[str, Any] = None,
                   expires_at: datetime = None) -> bool:
        """
        Zapisuje informację do pamięci.
        
        Args:
            user_id: ID użytkownika
            memory_type: Typ pamięci
            key: Klucz/identyfikator
            value: Wartość do zapamiętania
            metadata: Dodatkowe metadane
            expires_at: Data wygaśnięcia (opcjonalne)
            
        Returns:
            True jeśli zapisano pomyślnie
        """
        try:
            self.db_manager.save_memory_context(
                user_id=user_id,
                context_type=memory_type,
                key_name=key,
                value=value,
                metadata=metadata or {},
                expires_at=expires_at
            )
            
            logger.info(f"Saved memory for user {user_id}: {memory_type}.{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False
    
    def get_memory(self, user_id: int, memory_type: str, 
                  key: str = None) -> List[MemoryContext]:
        """
        Pobiera informacje z pamięci.
        
        Args:
            user_id: ID użytkownika
            memory_type: Typ pamięci
            key: Konkretny klucz (opcjonalne)
            
        Returns:
            Lista kontekstów pamięci
        """
        try:
            return self.db_manager.get_memory_context(
                user_id=user_id,
                context_type=memory_type,
                key_name=key
            )
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return []
    
    def get_all_user_memory(self, user_id: int) -> Dict[str, List[MemoryContext]]:
        """
        Pobiera całą pamięć użytkownika pogrupowaną po typach.
        
        Args:
            user_id: ID użytkownika
            
        Returns:
            Słownik z pamięcią pogrupowaną po typach
        """
        memory_data = defaultdict(list)
        
        for memory_type in self.memory_types.keys():
            contexts = self.get_memory(user_id, memory_type)
            if contexts:
                memory_data[memory_type] = contexts
        
        return dict(memory_data)
    
    def analyze_and_extract_memory(self, user_id: int, message: str,
                                  conversation_context: List[str] = None) -> List[Dict[str, Any]]:
        """
        Analizuje wiadomość i wyciąga informacje do zapamiętania.
        
        Args:
            user_id: ID użytkownika
            message: Wiadomość do analizy
            conversation_context: Kontekst rozmowy
            
        Returns:
            Lista informacji do zapamiętania
        """
        extracted_memories = []
        
        # Analiza wzorców w tekście
        patterns = {
            'preferences': [
                r'lubię|kocham|preferuję|wolę|nie lubię|nienawidzę',
                r'mój ulubiony|moja ulubiona|moje ulubione'
            ],
            'personal_info': [
                r'nazywam się|jestem|mam na imię|mam|jestem z',
                r'pracuję jako|jestem|zawód|firma|praca'
            ],
            'goals': [
                r'chcę|planuję|zamierzam|mój cel|marzę|dążę do',
                r'w przyszłości|za rok|planuje|cel'
            ],
            'habits': [
                r'zwykle|zazwyczaj|często|codziennie|regularnie',
                r'mam w zwyczaju|zawsze|nigdy nie'
            ],
            'interests': [
                r'interesuję się|fascynuje mnie|hobby|pasja',
                r'lubię czytać|lubię grać|lubię oglądać'
            ]
        }
        
        # Szukaj wzorców w wiadomości
        message_lower = message.lower()
        
        for memory_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, message_lower)
                for match in matches:
                    # Wyciągnij kontekst wokół dopasowania
                    start = max(0, match.start() - 50)
                    end = min(len(message), match.end() + 100)
                    context = message[start:end].strip()
                    
                    extracted_memories.append({
                        'type': memory_type,
                        'key': f"auto_extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        'value': context,
                        'confidence': 0.7,
                        'source': 'pattern_analysis',
                        'timestamp': datetime.now().isoformat()
                    })
        
        # Analiza nazwisk, miejsc, dat
        name_pattern = r'\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*\b'
        names = re.findall(name_pattern, message)
        
        for name in names:
            if len(name.split()) >= 2:  # Prawdopodobnie imię i nazwisko
                extracted_memories.append({
                    'type': 'relationships',
                    'key': f"person_{name.replace(' ', '_').lower()}",
                    'value': f"Osoba: {name}",
                    'confidence': 0.6,
                    'source': 'name_extraction',
                    'timestamp': datetime.now().isoformat()
                })
        
        # Analiza dat
        date_patterns = [
            r'\d{1,2}[./]\d{1,2}[./]\d{2,4}',
            r'\d{1,2}\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+\d{2,4}'
        ]
        
        for pattern in date_patterns:
            dates = re.findall(pattern, message, re.IGNORECASE)
            for date in dates:
                extracted_memories.append({
                    'type': 'episodic_memory',
                    'key': f"date_{date.replace('/', '_').replace('.', '_').replace(' ', '_')}",
                    'value': f"Ważna data: {date}",
                    'confidence': 0.8,
                    'source': 'date_extraction',
                    'timestamp': datetime.now().isoformat()
                })
        
        return extracted_memories
    
    def save_extracted_memories(self, user_id: int, 
                               extracted_memories: List[Dict[str, Any]],
                               confidence_threshold: float = 0.6):
        """
        Zapisuje wyciągnięte wspomnienia jeśli przekraczają próg pewności.
        
        Args:
            user_id: ID użytkownika
            extracted_memories: Lista wyciągniętych wspomnień
            confidence_threshold: Minimalny próg pewności
        """
        saved_count = 0
        
        for memory in extracted_memories:
            if memory.get('confidence', 0) >= confidence_threshold:
                metadata = {
                    'confidence': memory.get('confidence'),
                    'source': memory.get('source'),
                    'extraction_timestamp': memory.get('timestamp')
                }
                
                success = self.save_memory(
                    user_id=user_id,
                    memory_type=memory['type'],
                    key=memory['key'],
                    value=memory['value'],
                    metadata=metadata
                )
                
                if success:
                    saved_count += 1
        
        logger.info(f"Saved {saved_count} extracted memories for user {user_id}")
        return saved_count
    
    def get_relevant_context(self, user_id: int, query: str,
                           max_contexts: int = 10) -> List[MemoryContext]:
        """
        Pobiera konteksty pamięci relevantne dla zapytania.
        
        Args:
            user_id: ID użytkownika
            query: Zapytanie użytkownika
            max_contexts: Maksymalna liczba kontekstów
            
        Returns:
            Lista relevantnych kontekstów
        """
        all_memory = self.get_all_user_memory(user_id)
        relevant_contexts = []
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Przeszukaj wszystkie konteksty
        for memory_type, contexts in all_memory.items():
            for context in contexts:
                # Oblicz relevancję na podstawie wspólnych słów
                context_words = set(context.value.lower().split())
                common_words = query_words.intersection(context_words)
                
                if common_words:
                    relevance_score = len(common_words) / len(query_words.union(context_words))
                    
                    relevant_contexts.append({
                        'context': context,
                        'relevance': relevance_score,
                        'common_words': common_words
                    })
        
        # Sortuj po relevancji i zwróć najlepsze
        relevant_contexts.sort(key=lambda x: x['relevance'], reverse=True)
        return [item['context'] for item in relevant_contexts[:max_contexts]]
    
    def update_conversation_context(self, user_id: int, user_message: str,
                                  assistant_response: str):
        """
        Aktualizuje kontekst bieżącej rozmowy.
        
        Args:
            user_id: ID użytkownika
            user_message: Wiadomość użytkownika
            assistant_response: Odpowiedź asystenta
        """
        conversation_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_message': user_message,
            'assistant_response': assistant_response
        }
        
        # Zapisz jako JSON
        self.save_memory(
            user_id=user_id,
            memory_type='conversation_context',
            key=f"turn_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            value=json.dumps(conversation_entry, ensure_ascii=False),
            expires_at=datetime.now() + timedelta(hours=24)  # Wygasa po 24h
        )
    
    def get_conversation_summary(self, user_id: int, hours: int = 24) -> str:
        """
        Tworzy podsumowanie ostatnich rozmów.
        
        Args:
            user_id: ID użytkownika
            hours: Liczba godzin wstecz
            
        Returns:
            Podsumowanie rozmów
        """
        contexts = self.get_memory(user_id, 'conversation_context')
        
        # Filtruj ostatnie rozmowy
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_contexts = [
            ctx for ctx in contexts 
            if ctx.created_at >= cutoff_time
        ]
        
        if not recent_contexts:
            return "Brak ostatnich rozmów do podsumowania."
        
        # Twórz podsumowanie
        summary_parts = []
        for ctx in recent_contexts[-10:]:  # Ostatnie 10 wymian
            try:
                conversation_data = json.loads(ctx.value)
                user_msg = conversation_data.get('user_message', '')[:100]
                summary_parts.append(f"Użytkownik: {user_msg}...")
            except json.JSONDecodeError:
                continue
        
        return "Ostatnie tematy rozmów:\n" + "\n".join(summary_parts)
    
    def cleanup_expired_memory(self, user_id: int = None):
        """
        Czyści wygasłą pamięć.
        
        Args:
            user_id: ID użytkownika (opcjonalne, jeśli None to dla wszystkich)
        """
        try:
            self.db_manager.cleanup_expired_memory()
            logger.info("Cleaned up expired memory entries")
        except Exception as e:
            logger.error(f"Error cleaning up memory: {e}")
    
    def get_memory_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Pobiera statystyki pamięci użytkownika.
        
        Args:
            user_id: ID użytkownika
            
        Returns:
            Statystyki pamięci
        """
        all_memory = self.get_all_user_memory(user_id)
        
        stats = {
            'total_entries': 0,
            'by_type': {},
            'oldest_entry': None,
            'newest_entry': None,
            'total_size_chars': 0
        }
        
        all_contexts = []
        for memory_type, contexts in all_memory.items():
            stats['by_type'][memory_type] = len(contexts)
            stats['total_entries'] += len(contexts)
            all_contexts.extend(contexts)
        
        if all_contexts:
            # Znajdź najstarszy i najnowszy wpis
            sorted_contexts = sorted(all_contexts, key=lambda x: x.created_at)
            stats['oldest_entry'] = sorted_contexts[0].created_at.isoformat()
            stats['newest_entry'] = sorted_contexts[-1].created_at.isoformat()
            
            # Oblicz całkowity rozmiar
            stats['total_size_chars'] = sum(len(ctx.value) for ctx in all_contexts)
        
        return stats
    
    def search_memory(self, user_id: int, search_term: str,
                     memory_types: List[str] = None) -> List[Tuple[MemoryContext, float]]:
        """
        Przeszukuje pamięć użytkownika.
        
        Args:
            user_id: ID użytkownika
            search_term: Termin wyszukiwania
            memory_types: Lista typów pamięci do przeszukania
            
        Returns:
            Lista tupli (kontekst, score)
        """
        if memory_types is None:
            memory_types = list(self.memory_types.keys())
        
        search_results = []
        search_lower = search_term.lower()
        
        for memory_type in memory_types:
            contexts = self.get_memory(user_id, memory_type)
            
            for context in contexts:
                # Proste wyszukiwanie pełnotekstowe
                value_lower = context.value.lower()
                
                if search_lower in value_lower:
                    # Oblicz score na podstawie pozycji i długości
                    position = value_lower.find(search_lower)
                    score = 1.0 - (position / len(value_lower))
                    
                    search_results.append((context, score))
        
        # Sortuj po score
        search_results.sort(key=lambda x: x[1], reverse=True)
        return search_results
    
    def export_user_memory(self, user_id: int) -> Dict[str, Any]:
        """
        Eksportuje całą pamięć użytkownika do struktury JSON.
        
        Args:
            user_id: ID użytkownika
            
        Returns:
            Eksport pamięci
        """
        all_memory = self.get_all_user_memory(user_id)
        
        export_data = {
            'user_id': user_id,
            'export_timestamp': datetime.now().isoformat(),
            'memory_types': {},
            'stats': self.get_memory_stats(user_id)
        }
        
        for memory_type, contexts in all_memory.items():
            export_data['memory_types'][memory_type] = [
                {
                    'key': ctx.key_name,
                    'value': ctx.value,
                    'metadata': ctx.metadata,
                    'created_at': ctx.created_at.isoformat(),
                    'updated_at': ctx.updated_at.isoformat()
                }
                for ctx in contexts
            ]
        
        return export_data


# Globalna instancja
_memory_module = None

def get_memory_module() -> MemoryModule:
    """Pobiera globalną instancję modułu pamięci."""
    global _memory_module
    if _memory_module is None:
        _memory_module = MemoryModule()
    return _memory_module

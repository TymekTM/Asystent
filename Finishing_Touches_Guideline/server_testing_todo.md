🧪 Testy serwera Gai – pełna checklista
🌐 1. API i komunikacja z klientem
Serwer przyjmuje zapytania (POST /query, /tts, itd.)

Obsługuje nagłe rozłączenia lub błędne żądania (HTTP 4xx / 5xx)

Czas odpowiedzi średnio <2s przy GPT i <0.5s przy pluginach

Odpowiedzi są w formacie JSON { text, intent, source, metadata }

Obsługa wielu klientów jednocześnie bez błędów (test 3–5 naraz)

Logi każdego zapytania trafiają do systemu logowania

🧠 2. Parser intencji
Intencje są poprawnie klasyfikowane

Nieznane intencje trafiają do fallbacka (LLM)

Obsługa niejednoznacznych zapytań (np. „zrób coś”)

Obsługa różnych języków (min. PL + EN)

Prawidłowy fallback do domyślnego modelu, jeśli nie rozpoznano

🔁 3. Routing zapytań
Zapytanie trafia do właściwego pluginu (np. pogoda, notatki)

Działa przełączanie między pluginami a fallbackiem

Przejście intencji → akcja → odpowiedź przebiega bez błędów

Działa ręczne wymuszanie źródła odpowiedzi (do debugów)

🧩 4. Pluginy
Każdy plugin działa i zwraca odpowiedź w <500ms (lokalnie)

Pluginy nie crashują przy błędnych danych wejściowych

Pluginy mają timeout (np. max 3s)

Logowanie błędów pluginów (nie crash całego systemu)

Rejestrowanie nazw, ID użytkownika i czasu użycia

🧠 5. Pamięć (memory manager)
Short-term memory trzyma dane ok. 15–20 minut

Mid-term memory trzyma dane dzienne (reset po północy lub ręcznie)

Long-term memory zapisuje do bazy (SQLite) i odczytuje przy starcie

Wspomnienia są oznaczane jako ważne (logika działa)

Fallback do „brak pamięci” nie crashuje odpowiedzi

Logika zarządzania pamięcią działa (FIFO, TTL itd.)

📚 6. Nauka nawyków
System zapisuje powtarzalne zapytania i pory dnia

Potrafi zasugerować automatyczne akcje

Zachowania są logowane (czas + treść + intencja)

Możliwość włączenia/wyłączenia tej funkcji globalnie

Brak nadpisywania unikalnych sesji przez inne

🧠 7. Model AI / LLM fallback
Działa gpt-4.1-nano jako domyślny backend

Lokalne modele tymczasowo wyłączone – fallback działa?

Obsługa błędów API (rate limit, 401, brak połączenia)

Odpowiedź fallbacka zawiera meta-info (że to fallback)

Token limit i retry policy działają poprawnie

📦 8. Logika sesji i użytkowników
Każdy użytkownik ma odrębną sesję (UUID / token)

Dane nie mieszają się między użytkownikami

Serwer potrafi trzymać kilka aktywnych użytkowników naraz

Można przełączać użytkownika (symulacja z klienta)

🧪 9. Stabilność i odporność
Serwer nie crashuje przy dużej ilości zapytań (np. 50 w 10s)

Obsługa restartu – dane się nie gubią, pamięć działa dalej

System działa stabilnie >1h pod obciążeniem (symulacja CLI / curl)

Brak wycieków pamięci (do sprawdzenia przez htop / docker stats)

🧰 10. Dev tools / debug
Wszystkie błędy są logowane z tracebackiem

Możliwość logowania intent, plugin, latency, user_id

Tryb verbose/dev możliwy do uruchomienia z flagą

Endpoint testowy /ping i /debug odpowiada

💳 11. Dostępy i limity (free vs. paid)
Serwer poprawnie rozróżnia użytkowników darmowych i płatnych (np. po tokenie, ID lub nagłówku)

Nałożone są limity dla użytkowników darmowych:

Maks. liczba zapytań/miesięcnie (np. 500)

Ograniczenie do wybranych pluginów / brak LLM

Użytkownicy płatni mają dostęp do pełnych funkcji

Ratelimity zwracają sensowne odpowiedzi (np. HTTP 429 + komunikat)

Serwer nie wywala błędu aplikacji przy przekroczeniu limitu

Obsługa użytkowników w limicie/reset po czasie działa (np. sliding window)

Możliwość przetestowania przez X-Debug: force-limit lub inny test flag

🧪 Scenariusze testowe dla serwera (rozszerzone)
Zapytanie o pogodę 10x od różnych użytkowników naraz

Losowe pytania (niepasujące do żadnej intencji)

Brak odpowiedzi z pluginu → fallback do LLM

Przerywane zapytania HTTP (np. curl --max-time 1)

Test działania na 2 urządzeniach naraz (multiclient)

Zmiana ID użytkownika w trakcie działania

Odpowiedź z pluginu + zapis wspomnienia + natychmiastowe użycie tej wiedzy

🧪 Scenariusze specjalne – darmowy vs płatny
Użytkownik darmowy wysyła 15 zapytań w 60s → powinien dostać 429 Too Many Requests

Użytkownik płatny wykonuje tę samą liczbę zapytań → brak błędów

Użytkownik darmowy prosi o coś obsługiwanego tylko przez plugin premium → dostaje komunikat odmowy

Użytkownik płatny korzysta z tych samych funkcji → działa

Użytkownik darmowy dostaje skrócone odpowiedzi z LLM (test: max 150 tokenów)

Użytkownik darmowy wykonuje zapytania do LLM, ale fallback jest wyłączony → system powinien zasugerować upgrade lub zwrócić komunikat

Zmiana konta z darmowego na płatne w czasie jednej sesji → nowy zakres uprawnień jest respektowany bez restartu

Przeciążenie jednego użytkownika nie wpływa na innego (izolacja sesji i limitów)

🧪 Testy klienta Gai – pełna checklista
🎙️ 1. Wejście głosowe (ASR)
Mikrofon działa i nagrywa bez lagów

Transkrypcja Whisperem lokalnie (sprawdź różne języki)

Obsługa ciszy (timeout, brak odpowiedzi)

Obsługa błędów (np. brak dostępu do mikrofonu)

💬 2. Obsługa tekstu (alternatywny input)
Możliwość wpisania tekstu zamiast mówienia

Obsługa enter/submit klawiszem

Działa przy wyłączonym mikrofonie

🔄 3. Przesyłanie danych do serwera
JSON z intencją trafia do serwera

ID użytkownika przekazywane poprawnie

Serwer odpowiada w czasie <2s (średnio)

Obsługa przerwania połączenia lub błędów HTTP

🧠 4. Odbiór odpowiedzi (serwer → klient)
Klient poprawnie odbiera tekst odpowiedzi

Obsługa fallbacków (np. gdy plugin nie odpowiada)

Obsługa długich odpowiedzi (>200 znaków)

Obsługa błędów formatu (np. brak pola text)

🔊 5. Synteza mowy (TTS)
Odpowiedź jest czytana natychmiast po odebraniu

Streamowanie działa (nie czeka na cały tekst)

Brak błędów z plikami tymczasowymi

Możliwość przerwania lub anulowania wypowiedzi

Obsługa błędu TTS (np. API padło → fallback na tekst)

🧩 6. Overlay (rollbackowa wersja)
Wyświetla tekst użytkownika i odpowiedź

Nie crashuje przy pustej odpowiedzi

Skaluje się na różnych rozdzielczościach

Czytelność i kontrast – test noc/dzień

Responsywność – nie blokuje innych elementów

👤 7. Sesja użytkownika
ID sesji generowane i utrzymywane

Obsługa wielu instancji klienta (różni użytkownicy)

Zmiana użytkownika powoduje zmianę historii / kontekstu

💾 8. Pamięć klienta (jeśli ma cache/context)
Poprawnie przechowuje dane tymczasowe (short term)

Reset kontekstu działa

Nie przecieka pamięć – test 100 interakcji

⚠️ 9. Fallbacki i edge case'y
Brak odpowiedzi z serwera → pokazanie komunikatu

Błąd TTS → wyświetlenie tekstu

Błąd transkrypcji → info „nie zrozumiałem”

Błąd sieci → ponowna próba lub informacja dla użytkownika

🧪 10. Scenariusze testowe (kombinacje)
Krótkie pytania (np. „która godzina?”)

Długie pytania („czy możesz podsumować mi dzień?”)

Pytania nietypowe („czy znasz Ricka?”)

Przerywanie TTS kolejnym pytaniem

Test: 3 użytkowników w tym samym czasie

Test: klient działa przez >1h i nie crashuje

🧰 Narzędzia pomocnicze do testów
log_viewer: do podglądu, czy klient wysyła/odbiera poprawnie

dev_mode: opcja debugowania z surowymi odpowiedziami

test_user.json: symulacja różnych profili użytkowników

network_monitor: do testów błędów sieci

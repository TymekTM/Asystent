# ✅ FIXY

- When AI wants to activate listening and user does the same time it just happens twice
- Moduł od muzyki klucz spotify

# ⭐ WAŻNE (strategiczne / fundamenty)

- Plug and play installation
- Listen after finished speaking (jako funkcja dla ai)
- Test poorman and richman mode
- Dostosowywanie tts w zależności od pory dnia i "święta"
- Clean up main catalog
- Nie ma opcji ustawić mikrofon oraz wyjście audio w klient
- overlay się nie wyświetla
- daily briefing przy każdym uruchomieniu aplikacji
- przetestować cały system
- Rebuid overlay

# 🔧 OPTYMALIZACJE

# 🟢 ŁATWE (mały scope, max 1 dzień)

- Wheel decide do robienia czego
- Build-in system notatek UI kompatybilnych z Obsidian

# 🟡 ŚREDNIE (2–4 dni, integracja kilku rzeczy)

- Instalator z GUI
- API integrations: weather, calendar, IoT – MCP
- Desktop/mobile version (Tauri)
  czy

# 🔴 TRUDNE (większe systemy, AI/ML, duży zakres)

- TTS and voice personalization (głos, język, szybkość, test)
- Wykrywanie rozmówcy za pomocą speechbrain
- RAG (retrieval-augmented generation)

Najważniejsze rzeczy do poprawy / dodać
Priorytet Temat Co się dzieje / co poprawić
🔴 Brak Dockerfile + docker-compose Serwer ma zależności (SQLite, pliki audio, modele). Wrzuć Dockerfile (oparty na python:3.12-slim) i plik docker-compose.yml z usługą db oraz opcjonalnie klientem. Ułatwi CI i deploy.
🟠 CI / lint Nie widzę .github/workflows. Dodaj job: lint (ruff/black) + mypy + pytest. Wykryje sporo drobnych błędów zanim przejdą dalej.
🟡 Struktura repo Masz sporo plików w root (mode_integrator.py, overlay/, web_ui/). Rozważ podział: gaja_core/, gaja_server/, gaja_client/. Łatwiej będzie budować wheel/installer.
🟡 Pliki audio i modele Wymagasz pip-install „dużych” paczek (faster-whisper, piper). Rozważ lazy-download przy pierwszym uruchomieniu + progres bar (masz pseudo-mechanizm w requirements_build, ale warto dorobić)
🟡 Dokumentacja API FastAPI generuje swagger, ale fajnie byłoby dodać krótki diagram sekwencji (np. w README) jak klient ↔ serwer ↔ AI provider ↔ plugin przebiega przy pojedynczej komendzie.

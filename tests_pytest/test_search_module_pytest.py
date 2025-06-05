import pytest
from unittest.mock import patch, MagicMock, ANY, AsyncMock
import asyncio
import time
from modules.search_module import (
    search_handler,
    normalize_query,
    _search_cache,
    CACHE_TTL,
    SEARCH_SUMMARY_PROMPT,
    DuckDuckGoSearchException,
    is_similar,
    random_headers,
    USER_AGENTS,
    extract_text,
    SearchCache,
    MAIN_MODEL # Import MAIN_MODEL for assertions
)
# from audio_modules.beep_sounds import play_beep, stop_beep # Not directly used
# from ai_module import chat_with_providers # Keep this commented or remove if not directly used in test setup

# ──────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────

@pytest.fixture
def mock_play_beep():
    with patch('modules.search_module.play_beep', new_callable=MagicMock) as mock:
        yield mock

@pytest.fixture
def mock_stop_beep():
    with patch('modules.search_module.stop_beep', new_callable=MagicMock) as mock:
        yield mock

@pytest.fixture
def mock_chat_with_providers():
    # Changed: Set a default return_value on the AsyncMock directly.
    # Tests can override this by setting mock_chat_with_providers.return_value in the test body.
    mock = AsyncMock(return_value={"message": {"content": "Default Mocked AI summary."}})
    with patch('modules.search_module.chat_with_providers', new=mock) as patched_mock:
        yield patched_mock

@pytest.fixture
def mock_search_duckduckgo():
    with patch('modules.search_module._search_duckduckgo', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_fetch_page(): # This fixture might not be used if _fetch_pages_concurrently is always used
    with patch('modules.search_module._fetch_page', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_fetch_pages_concurrently():
    with patch('modules.search_module._fetch_pages_concurrently', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
def mock_fallback_search():
    with patch('modules.search_module._fallback_search', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture(autouse=True)
def clear_search_cache_before_each_test():
    _search_cache.clear()
    yield
    _search_cache.clear()

# ──────────────────────────────────────────
#  Tests (Unchanged basic tests)
# ──────────────────────────────────────────
@pytest.mark.parametrize("input,expected", [
    ("Hello, World!", "hello world"),
    ("TEST? query.", "test query"),
])
def test_normalize_query(input, expected):
    assert normalize_query(input) == expected


def test_normalize_query_removes_punctuation_and_lower():
    assert normalize_query("Hello, World!") == "hello world"
    assert normalize_query("Test--Test") == "testtest"


def test_is_similar_true():
    q1 = "this is a test"
    q2 = "this is test"
    assert is_similar(q1, q2)


def test_is_similar_true_and_false():
    assert is_similar("one two three", "three two one")
    assert not is_similar("", "test")
    assert not is_similar("a b", "c d")


def test_is_similar_false():
    assert not is_similar("a b c", "x y z")


def test_random_headers_structure():
    hdr = random_headers()
    assert isinstance(hdr, dict)
    assert 'User-Agent' in hdr and 'Accept' in hdr
    assert hdr['User-Agent'] in USER_AGENTS


def test_random_headers_keys_and_values():
    headers = random_headers()
    assert isinstance(headers, dict)
    assert 'User-Agent' in headers
    assert 'Accept' in headers


def test_extract_text():
    html = '<html><body><p>First</p><p>Second</p></body></html>'
    txt = extract_text(html)
    assert 'First' in txt and 'Second' in txt


def test_extract_text_paragraphs():
    html = "<html><body><p>First</p><p>Second</p><p>Third</p></body></html>"
    assert extract_text(html) == "First Second Third"


def test_search_cache_put_get_and_evict():
    cache = SearchCache(maxlen=2)
    now = time.time()
    cache.put('a', (now, 'param', 'resA'))
    cache.put('b', (now, 'param', 'resB'))
    assert cache.get('a', now) == 'resA'
    cache.put('c', (now, 'param', 'resC'))
    assert cache.get('b', now) == 'resB'
    assert cache.get('a', now) is None

# ──────────────────────────────────────────
#  Refactored search_handler Tests
# ──────────────────────────────────────────

@pytest.mark.anyio
async def test_search_handler_empty_query(mock_play_beep, mock_stop_beep):
    result = await search_handler("")
    assert result == "Podaj zapytanie wyszukiwania."
    mock_play_beep.assert_not_called()
    mock_stop_beep.assert_not_called()

@pytest.mark.anyio
async def test_search_handler_cached(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "cached test"
    normalized_query = normalize_query(query)
    cached_content = "CACHED_RESULT"
    _search_cache.put(normalized_query, (time.time(), query, cached_content))

    result = await search_handler(query)
    assert result == cached_content

    mock_play_beep.assert_not_called()
    mock_stop_beep.assert_not_called()
    mock_search_duckduckgo.assert_not_called()
    mock_fetch_pages_concurrently.assert_not_called()
    mock_fallback_search.assert_not_called()
    mock_chat_with_providers.assert_not_called()

@pytest.mark.anyio
async def test_search_handler_no_results_async(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "query with no results"
    mock_search_duckduckgo.return_value = []
    mock_fallback_search.return_value = []
    # _fetch_pages_concurrently will not be called if both primary and fallback searches yield no URLs

    result = await search_handler(query)
    assert result == "Nie znaleziono wyników. Spróbuj przeformułować zapytanie lub sprawdź połączenie internetowe."

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalize_query(query))
    mock_fallback_search.assert_called_once_with(normalize_query(query))
    mock_fetch_pages_concurrently.assert_not_called() # Changed: Should not be called
    mock_chat_with_providers.assert_not_called()
    mock_stop_beep.assert_called_once()

@pytest.mark.anyio
async def test_search_handler_successful_search_and_summary(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "successful query"
    normalized_query = normalize_query(query)
    search_urls = ["http://example.com/page1", "http://example.com/page2"]
    fetched_content = "Page 1 content. Page 2 content."
    ai_summary = "AI summary of combined content."

    mock_search_duckduckgo.return_value = search_urls
    mock_fetch_pages_concurrently.return_value = fetched_content
    mock_chat_with_providers.return_value = {"message": {"content": ai_summary}} # Override default mock
    mock_fallback_search.return_value = []

    result = await search_handler(query)
    assert result == ai_summary

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalized_query)
    mock_fetch_pages_concurrently.assert_called_once_with(search_urls)
    mock_fallback_search.assert_not_called()

    expected_prompt_content = SEARCH_SUMMARY_PROMPT.format(query=query, text=fetched_content[:4500])
    mock_chat_with_providers.assert_called_once_with(
        model_name=MAIN_MODEL,
        messages=[{"role": "user", "content": expected_prompt_content}],
        user_id=None
    )
    mock_stop_beep.assert_called_once()
    assert _search_cache.get(normalized_query, time.time()) == ai_summary

@pytest.mark.anyio
async def test_search_handler_fallback_search_success(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "query for fallback"
    normalized_query = normalize_query(query)
    fallback_urls = ["http://fallback.com/fb_page1"]
    fallback_content = "Fallback page content."
    ai_summary_of_fallback = "AI summary of fallback content."

    mock_search_duckduckgo.return_value = [] # Primary search yields no URLs
    mock_fallback_search.return_value = fallback_urls
    # _fetch_pages_concurrently will only be called with fallback_urls in this scenario
    mock_fetch_pages_concurrently.return_value = fallback_content
    mock_chat_with_providers.return_value = {"message": {"content": ai_summary_of_fallback}}

    result = await search_handler(query)
    assert result == ai_summary_of_fallback

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalized_query)
    mock_fallback_search.assert_called_once_with(normalized_query)
    
    # _fetch_pages_concurrently called once with fallback_urls
    mock_fetch_pages_concurrently.assert_called_once_with(fallback_urls)

    expected_prompt_content = SEARCH_SUMMARY_PROMPT.format(query=query, text=fallback_content[:4500])
    mock_chat_with_providers.assert_called_once_with(
        model_name=MAIN_MODEL, 
        messages=[{"role": "user", "content": expected_prompt_content}],
        user_id=None
    )
    mock_stop_beep.assert_called_once()
    assert _search_cache.get(normalized_query, time.time()) == ai_summary_of_fallback

@pytest.mark.anyio
async def test_search_handler_duckduckgo_exception_rate_limit(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "trigger ddg ratelimit"
    mock_search_duckduckgo.side_effect = DuckDuckGoSearchException("Ratelimit exceeded")

    result = await search_handler(query)
    assert result == "Przepraszam, przekroczono limit zapytań do wyszukiwarki. Spróbuj ponownie za chwilę."

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalize_query(query))
    mock_fetch_pages_concurrently.assert_not_called()
    mock_fallback_search.assert_not_called() # Not called if DDG specific error handled by search_handler
    mock_chat_with_providers.assert_not_called()
    mock_stop_beep.assert_called_once()

@pytest.mark.anyio
async def test_search_handler_duckduckgo_general_exception(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "trigger general ddg error"
    mock_search_duckduckgo.side_effect = DuckDuckGoSearchException("Some other DDG error")
    # Fallback is NOT attempted by search_handler if _search_duckduckgo itself raises an exception
    # that is caught by search_handler's DuckDuckGoSearchException block.

    result = await search_handler(query)
    # Changed: Correct expected message
    assert result == "Przepraszam, napotkałem chwilowy problem z wyszukiwaniem. Spróbuj ponownie za kilka minut."

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalize_query(query))
    mock_fallback_search.assert_not_called() # Changed: Should not be called
    mock_fetch_pages_concurrently.assert_not_called() # Changed: Should not be called
    mock_chat_with_providers.assert_not_called()
    mock_stop_beep.assert_called_once()

@pytest.mark.anyio
async def test_search_handler_fetch_pages_concurrently_exception(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "trigger fetch error"
    search_urls = ["http://example.com/page1"]
    mock_search_duckduckgo.return_value = search_urls
    mock_fetch_pages_concurrently.side_effect = Exception("Network error during fetch")
    # Fallback is NOT called if the exception in _fetch_pages_concurrently is a generic one caught by the main try-except.

    result = await search_handler(query)
    assert result == "Wystąpił nieoczekiwany błąd podczas wyszukiwania. Spróbuj ponownie później."

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalize_query(query))
    mock_fetch_pages_concurrently.assert_called_once_with(search_urls)
    mock_fallback_search.assert_not_called() # Fallback is not initiated if primary fetch fails with generic Exception
    mock_chat_with_providers.assert_not_called()
    mock_stop_beep.assert_called_once()

@pytest.mark.anyio
async def test_search_handler_chat_with_providers_returns_none(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "chat returns none"
    search_urls = ["http://example.com/page1"]
    fetched_content = "Some content."
    mock_search_duckduckgo.return_value = search_urls
    mock_fetch_pages_concurrently.return_value = fetched_content
    mock_chat_with_providers.return_value = None # Override default mock to return None
    mock_fallback_search.return_value = []

    result = await search_handler(query)
    assert result == "Błąd podczas generowania podsumowania. Spróbuj ponownie później."

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalize_query(query))
    mock_fetch_pages_concurrently.assert_called_once_with(search_urls)
    mock_fallback_search.assert_not_called()
    expected_prompt_content = SEARCH_SUMMARY_PROMPT.format(query=query, text=fetched_content[:4500])
    mock_chat_with_providers.assert_called_once_with(
        model_name=MAIN_MODEL,
        messages=[{"role": "user", "content": expected_prompt_content}],
        user_id=None
    )
    mock_stop_beep.assert_called_once()

@pytest.mark.anyio
async def test_search_handler_expired_cache_then_fresh_search(
    mock_play_beep, mock_stop_beep, mock_chat_with_providers,
    mock_search_duckduckgo, mock_fetch_pages_concurrently, mock_fallback_search
):
    query = "expired cache then fresh"
    normalized_query = normalize_query(query)
    expired_time = time.time() - CACHE_TTL - 60
    _search_cache.put(normalized_query, (expired_time, query, "EXPIRED_CACHED_RESULT"))

    fresh_search_urls = ["http://fresh.com/page"]
    fresh_fetched_content = "Fresh page content."
    fresh_ai_summary = "AI summary of fresh content."

    mock_search_duckduckgo.return_value = fresh_search_urls
    mock_fetch_pages_concurrently.return_value = fresh_fetched_content
    mock_chat_with_providers.return_value = {"message": {"content": fresh_ai_summary}}
    mock_fallback_search.return_value = []

    result = await search_handler(query)
    assert result == fresh_ai_summary
    assert result != "EXPIRED_CACHED_RESULT"

    mock_play_beep.assert_called_once_with("search", True)
    mock_search_duckduckgo.assert_called_once_with(normalized_query)
    mock_fetch_pages_concurrently.assert_called_once_with(fresh_search_urls)
    mock_fallback_search.assert_not_called()
    expected_prompt_content = SEARCH_SUMMARY_PROMPT.format(query=query, text=fresh_fetched_content[:4500])
    mock_chat_with_providers.assert_called_once_with(
        model_name=MAIN_MODEL,
        messages=[{"role": "user", "content": expected_prompt_content}],
        user_id=None
    )
    mock_stop_beep.assert_called_once()
    assert _search_cache.get(normalized_query, time.time()) == fresh_ai_summary

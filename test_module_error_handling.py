import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from collections import deque
from assistant import Assistant

class TestModuleErrorHandling:
    """Test cases for module error detection and AI fallback retry."""
    
    @pytest.fixture
    def assistant(self):
        """Create an Assistant instance for testing."""
        with patch('assistant.load_config'), \
             patch('assistant.TTSModule'), \
             patch('assistant.WhisperASR'), \
             patch('assistant.get_active_window_title'):
            assistant = Assistant()
            assistant.conversation_history = deque(maxlen=10)
            return assistant
    
    def test_is_module_error_response_detects_polish_errors(self, assistant):
        """Test if Polish error messages are detected correctly."""
        error_responses = [
            "Błąd podczas pobierania danych",
            "Przepraszam, wystąpił błąd",
            "Nie udało się wykonać operacji",
            "Błąd połączenia z API"
        ]
        
        for error_response in error_responses:
            assert assistant.is_module_error_response(error_response) == True
    
    def test_is_module_error_response_detects_english_errors(self, assistant):
        """Test if English error messages are detected correctly."""
        error_responses = [
            "Error occurred while processing",
            "API error: connection timeout",
            "Failed to retrieve data",
            "Exception in module execution"
        ]
        
        for error_response in error_responses:
            assert assistant.is_module_error_response(error_response) == True
    
    def test_is_module_error_response_ignores_success_responses(self, assistant):
        """Test if successful responses are not detected as errors."""
        success_responses = [
            "Operacja wykonana pomyślnie",
            "Dane zostały pobrane",
            "Successfully completed task",
            "Here are your search results",
            "Weather forecast: sunny"
        ]
        
        for success_response in success_responses:
            assert assistant.is_module_error_response(success_response) == False
    
    def test_is_module_error_response_handles_edge_cases(self, assistant):
        """Test edge cases for error detection."""
        edge_cases = [
            None,
            "",
            123,  # Non-string input
            [],   # Non-string input
        ]
        
        for edge_case in edge_cases:
            assert assistant.is_module_error_response(edge_case) == False
    
    @pytest.mark.asyncio
    async def test_retry_with_ai_fallback_calls_generate_response(self, assistant):
        """Test if AI fallback correctly calls generate_response without tools."""
        original_query = "What's the weather?"
        error_response = "Błąd API pogody"
        
        with patch('assistant.generate_response', return_value='{"text": "I cannot check the weather right now, but I can help you with other tasks."}') as mock_generate, \
             patch('assistant.parse_response', return_value={"text": "I cannot check the weather right now, but I can help you with other tasks."}) as mock_parse, \
             patch('assistant.detect_language', return_value="en") as mock_detect, \
             patch.object(assistant, 'speak_and_maybe_listen', new_callable=AsyncMock) as mock_speak:
            
            await assistant.retry_with_ai_fallback(original_query, error_response, TextMode=True)
            
            # Verify generate_response was called with empty tools_info
            mock_generate.assert_called_once()
            args, kwargs = mock_generate.call_args
            assert kwargs.get('tools_info') == ""  # No tools should be provided
            
            # Verify speak_and_maybe_listen was called with AI response
            mock_speak.assert_called_once()
            spoken_text = mock_speak.call_args[0][0]
            assert "I cannot check the weather right now" in spoken_text
    
    @pytest.mark.asyncio
    async def test_retry_with_ai_fallback_handles_exceptions(self, assistant):
        """Test if AI fallback handles exceptions gracefully."""
        original_query = "Test query"
        error_response = "Module error"
        
        with patch('assistant.generate_response', side_effect=Exception("AI error")) as mock_generate, \
             patch.object(assistant, 'speak_and_maybe_listen', new_callable=AsyncMock) as mock_speak:
            
            await assistant.retry_with_ai_fallback(original_query, error_response, TextMode=True)
            
            # Verify fallback error message was spoken
            mock_speak.assert_called_once()
            spoken_text = mock_speak.call_args[0][0]
            assert "nieoczekiwany błąd" in spoken_text
    
    def test_error_detection_comprehensive_polish_terms(self, assistant):
        """Test comprehensive Polish error term detection."""
        polish_errors = [
            "Błąd w systemie",
            "BŁĄD KRYTYCZNY",
            "błąd połączenia",
            "Przepraszam za błąd",
            "przepraszam, nie mogę",
            "Wystąpił błąd podczas",
            "wystąpił nieoczekiwany błąd",
            "Nie udało się połączyć",
            "nie udało się wykonać"
        ]
        
        for error_text in polish_errors:
            assert assistant.is_module_error_response(error_text) == True, f"Failed to detect error in: {error_text}"
    
    def test_error_detection_comprehensive_english_terms(self, assistant):
        """Test comprehensive English error term detection."""
        english_errors = [
            "Error in processing",
            "ERROR: Invalid request",
            "error occurred",
            "Failed to connect",
            "FAILED operation",
            "failed to retrieve",
            "Exception caught",
            "EXCEPTION in module",
            "exception during execution",
            "Timeout error",
            "TIMEOUT occurred",
            "timeout while waiting",
            "Connection error",
            "CONNECTION FAILED",
            "connection timeout",
            "API error response",
            "API ERROR occurred",
            "api error: invalid key",
            "Invalid response format",
            "INVALID RESPONSE",
            "invalid response received"
        ]
        
        for error_text in english_errors:
            assert assistant.is_module_error_response(error_text) == True, f"Failed to detect error in: {error_text}"

if __name__ == "__main__":
    pytest.main([__file__])

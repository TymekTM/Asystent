import json
import re
import os
import importlib
import requests
import logging # Add logging import
import langid # Add import for langid
from typing import Dict, Any, Optional, Tuple
from config import STT_MODEL, MAIN_MODEL, PROVIDER, _config, DEEP_MODEL # Added DEEP_MODEL
from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT, DETECT_LANGUAGE_PROMPT # Added DETECT_LANGUAGE_PROMPT

logger = logging.getLogger(__name__) # Add logger instance

class AIProviders:
    def __init__(self):
        self.providers = {
            "ollama": {
                "module": None,
                "check": self.check_ollama,
                "chat": self.chat_ollama
            },
            "lmstudio": {
                "check": self.check_lmstudio,
                "chat": self.chat_lmstudio
            },
            "openai": {
                "module": None,
                "check": self.check_openai,
                "chat": self.chat_openai
            },
            "deepseek": {
                "module": None,
                "check": self.check_deepseek,
                "chat": self.chat_deepseek
            },
            "anthropic": {
                "module": None,
                "check": self.check_anthropic,
                "chat": self.chat_anthropic
            },
            "transformer": {
                "check": lambda: True,
                "chat": self.chat_transformer
            }
        }
        self.initialize_providers()

    def initialize_providers(self):
        try:
            self.providers["ollama"]["module"] = importlib.import_module("ollama")
        except ImportError:
            pass
        try:
            self.providers["openai"]["module"] = importlib.import_module("openai")
        except ImportError:
            pass
        try:
            self.providers["deepseek"]["module"] = importlib.import_module("deepseek")
        except ImportError:
            pass
        try:
            self.providers["anthropic"]["module"] = importlib.import_module("anthropic")
        except ImportError:
            pass

    # Metody diagnostyczne
    def check_ollama(self) -> bool:
        try:
            return requests.get("http://localhost:11434", timeout=5).status_code == 200
        except:
            return False

    def check_lmstudio(self) -> bool:
        url = "http://localhost:1234/v1/models"
        logger.debug(f"Checking LM Studio endpoint: {url}")
        try:
            response = requests.get(url, timeout=5)
            logger.debug(f"LM Studio check response status: {response.status_code}")
            return response.status_code == 200
        except requests.exceptions.ConnectionError as e:
            logger.error(f"LM Studio check failed: Connection error - {e}")
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"LM Studio check failed: Timeout - {e}")
            return False
        except Exception as e:
            logger.error(f"LM Studio check failed: Unexpected error - {e}")
            return False

    def check_openai(self) -> bool:
        return "OPENAI_API_KEY" in os.environ or (_config.get("API_KEYS", {}).get("OPENAI_API_KEY") and _config.get("API_KEYS", {}).get("OPENAI_API_KEY") != "YOUR_OPENAI_API_KEY_HERE")

    def check_deepseek(self) -> bool:
        return "DEEPSEEK_API_KEY" in os.environ or (_config.get("API_KEYS", {}).get("DEEPSEEK_API_KEY") and _config.get("API_KEYS", {}).get("DEEPSEEK_API_KEY") != "YOUR_DEEPSEEK_API_KEY_HERE")

    def check_anthropic(self) -> bool:
        return "ANTHROPIC_API_KEY" in os.environ or (_config.get("API_KEYS", {}).get("ANTHROPIC_API_KEY") and _config.get("API_KEYS", {}).get("ANTHROPIC_API_KEY") != "YOUR_ANTHROPIC_API_KEY_HERE")

    # Implementacje z obsługą opcjonalnych zdjęć
    def chat_ollama(self, model: str, messages: list, images: list = None) -> Optional[Dict[str, Any]]:
        try:
            kwargs = {}
            if images is not None:
                # Jeśli dany provider obsługuje obrazy bezpośrednio, przekazujemy je
                kwargs["images"] = images
            response = self.providers["ollama"]["module"].chat(model=model, messages=messages, **kwargs)
            return {"message": {"content": response["message"]["content"]}}
        except Exception as e:
            print(f"Błąd Ollama: {e}")
            return None

    def chat_lmstudio(self, model: str, messages: list, images: list = None) -> Optional[Dict[str, Any]]:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
            }
            if images is not None:
                payload["images"] = images
            response = requests.post(
                "http://localhost:1234/v1/chat/completions",
                json=payload,
                timeout=30
            )
            data = response.json()
            if "choices" in data and data["choices"] and "message" in data["choices"][0] and "content" in data["choices"][0]["message"]:
                return {"message": {"content": data["choices"][0]["message"]["content"]}}
            else:
                print(f"Błąd LM Studio: nieprawidłowa odpowiedź: {data}")
                return {"message": {"content": "Błąd: nieprawidłowa odpowiedź z LM Studio"}}
        except Exception as e:
            print(f"Błąd LM Studio: {e}")
            return {"message": {"content": f"Błąd LM Studio: {e}"}}

    def chat_openai(self, model: str, messages: list, images: list = None) -> Optional[Dict[str, Any]]:
        # Chat via OpenAI provider
        try:
            api_key = os.getenv("OPENAI_API_KEY") or _config.get("API_KEYS", {}).get("OPENAI_API_KEY")
            if not api_key or api_key == "YOUR_OPENAI_API_KEY_HERE":
                logger.error("OpenAI API Key not configured or invalid.")
                return {"message": {"content": "Błąd OpenAI: Klucz API nie skonfigurowany."}}
            openai_module = self.providers["openai"]["module"]
            if not openai_module:
                logger.error("OpenAI module not available.")
                return {"message": {"content": "Błąd OpenAI: moduł openai nie zaimportowany."}}
            # Set API key
            openai_module.api_key = api_key
            # Optionally include images in prompt
            if images:
                images_info = "\n\nObrazy: " + ", ".join(images)
                messages[-1]["content"] += images_info
            # Call chat completion
            response = openai_module.chat.completions.create(
                model=model,
                messages=messages,
                temperature=_config.get("temperature", 0.7),
                max_tokens=_config.get("max_tokens", 150)
            )
            content = None
            # Extract content from response
            if hasattr(response, 'choices') and response.choices:
                msg = getattr(response.choices[0].message, 'content', None)
                content = msg or response.choices[0].message.content
            if not content:
                raise ValueError("No content in OpenAI response.")
            return {"message": {"content": content}}
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}", exc_info=True)
            return {"message": {"content": f"Błąd OpenAI: {e}"}}

    def chat_deepseek(self, model: str, messages: list, images: list = None) -> Optional[Dict[str, Any]]:
        try:
            api_key = os.getenv("DEEPSEEK_API_KEY") or _config.get("API_KEYS", {}).get("DEEPSEEK_API_KEY")
            if not api_key or api_key == "YOUR_DEEPSEEK_API_KEY_HERE":
                 print("DeepSeek API Key not configured.")
                 return None
            if images is not None:
                images_info = "\n\nObrazy: " + ", ".join(images)
                messages[-1]["content"] += images_info
            client = self.providers["deepseek"]["module"].Client(api_key=api_key)
            response = client.chat.completions.create(model=model, messages=messages)
            return {"message": {"content": response.choices[0].message.content}}
        except Exception as e:
            print(f"Błąd DeepSeek: {e}")
            return None

    def chat_anthropic(self, model: str, messages: list, images: list = None) -> Optional[Dict[str, Any]]:
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY") or _config.get("API_KEYS", {}).get("ANTHROPIC_API_KEY")
            if not api_key or api_key == "YOUR_ANTHROPIC_API_KEY_HERE":
                 print("Anthropic API Key not configured.")
                 return None
            anthropic_module = self.providers["anthropic"]["module"]
            if not anthropic_module:
                print("anthropic module not available.")
                return None
            client = anthropic_module.Anthropic(api_key=api_key)
            prompt = "\n\n".join(
                f"{anthropic_module.HUMAN_PROMPT if msg['role'] == 'user' else anthropic_module.AI_PROMPT} {msg['content']}"
                for msg in messages
            )
            if images is not None:
                prompt += "\n\nObrazy: " + ", ".join(images)
            response = client.completions.create(model=model, prompt=prompt, max_tokens_to_sample=1000)
            return {"message": {"content": response.completion}}
        except Exception as e:
            print(f"Błąd Anthropic: {e}")
            return None

    def chat_transformer(self, model: str, messages: list, images: list = None) -> Optional[Dict[str, Any]]:
        try:
            from transformers import pipeline
            if images is not None:
                images_info = "\n\nObrazy: " + ", ".join(images)
                messages[-1]["content"] += images_info
            generator = pipeline('text-generation', model=model)
            response = generator(messages[-1]["content"], max_length=512, do_sample=True)
            return {"message": {"content": response[0]["generated_text"]}}
        except Exception as e:
            print(f"Błąd Transformers: {e}")
            return None

ai_providers = AIProviders()

def health_check() -> Dict[str, bool]:
    return {provider: ai_providers.providers[provider]["check"]() for provider in ai_providers.providers}

def remove_chain_of_thought(text: str) -> str:
    pattern = r"<think>.*?</think>|<\|begin_of_thought\|>.*?<\|end_of_thought\|>|<\|begin_of_solution\|>.*?<\|end_of_solution\|>|<\|end\|>"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()

def extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) > 0 and lines[0].strip() == "```":
            lines = lines[1:]
        if len(lines) > 0 and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    match = re.search(r'({.*})', text, re.DOTALL)
    return match.group(1) if match else text

def chat_with_providers(model: str, messages: list, images: list = None, provider_override: str = None) -> Optional[Dict[str, Any]]:
    selected_provider = provider_override or PROVIDER.lower()
    provider_config = ai_providers.providers.get(selected_provider)

    provider_check_result = False
    if provider_config:
        logger.debug(f"Checking configured provider: {selected_provider}")
        provider_check_result = provider_config["check"]()
        logger.debug(f"Check result for {selected_provider}: {provider_check_result}")
    else:
        logger.warning(f"Configured provider '{selected_provider}' not found in provider list.")

    if provider_check_result:
        logger.info(f"Attempting to use configured provider: {selected_provider}")
        response = provider_config["chat"](model, messages, images)
        if response:
            return response
        else:
            logger.warning(f"Configured provider {selected_provider} failed during chat. Trying fallbacks.")
    else:
        logger.warning(f"Configured provider {selected_provider} check failed or provider not found. Trying fallbacks.")

    # Fallback logic
    for provider_name, provider in ai_providers.providers.items():
        if provider_name == selected_provider:
            continue # Skip the one that already failed or wasn't configured

        fallback_check_result = False
        logger.debug(f"Checking fallback provider: {provider_name}")
        try:
             fallback_check_result = provider["check"]()
             logger.debug(f"Check result for fallback {provider_name}: {fallback_check_result}")
        except Exception as e:
             logger.error(f"Error checking fallback provider {provider_name}: {e}")

        if fallback_check_result:
            logger.info(f"Trying fallback provider: {provider_name}")
            response = provider["chat"](model, messages, images)
            if response:
                logger.info(f"Fallback provider {provider_name} succeeded.")
                return response
            else:
                 logger.warning(f"Fallback provider {provider_name} failed during chat.")
        # else: # Optional: Log if fallback check failed
        #    logger.debug(f"Skipping fallback provider {provider_name} due to failed check.")

    # If all providers fail
    logger.error("All providers failed.")
    return {"message": {"content": '{"command": "", "params": "", "text": "Błąd: Żaden dostawca nie odpowiada"}'}}

# --- New Function: Language Detection ---
def detect_language(text: str) -> Tuple[str, float, str]:
    """Detects the language of the input text using langid, with heuristics and fallback."""
    try:
        text = text.strip()
        # Heuristic: If text is too short, fallback
        if len(text) < 4:
            logger.info("Text too short for reliable language detection. Fallback to Polish.")
            return "pl", 1.0, "Detected language: pl\nRespond in Polish to all user inputs unless explicitly asked otherwise."
        lang_code, confidence = langid.classify(text)
        # Heuristic: If confidence is very low, fallback
        if confidence < 0.7:
            # Check for Polish diacritics or common words
            polish_chars = set("ąćęłńóśźż")
            if any(c in text for c in polish_chars) or any(w in text.lower() for w in ["jest", "czy", "jak", "co", "się", "nie", "tak"]):
                lang_code, confidence = "pl", 0.8
            else:
                logger.info(f"Low confidence ({confidence:.2f}) for langid result '{lang_code}'. Fallback to Polish.")
                lang_code, confidence = "pl", confidence
        lang_map = {
            "en": "English",
            "pl": "Polish",
            "de": "German",
            "es": "Spanish",
            "fr": "French",
            "it": "Italian",
            "ru": "Russian",
            "sv": "Swedish",
        }
        lang_name = lang_map.get(lang_code, lang_code)
        prompt_text = (
            f"Detected language: {lang_code}\nRespond in {lang_name} to all user inputs unless explicitly asked otherwise."
        )
        return lang_code, confidence, prompt_text
    except Exception as e:
        logger.error(f"Language detection failed: {e}", exc_info=True)
        return "pl", 0.0, "Detected language: pl\nRespond in Polish to all user inputs unless explicitly asked otherwise."

# --- Improved Refiner: lock language, prevent translation ---
def refine_query(query: str, detected_language: str = "Polish") -> str:
    """Refines the user query using the AI provider, focusing on transcription correction, never translation."""
    try:
        # Add language lock to the prompt
        language_lock = f"The user's language is {detected_language}. DO NOT translate, rephrase, or change the language. Only correct transcription errors."
        prompt = language_lock + "\n" + CONVERT_QUERY_PROMPT
        response = chat_with_providers(
            model=MAIN_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ]
        )
        if response and response.get("message", {}).get("content"):
            refined = response["message"]["content"].strip()
            return refined if refined else query
        else:
            logger.warning("Query refinement failed: No response from AI. Returning original query.")
            return query
    except Exception as e:
        logger.error(f"Query refinement failed: {e}. Returning original query.", exc_info=True)
        return query

# Change generate_response to accept optional system prompt override
def generate_response(conversation_history: list, functions_info: str, system_prompt_override: str = None) -> str:
    """Generates the main AI response based on history and available functions. Always returns JSON string."""
    try:
        # Use overridden system prompt if provided, else default
        current_system_prompt = (system_prompt_override if system_prompt_override else SYSTEM_PROMPT)
        current_system_prompt += f"\n\nAvailable tools: {functions_info}"
        messages_for_api = list(conversation_history)
        if messages_for_api and messages_for_api[0]["role"] == "system":
            messages_for_api[0]["content"] = current_system_prompt
        else:
            messages_for_api.insert(0, {"role": "system", "content": current_system_prompt})

        response = chat_with_providers(MAIN_MODEL, messages_for_api)
        ai_content = response["message"]["content"].strip() if response and response.get("message", {}).get("content") else None
        if ai_content:
            # Try to parse as JSON, ensure response has required structure
            try:
                parsed = json.loads(extract_json(ai_content))
                if isinstance(parsed, dict) and "text" in parsed:
                    # Ensure all keys are present
                    return json.dumps({
                        "text": parsed.get("text", ""),
                        "command": parsed.get("command", ""),
                        "params": parsed.get("params", {})
                    }, ensure_ascii=False)
                if isinstance(parsed, str):
                    # Wrap string into required structure
                    return json.dumps({
                        "text": parsed,
                        "command": "",
                        "params": {}
                    }, ensure_ascii=False)
            except Exception:
                # Not valid JSON, wrap as text with default fields
                return json.dumps({
                    "text": ai_content,
                    "command": "",
                    "params": {}
                }, ensure_ascii=False)
        # No content from AI, return error in required structure
        logger.error("Response generation failed: No content from AI.")
        return json.dumps({
            "text": "Przepraszam, nie udało mi się wygenerować odpowiedzi.",
            "command": "",
            "params": {}
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Response generation failed: {e}", exc_info=True)
        return json.dumps({
            "text": "Przepraszam, wystąpił błąd podczas generowania odpowiedzi.",
            "command": "",
            "params": {}
        }, ensure_ascii=False)

def parse_response(response_text: str) -> dict:
    try:
        parsed = json.loads(extract_json(response_text))
        # Ensure all required keys exist
        if isinstance(parsed, dict):
            return {
                "text": parsed.get("text", ""),
                "command": parsed.get("command", ""),
                "params": parsed.get("params", {})
            }
        # If parsed is a string, wrap into dict
        if isinstance(parsed, str):
            return {"text": parsed, "command": "", "params": {}}
        # Unexpected type, return error
        return {"text": "Nieprawidłowa odpowiedź AI", "command": "", "params": {}}
    except Exception:
        return {"text": "Nieprawidłowa odpowiedź AI", "command": "", "params": {}}

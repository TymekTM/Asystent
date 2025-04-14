import json
import re
import os
import importlib
import requests
import logging # Add logging import
from typing import Dict, Any, Optional
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
                # Jeśli provider nie obsługuje osobnego parametru obrazów, możesz spróbować dołączyć je do wiadomości
                payload["images"] = images
                # Alternatywnie:
                # images_info = "\n\nObrazy: " + ", ".join(images)
                # messages[-1]["content"] += images_info
            response = requests.post(
                "http://localhost:1234/v1/chat/completions",
                json=payload,
                timeout=30
            )
            return {"message": {"content": response.json()["choices"][0]["message"]["content"]}}
        except Exception as e:
            print(f"Błąd LM Studio: {e}")
            return None

    def chat_openai(self, model: str, messages: list, images: list = None) -> Optional[Dict[str, Any]]:
        try:
            api_key = os.getenv("OPENAI_API_KEY") or _config.get("API_KEYS", {}).get("OPENAI_API_KEY")
            if not api_key or api_key == "YOUR_OPENAI_API_KEY_HERE":
                 print("OpenAI API Key not configured.")
                 return None
            # Ensure the openai library is initialized with the key if not using env var
            openai_module = self.providers["openai"]["module"]
            if openai_module and not os.getenv("OPENAI_API_KEY"):
                 openai_module.api_key = api_key

            if images is not None:
                images_info = "\n\nObrazy: " + ", ".join(images)
                messages[-1]["content"] += images_info
            response = openai_module.ChatCompletion.create(
                model=model,
                messages=messages
            )
            return {"message": {"content": response.choices[0].message.content}}
        except Exception as e:
            print(f"Błąd OpenAI: {e}")
            return None

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
def detect_language(text: str) -> str:
    """Detects the language of the input text using the main AI provider."""
    try:
        # Use a smaller/faster model if available and suitable, otherwise MAIN_MODEL
        # For simplicity, using MAIN_MODEL for now
        response = chat_with_providers(
            model=MAIN_MODEL, # Or a dedicated smaller model
            messages=[
                {"role": "system", "content": DETECT_LANGUAGE_PROMPT},
                {"role": "user", "content": text}
            ]
        )
        if response and response.get("message", {}).get("content"):
            lang = response["message"]["content"].strip().capitalize()
            # Basic validation
            if len(lang.split()) == 1 and lang != 'Unknown':
                return lang
            else:
                logger.warning(f"Language detection returned unexpected format: {lang}. Defaulting to Polish.")
                return "Polish" # Default fallback
        else:
            logger.error("Language detection failed: No response from AI.")
            return "Polish" # Default fallback
    except Exception as e:
        logger.error(f"Language detection failed: {e}", exc_info=True)
        return "Polish" # Default fallback on error

def refine_query(query: str, detected_language: str = "Polish") -> str:
    """Refines the user query using the AI provider, focusing on transcription correction."""
    try:
        # Pass language context if needed by the prompt/model, though current prompt doesn't explicitly use it
        response = chat_with_providers(
            model=MAIN_MODEL, # Or a model specifically fine-tuned for correction
            messages=[
                {"role": "system", "content": CONVERT_QUERY_PROMPT},
                {"role": "user", "content": query}
            ]
        )
        if response and response.get("message", {}).get("content"):
            refined = response["message"]["content"].strip()
            # Basic check: don't return empty string if original wasn't
            return refined if refined else query
        else:
            logger.warning("Query refinement failed: No response from AI. Returning original query.")
            return query
    except Exception as e:
        logger.error(f"Query refinement failed: {e}. Returning original query.", exc_info=True)
        return query

def generate_response(conversation_history: list, functions_info: str) -> str:
    """Generates the main AI response based on history and available functions."""
    try:
        # Add function info to the system prompt or a user message?
        # Let's add it to the system prompt context for this call.
        current_system_prompt = SYSTEM_PROMPT + f"\n\nAvailable tools: {functions_info}"

        messages_for_api = list(conversation_history) # Create a copy
        # Replace the original system prompt with the enhanced one if it exists
        if messages_for_api and messages_for_api[0]["role"] == "system":
            messages_for_api[0]["content"] = current_system_prompt
        else:
            messages_for_api.insert(0, {"role": "system", "content": current_system_prompt})

        response = chat_with_providers(MAIN_MODEL, messages_for_api)
        if response and response.get("message", {}).get("content"):
            return response["message"]["content"].strip()
        else:
            logger.error("Response generation failed: No content from AI.")
            return "Przepraszam, nie udało mi się wygenerować odpowiedzi."
    except Exception as e:
        logger.error(f"Response generation failed: {e}", exc_info=True)
        return "Przepraszam, wystąpił błąd podczas generowania odpowiedzi."

def parse_response(response_text: str) -> dict:
    try:
        return json.loads(extract_json(response_text))
    except json.JSONDecodeError:
        return {"error": "Nieprawidłowa odpowiedź AI"}

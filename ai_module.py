"""
ai_providers.py – ulepszona wersja
"""

from __future__ import annotations

import json
import os
import re
import importlib
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Callable
from collections import deque

import requests  # Added requests import
# Lazy import for transformers to speed up startup
pipeline = None

def _load_pipeline():
    global pipeline
    if pipeline is None:
        try:
            from transformers import pipeline as _pipeline
            pipeline = _pipeline
        except ImportError:
            pipeline = None
            logger.warning(
                "⚠️  transformers nie jest dostępny - będzie automatycznie doinstalowany przy pierwszym użyciu"
            )
    return pipeline

from config import STT_MODEL, MAIN_MODEL, PROVIDER, _config, DEEP_MODEL, load_config # Added load_config import
from prompt_builder import (
    build_convert_query_prompt,
    build_full_system_prompt,
)
from performance_monitor import measure_performance

# -----------------------------------------------------------------------------
# Konfiguracja logów
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# Klasa providerów
# -----------------------------------------------------------------------------
class AIProviders:
    """Rejestr wszystkich obsługiwanych dostawców + metody pomocnicze."""

    def __init__(self) -> None:
        # Własne HTTP session dla LM Studio (redukcja latency handshake)
        self._lmstudio_session = requests.Session()

        # Cached clients to avoid reinitialization overhead
        self._openai_client = None
        self._deepseek_client = None

        # Dynamiczny import modułów – brakujące biblioteki ≠ twardy crash
        self._modules: Dict[str, Any] = {
            mod: self._safe_import(mod) for mod in ("ollama", "openai", "anthropic")
        }

        self.providers: Dict[
            str, Dict[str, Callable[..., Any] | None]
        ] = {
            "ollama": {
                "module": self._modules["ollama"],
                "check": self.check_ollama,
                "chat": self.chat_ollama,
            },
            "lmstudio": {
                "module": None,  # REST‑only – klucz zostawiamy dla spójności
                "check": self.check_lmstudio,
                "chat": self.chat_lmstudio,
            },
            "openai": {
                "module": self._modules["openai"],
                "check": self.check_openai,
                "chat": self.chat_openai,
            },
            "deepseek": {
                "module": None,
                "check": self.check_deepseek,
                "chat": self.chat_deepseek,
            },
            "anthropic": {
                "module": self._modules["anthropic"],
                "check": self.check_anthropic,
                "chat": self.chat_anthropic,
            },
            "transformer": {
                "module": None,
                "check": lambda: True,
                "chat": self.chat_transformer,
            },
        }

    # ---------------------------------------------------------------------
    # Helpery
    # ---------------------------------------------------------------------
    @staticmethod
    def _safe_import(module_name: str) -> Optional[Any]:
        try:
            return importlib.import_module(module_name)
        except ImportError:
            logger.debug("Moduł %s nie został znaleziony – pomijam.", module_name)
            return None

    @staticmethod
    def _key_ok(env_var: str, cfg_key: str) -> bool:
        key = os.getenv(env_var) or _config.get("API_KEYS", {}).get(cfg_key)
        return bool(key and not key.startswith("YOUR_"))

    @staticmethod
    def _append_images(messages: List[dict], images: Optional[List[str]]) -> None:
        if images:
            messages[-1]["content"] += "\n\nObrazy: " + ", ".join(images)

    # ---------------------------------------------------------------------
    # Check‑i (zwracają bool, nic nie rzucają)
    # ---------------------------------------------------------------------
    def check_ollama(self) -> bool:
        try:
            return (
                requests.get("http://localhost:11434", timeout=5).status_code == 200
            )
        except requests.RequestException:
            return False

    def check_lmstudio(self) -> bool:
        try:
            url = _config.get("LMSTUDIO_URL", "http://localhost:1234/v1/models")
            return self._lmstudio_session.get(url, timeout=5).status_code == 200
        except requests.RequestException:
            return False

    def check_openai(self) -> bool:
        return self._key_ok("OPENAI_API_KEY", "OPENAI_API_KEY")

    def check_deepseek(self) -> bool:
        return self._key_ok("DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY")

    def check_anthropic(self) -> bool:
        return self._key_ok("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")

    # ---------------------------------------------------------------------
    # Chat‑y
    # ---------------------------------------------------------------------
    def chat_ollama(
        self,
        model: str,
        messages: List[dict],
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            self._append_images(messages, images)
            ollama_mod = self.providers["ollama"]["module"]
            resp = ollama_mod.chat(model=model, messages=messages)
            return {"message": {"content": resp["message"]["content"]}}
        except Exception as exc:  # pragma: no cover
            logger.error("Ollama error: %s", exc)
            return None

    def chat_lmstudio(
        self,
        model: str,
        messages: List[dict],
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature if temperature is not None else _config.get("temperature", 0.7),
            }
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens
            self._append_images(messages, images)
            url = _config.get(
                "LMSTUDIO_URL", "http://localhost:1234/v1/chat/completions"
            )
            r = self._lmstudio_session.post(url, json=payload, timeout=30)
            data = r.json()
            return {
                "message": {"content": data["choices"][0]["message"]["content"]}
            }
        except Exception as exc:
            logger.error("LM Studio error: %s", exc)
            return {
                "message": {"content": f"LM Studio error: {exc}"}
            }

    def chat_openai(
        self,
        model: str,
        messages: List[dict],
        images: Optional[List[str]] = None,
        functions: Optional[List[dict]] = None,
        function_calling_system=None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            api_key = os.getenv("OPENAI_API_KEY") or _config["API_KEYS"]["OPENAI_API_KEY"]
            if not api_key:
                raise ValueError("Brak OPENAI_API_KEY.")

            if self._openai_client is None:
                from openai import OpenAI  # type: ignore
                self._openai_client = OpenAI(api_key=api_key)

            client = self._openai_client
            self._append_images(messages, images)

            # Prepare parameters for OpenAI API call
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature if temperature is not None else _config.get("temperature", 0.7),
                "max_tokens": max_tokens if max_tokens is not None else _config.get("max_tokens", 1500),
            }
            
            # Add tools (functions) if provided
            if functions:
                params["tools"] = functions
                params["tool_choice"] = "auto"
            
            resp = client.chat.completions.create(**params)
            
            # Handle function calls
            if resp.choices[0].message.tool_calls:                # Execute function calls and collect results
                tool_results = []
                for tool_call in resp.choices[0].message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_calling_system:
                        result = function_calling_system.execute_function(
                            function_name, function_args, 
                            conversation_history=deque(messages[-10:]) if messages else None  # Pass recent conversation
                        )
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(result)
                        })
                
                # Add tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": resp.choices[0].message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function", 
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in resp.choices[0].message.tool_calls
                    ]
                })
                
                # Add tool results
                messages.extend(tool_results)
                
                # Get final response with tool results
                final_params = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature if temperature is not None else _config.get("temperature", 0.7),
                    "max_tokens": max_tokens if max_tokens is not None else _config.get("max_tokens", 1500),
                }
                
                final_resp = client.chat.completions.create(**final_params)
                return {
                    "message": {"content": final_resp.choices[0].message.content},
                    "tool_calls_executed": len(tool_results)
                }
            else:
                return {
                    "message": {"content": resp.choices[0].message.content}
                }
        except Exception as exc:
            logger.error("OpenAI error: %s", exc, exc_info=True)
            return {"message": {"content": f"Błąd OpenAI: {exc}"}}

    def chat_deepseek(
        self,
        model: str,
        messages: List[dict],
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            api_key = (
                os.getenv("DEEPSEEK_API_KEY")
                or _config["API_KEYS"]["DEEPSEEK_API_KEY"]
            )
            if not api_key:
                raise ValueError("Brak DEEPSEEK_API_KEY.")
            # DeepSeek jest w 100 % OpenAI‑compatible
            if self._deepseek_client is None:
                from openai import OpenAI  # type: ignore
                self._deepseek_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

            client = self._deepseek_client
            self._append_images(messages, images)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature if temperature is not None else _config.get("temperature", 0.7),
                max_tokens=max_tokens if max_tokens is not None else _config.get("max_tokens", 1500),
            )
            return {
                "message": {"content": resp.choices[0].message.content}
            }
        except Exception as exc:
            logger.error("DeepSeek error: %s", exc)
            return None

    def chat_anthropic(
        self,
        model: str,
        messages: List[dict],
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            api_key = (
                os.getenv("ANTHROPIC_API_KEY")
                or _config["API_KEYS"]["ANTHROPIC_API_KEY"]
            )
            if not api_key:
                raise ValueError("Brak ANTHROPIC_API_KEY.")
            from anthropic import Anthropic  # type: ignore

            client = Anthropic(api_key=api_key)
            self._append_images(messages, images)
            resp = client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens if max_tokens is not None else 1000,
                temperature=temperature if temperature is not None else _config.get("temperature", 0.7),
            )
            return {"message": {"content": resp.content[0].text}}
        except Exception as exc:
            logger.error("Anthropic error: %s", exc)
            return None

    def chat_transformer(
        self,
        model: str,
        messages: List[dict],
        images: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            self._append_images(messages, images)
            pl = _load_pipeline()
            if pl is None:
                return None
            generator = pl("text-generation", model=model)
            gen_kwargs = {"max_length": max_tokens or 512, "do_sample": True}
            if temperature is not None:
                gen_kwargs["temperature"] = temperature
            resp = generator(messages[-1]["content"], **gen_kwargs)
            return {"message": {"content": resp[0]["generated_text"]}}
        except Exception as exc:  # pragma: no cover
            logger.error("Transformers error: %s", exc)
            return None


_ai_providers: Optional[AIProviders] = None

def get_ai_providers() -> AIProviders:
    global _ai_providers
    if _ai_providers is None:
        _ai_providers = AIProviders()
    return _ai_providers

# -----------------------------------------------------------------------------
# Publiczne funkcje
# -----------------------------------------------------------------------------
@measure_performance
def health_check() -> Dict[str, bool]:
    providers = get_ai_providers()
    return {name: cfg["check"]() for name, cfg in providers.providers.items()}


# ------------------------------------------------------------------ utils ---


def remove_chain_of_thought(text: str) -> str:
    pattern = (
        r"<think>.*?</think>|<\|begin_of_thought\|>.*?<\|end_of_thought\|>|"
        r"<\|begin_of_solution\|>.*?<\|end_of_solution\|>|<\|end\|>"
    )
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def extract_json(text: str) -> str:
    """Zwraca pierwszy blok JSON z tekstu (albo cały string)."""
    text = text.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if ln.strip("`")]
        text = "\n".join(lines).strip()
    # Find all JSON-like blocks and choose the most complete one
    matches = re.findall(r"(\{.*\})", text, flags=re.DOTALL)
    if matches:
        # Return the largest match, assuming it's the full JSON object
        return max(matches, key=len)
    return text




# ---------------------------------------------------------------- refiner ----

@lru_cache(maxsize=256)
@measure_performance
def refine_query(query: str, detected_language: str = "Polish") -> str:
    try:
        prompt = build_convert_query_prompt(detected_language)
        resp = chat_with_providers(
            model=MAIN_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query},
            ],
        )
        return (
            resp["message"]["content"].strip()
            if resp and resp.get("message", {}).get("content")
            else query
        )
    except Exception as exc:  # pragma: no cover
        logger.error("refine_query error: %s", exc)
        return query


# ---------------------------------------------------------------- chat glue --


@measure_performance
def chat_with_providers(
    model: str,
    messages: List[dict],
    images: Optional[List[str]] = None,
    provider_override: Optional[str] = None,
    functions: Optional[List[dict]] = None,
    function_calling_system=None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    providers = get_ai_providers()
    selected = (provider_override or PROVIDER).lower()
    provider_cfg = providers.providers.get(selected)

    def _try(provider_name: str) -> Optional[Dict[str, Any]]:
        prov = providers.providers[provider_name]
        try:
            if prov["check"]():
                # Only pass functions to OpenAI provider for now
                if provider_name == "openai" and functions:
                    return prov["chat"](
                        model,
                        messages,
                        images,
                        functions,
                        function_calling_system,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                else:
                    return prov["chat"](
                        model,
                        messages,
                        images,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
        except Exception as exc:  # pragma: no cover
            logger.error("Provider %s failed: %s", provider_name, exc)
        return None

    # najpierw preferowany
    if provider_cfg:
        resp = _try(selected)
        if resp:
            return resp

    # fallback‑i
    for name in providers.providers:
        if name == selected:
            continue
        resp = _try(name)
        if resp:
            logger.info("Fallback provider %s zadziałał.", name)
            return resp

    # total failure
    logger.error("Wszyscy providerzy zawiedli.")
    error_payload = json.dumps(
        {
            "command": "",
            "params": {},
            "text": "Błąd: Żaden dostawca nie odpowiada",
        },
        ensure_ascii=False,
    )
    return {"message": {"content": error_payload}}


# ---------------------------------------------------------------- response ---


@measure_performance
def generate_response_logic(
    provider_name: str,
    model_name: str,
    messages: List[Dict[str, Any]],
    tools_info: str,
    system_prompt_override: Optional[str] = None,
    detected_language: Optional[str] = None,
    language_confidence: Optional[float] = None,
    images: Optional[List[str]] = None, # Added images
    active_window_title: Optional[str] = None, # Added
    track_active_window_setting: bool = False # Added
) -> str:
    """Core logic to generate a response from a chosen AI provider."""
    # Build the full system prompt
    # The first message in 'messages' is typically the system prompt.
    # We will replace it or prepend a new one if it doesn't exist.
    system_message_content = build_full_system_prompt(
        system_prompt_override=system_prompt_override,
        detected_language=detected_language,
        language_confidence=language_confidence,
        tools_description=tools_info,
        active_window_title=active_window_title, # Pass through
        track_active_window_setting=track_active_window_setting # Pass through
    )

    # Convert deque to list for slicing and modification
    messages_list = list(messages)
    if messages_list and messages_list[0]["role"] == "system":
        messages_list[0]["content"] = system_message_content
    else:
        messages_list.insert(0, {"role": "system", "content": system_message_content})

    # Send the modified messages to the AI provider
    response = chat_with_providers(
        model=model_name,
        messages=messages_list,
        images=images,  # Pass images to the provider
        provider_override=provider_name,  # Ensure the correct provider is used
    )

    # Extract and return the response content
    return (
        response["message"]["content"].strip()
        if response and response.get("message", {}).get("content")
        else ""
    )


@measure_performance
def generate_response(
    conversation_history: deque,
    tools_info: str = "",
    system_prompt_override: str = None,
    detected_language: str = "en",
    language_confidence: float = 1.0,
    active_window_title: str = None, 
    track_active_window_setting: bool = False,
    tool_suggestion: str = None,
    modules: Dict[str, Any] = None,
    use_function_calling: bool = True,
    user_name: str = None
) -> str:
    """
    Generates a response from the AI model based on conversation history and available tools.
    Can use either traditional prompt-based approach or OpenAI Function Calling.

    Args:
        conversation_history: A deque of previous messages.
        tools_info: A string describing available tools/plugins.
        system_prompt_override: An optional string to override the default system prompt.
        detected_language: The detected language code (e.g., "en", "pl").
        language_confidence: The confidence score for the detected language.
        active_window_title: The title of the currently active window.
        track_active_window_setting: Boolean indicating if active window tracking is enabled.
        modules: Dictionary of available modules for function calling.
        use_function_calling: Whether to use OpenAI Function Calling or traditional approach.

    Returns:
        A string containing the AI's response, potentially in JSON format for commands.
    """
    import datetime
    try:
        config = load_config() # Use imported load_config
        api_keys = config.get("API_KEYS", {}) # Get the nested API_KEYS dictionary
        api_key = api_keys.get("OPENAI_API_KEY") # Get the OpenAI API key from the nested dictionary
        model_name = config.get("OPENAI_MODEL", "gpt-4-turbo")

        if not api_key:
            logger.error("OpenAI API key not found in configuration.")
            return '{"text": "Błąd: Klucz API OpenAI nie został skonfigurowany.", "command": "", "params": {}}'
          # Initialize function calling system if enabled and modules provided
        function_calling_system = None
        functions = None
        
        if use_function_calling and modules and PROVIDER.lower() == "openai":
            from function_calling_system import convert_module_system_to_function_calling
            function_calling_system = convert_module_system_to_function_calling(modules)
            functions = function_calling_system.convert_modules_to_functions()
            logger.info(f"Function calling enabled with {len(functions)} functions")
              # Use standard system prompt for function calling
            system_prompt = build_full_system_prompt(
                system_prompt_override=system_prompt_override,
                detected_language=detected_language,
                language_confidence=language_confidence,
                tools_description="",  # Functions are handled separately
                active_window_title=active_window_title,
                track_active_window_setting=track_active_window_setting,
                tool_suggestion=tool_suggestion,
                user_name=user_name
            )
        else:            # Traditional prompt-based approach
            system_prompt = build_full_system_prompt(
                system_prompt_override=system_prompt_override,
                detected_language=detected_language,
                language_confidence=language_confidence,
                tools_description=tools_info,
                active_window_title=active_window_title,
                track_active_window_setting=track_active_window_setting,
                tool_suggestion=tool_suggestion,
                user_name=user_name
            )
        
        # --- PROMPT LOGGING ---
        try:
            import json
            timestamp = datetime.datetime.now().isoformat()
            
            with open("user_data/prompts_log.txt", "a", encoding="utf-8") as f:
                # Log the system prompt
                system_prompt_msg = {"role": "system", "content": system_prompt}
                f.write(f"{timestamp} | {json.dumps(system_prompt_msg, ensure_ascii=False)}\n")
                
                # Log conversation history
                for msg in list(conversation_history):
                    if msg.get("role") != "system":
                        f.write(f"{timestamp} | {json.dumps(msg, ensure_ascii=False)}\n")
                
                # Log available functions if using function calling
                if functions:
                    functions_msg = {"role": "system", "content": f"Available functions: {len(functions)}"}
                    f.write(f"{timestamp} | {json.dumps(functions_msg, ensure_ascii=False)}\n")
        except Exception as log_exc:
            logger.warning(f"[PromptLog] Failed to log prompt: {log_exc}")

        # Convert deque to list for slicing and modification
        messages = list(conversation_history)
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = system_prompt
        else:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Make API call with or without functions
        resp = chat_with_providers(
            MAIN_MODEL, 
            messages, 
            functions=functions,
            function_calling_system=function_calling_system
        )
        
        # --- RAW API RESPONSE LOGGING ---
        try:
            raw_content = resp.get("message", {}).get("content", "").strip() if resp else ""
            import json
            import datetime
            with open("user_data/prompts_log.txt", "a", encoding="utf-8") as f:
                raw_api_msg = {"role": "assistant_api_raw", "content": raw_content}
                f.write(f"{datetime.datetime.now().isoformat()} | {json.dumps(raw_api_msg, ensure_ascii=False)}\n")
                
                # Log if function calls were executed
                if resp and resp.get("tool_calls_executed"):
                    tool_calls_msg = {"role": "system", "content": f"Tool calls executed: {resp['tool_calls_executed']}"}
                    f.write(f"{datetime.datetime.now().isoformat()} | {json.dumps(tool_calls_msg, ensure_ascii=False)}\n")
        except Exception as log_exc:
            logger.warning(f"[RawAPI Log] Failed to log raw API response: {log_exc}")
        
        content = resp["message"]["content"].strip() if resp else ""
        if not content:
            raise ValueError("Empty response.")

        # If using function calling, return the content directly as it should be a natural response
        if use_function_calling and functions and resp.get("tool_calls_executed"):
            return json.dumps({
                "text": content,
                "command": "",
                "params": {},
                "function_calls_executed": True
            }, ensure_ascii=False)

        # Traditional JSON parsing for non-function calling responses
        parsed = extract_json(content)
        try:
            result = json.loads(parsed)
            if isinstance(result, dict) and "text" in result:
                return json.dumps(result, ensure_ascii=False)
        except Exception:
            pass

        # fallback: zawinąć surowy tekst
        return json.dumps({
            "text": content,
            "command": "",
            "params": {}
        }, ensure_ascii=False)
    except Exception as exc:  # pragma: no cover
        logger.error("generate_response error: %s", exc, exc_info=True)
        return json.dumps(
            {
                "text": "Przepraszam, wystąpił błąd podczas generowania odpowiedzi.",
                "command": "",
                "params": {},
            },
            ensure_ascii=False,
        )


@measure_performance
def parse_response(response_text: str) -> Dict[str, Any]:
    def try_parse(val):
        try:
            return json.loads(extract_json(val))
        except Exception:
            return val

    def ensure_dict(val):
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return {}

    try:
        parsed = try_parse(response_text)
        # Recursively parse if 'text' is a JSON string
        max_depth = 3
        depth = 0
        while isinstance(parsed, dict) and isinstance(parsed.get("text"), str):
            inner = parsed["text"].strip()
            # Heuristic: try to parse if it looks like JSON
            if (inner.startswith("{") and inner.endswith("}")) or (inner.startswith("\"") and inner.endswith("\"")):
                next_parsed = try_parse(inner)
                if isinstance(next_parsed, dict) and ("text" in next_parsed or "command" in next_parsed or "params" in next_parsed):
                    parsed = next_parsed
                    depth += 1
                    if depth >= max_depth:
                        break
                else:
                    break
            else:
                break
        if isinstance(parsed, dict):
            # Always ensure params is a dict
            params = parsed.get("params", {})
            params = ensure_dict(params)
            return {
                "text": parsed.get("text", ""),
                "command": parsed.get("command", ""),
                "params": params,
                "listen_after_tts": parsed.get("listen_after_tts", False) # ADDED
            }
        if isinstance(parsed, str):
            return {"text": parsed, "command": "", "params": {}, "listen_after_tts": False} # ADDED listen_after_tts
    except Exception as e: # pragma: no cover
        logger.error(f"Error parsing AI response: {response_text}, Error: {e}", exc_info=True) # Log the problematic response and error
        pass  # Fallthrough to default error response

    # Default error response or if parsing completely fails
    return {"text": "Nieprawidłowa odpowiedź AI", "command": "", "params": {}, "listen_after_tts": False} # ADDED listen_after_tts

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

import langid  # type: ignore
import requests  # type: ignore
from transformers import pipeline  # lazy‑loaded w chat_transformer

from config import STT_MODEL, MAIN_MODEL, PROVIDER, _config, DEEP_MODEL
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
        self, model: str, messages: List[dict], images: Optional[List[str]] = None
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
        self, model: str, messages: List[dict], images: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": _config.get("temperature", 0.7),
            }
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
        self, model: str, messages: List[dict], images: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            api_key = os.getenv("OPENAI_API_KEY") or _config["API_KEYS"]["OPENAI_API_KEY"]
            if not api_key:
                raise ValueError("Brak OPENAI_API_KEY.")
            # >= 1.0 klient
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key)
            self._append_images(messages, images)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=_config.get("temperature", 0.7),
                max_tokens=_config.get("max_tokens", 150),
            )
            return {
                "message": {"content": resp.choices[0].message.content}
            }
        except Exception as exc:
            logger.error("OpenAI error: %s", exc, exc_info=True)
            return {"message": {"content": f"Błąd OpenAI: {exc}"}}

    def chat_deepseek(
        self, model: str, messages: List[dict], images: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            api_key = (
                os.getenv("DEEPSEEK_API_KEY")
                or _config["API_KEYS"]["DEEPSEEK_API_KEY"]
            )
            if not api_key:
                raise ValueError("Brak DEEPSEEK_API_KEY.")
            # DeepSeek jest w 100 % OpenAI‑compatible
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            self._append_images(messages, images)
            resp = client.chat.completions.create(model=model, messages=messages)
            return {
                "message": {"content": resp.choices[0].message.content}
            }
        except Exception as exc:
            logger.error("DeepSeek error: %s", exc)
            return None

    def chat_anthropic(
        self, model: str, messages: List[dict], images: Optional[List[str]] = None
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
                max_tokens=1000,
            )
            return {"message": {"content": resp.content[0].text}}
        except Exception as exc:
            logger.error("Anthropic error: %s", exc)
            return None

    def chat_transformer(
        self, model: str, messages: List[dict], images: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            self._append_images(messages, images)
            generator = pipeline("text-generation", model=model)
            resp = generator(messages[-1]["content"], max_length=512, do_sample=True)
            return {"message": {"content": resp[0]["generated_text"]}}
        except Exception as exc:  # pragma: no cover
            logger.error("Transformers error: %s", exc)
            return None


# Jedna globalna instancja
ai_providers = AIProviders()

# -----------------------------------------------------------------------------
# Publiczne funkcje
# -----------------------------------------------------------------------------
@measure_performance
def health_check() -> Dict[str, bool]:
    return {
        name: cfg["check"]() for name, cfg in ai_providers.providers.items()
    }


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


# ---------------------------------------------------------------- language ---

@measure_performance
def detect_language(text: str) -> Tuple[str, float]: # Return type changed
    try:
        text = text.strip()
        if len(text) < 4:
            return "pl", 1.0 # Return only lang_code and confidence

        lang_code, conf = langid.classify(text)
        if conf < 0.7:
            # Heuristic for Polish if confidence is low but Polish characters are present
            if any(c in text for c in "ąćęłńóśźż"): # Polish specific characters
                lang_code, conf = "pl", 0.8 # Assume Polish with higher confidence
            else:
                # If no specific Polish chars and low confidence, default might be better or stick to 'pl' if it's common
                lang_code = "pl" # Or consider a more neutral default if 'pl' isn't always best guess

        # lang_name mapping is no longer needed here as we don't build the prompt string
        return lang_code, conf # Return only lang_code and confidence
    except Exception as exc:  # pragma: no cover
        logger.error("Language detection failed: %s", exc)
        return "pl", 0.0 # Default fallback


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
) -> Optional[Dict[str, Any]]:
    selected = (provider_override or PROVIDER).lower()
    provider_cfg = ai_providers.providers.get(selected)

    def _try(provider_name: str) -> Optional[Dict[str, Any]]:
        prov = ai_providers.providers[provider_name]
        try:
            if prov["check"]():
                return prov["chat"](model, messages, images)
        except Exception as exc:  # pragma: no cover
            logger.error("Provider %s failed: %s", provider_name, exc)
        return None

    # najpierw preferowany
    if provider_cfg:
        resp = _try(selected)
        if resp:
            return resp

    # fallback‑i
    for name in ai_providers.providers:
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
def generate_response(
    conversation_history: deque, # Update type hint to deque
    tools_info: str,
    system_prompt_override: Optional[str] = None,
    detected_language: Optional[str] = None, # Add new parameter
    language_confidence: Optional[float] = None # Add new parameter
) -> str:
    try:
        system_prompt = build_full_system_prompt(
            system_prompt_override=system_prompt_override,
            detected_language=detected_language,
            language_confidence=language_confidence,
            tools_description=tools_info
        )

        # Convert deque to list for slicing and modification
        messages = list(conversation_history)
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = system_prompt
        else:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Assuming chat_with_providers expects a list
        resp = chat_with_providers(MAIN_MODEL, messages)
        content = resp["message"]["content"].strip() if resp else ""
        if not content:
            raise ValueError("Empty response.")

        # jeśli content to string zawierający JSON – zwróć jako dict
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
            }
        if isinstance(parsed, str):
            return {"text": parsed, "command": "", "params": {}}
    except Exception:
        pass
    return {"text": "Nieprawidłowa odpowiedź AI", "command": "", "params": {}}

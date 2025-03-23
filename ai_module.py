# ai_module.py
import json
import re
import os
import importlib
import requests
from typing import Dict, Any, Optional
from config import STT_MODEL, MAIN_MODEL, PROVIDER
from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT


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
        """Dynamicznie ładuje dostępnych dostawców."""
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
        try:
            return requests.get("http://localhost:1234/v1/models", timeout=5).status_code == 200
        except:
            return False

    def check_openai(self) -> bool:
        return "OPENAI_API_KEY" in os.environ

    def check_deepseek(self) -> bool:
        return "DEEPSEEK_API_KEY" in os.environ

    def check_anthropic(self) -> bool:
        return "ANTHROPIC_API_KEY" in os.environ

    # Implementacje poszczególnych dostawców
    def chat_ollama(self, model: str, messages: list) -> Optional[Dict[str, Any]]:
        try:
            response = self.providers["ollama"]["module"].chat(model=model, messages=messages)
            return {"message": {"content": response["message"]["content"]}}
        except Exception as e:
            print(f"Błąd Ollama: {e}")
            return None

    def chat_lmstudio(self, model: str, messages: list) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(
                "http://localhost:1234/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )
            return {
                "message": {
                    "content": response.json()["choices"][0]["message"]["content"]
                }
            }
        except Exception as e:
            print(f"Błąd LM Studio: {e}")
            return None

    def chat_openai(self, model: str, messages: list) -> Optional[Dict[str, Any]]:
        try:
            response = self.providers["openai"]["module"].ChatCompletion.create(
                model=model,
                messages=messages
            )
            return {"message": {"content": response.choices[0].message.content}}
        except Exception as e:
            print(f"Błąd OpenAI: {e}")
            return None

    def chat_deepseek(self, model: str, messages: list) -> Optional[Dict[str, Any]]:
        try:
            client = self.providers["deepseek"]["module"].Client(
                api_key=os.getenv("DEEPSEEK_API_KEY")
            )
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            return {"message": {"content": response.choices[0].message.content}}
        except Exception as e:
            print(f"Błąd DeepSeek: {e}")
            return None

    def chat_anthropic(self, model: str, messages: list) -> Optional[Dict[str, Any]]:
        try:
            anthropic_module = self.providers["anthropic"]["module"]
            if not anthropic_module:
                print("anthropic module not available.")
                return None
            client = anthropic_module.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

            prompt = "\n\n".join(
                f"{anthropic_module.HUMAN_PROMPT if msg['role'] == 'user' else anthropic_module.AI_PROMPT} {msg['content']}"
                for msg in messages
            )
            response = client.completions.create(
                model=model,
                prompt=prompt,
                max_tokens_to_sample=1000
            )
            return {"message": {"content": response.completion}}
        except Exception as e:
            print(f"Błąd Anthropic: {e}")
            return None

    def chat_transformer(self, model: str, messages: list) -> Optional[Dict[str, Any]]:
        try:
            from transformers import pipeline
            generator = pipeline('text-generation', model=model)
            response = generator(
                messages[-1]["content"],
                max_length=512,
                do_sample=True
            )
            return {"message": {"content": response[0]["generated_text"]}}
        except Exception as e:
            print(f"Błąd Transformers: {e}")
            return None


ai_providers = AIProviders()


def health_check() -> Dict[str, bool]:
    """Zwraca status wszystkich dostawców"""
    return {
        provider: ai_providers.providers[provider]["check"]()
        for provider in ai_providers.providers
    }


def remove_chain_of_thought(text: str) -> str:
    pattern = r"<think>.*?</think>|<\|begin_of_thought\|>.*?<\|end_of_thought\|>|<\|begin_of_solution\|>.*?<\|end_of_solution\|>|<\|end\|>"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def extract_json(text: str) -> str:
    text = text.strip()
    # Jeśli mamy potrójne backticki, spróbuj je ściąć z początku/końca
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) > 0 and lines[0].strip() == "```":
            lines = lines[1:]
        if len(lines) > 0 and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    match = re.search(r'({.*})', text, re.DOTALL)
    return match.group(1) if match else text


def chat_with_providers(model: str, messages: list) -> Dict[str, Any]:
    selected_provider = PROVIDER.lower()

    # Najpierw próba z wybranym dostawcą
    if selected_provider in ai_providers.providers:
        provider = ai_providers.providers[selected_provider]
        if provider["check"]():
            response = provider["chat"](model, messages)
            if response:
                return response

    # Fallback: próba wszystkich dostawców po kolei
    for provider_name in ai_providers.providers:
        if provider_name == selected_provider:
            continue
        provider = ai_providers.providers[provider_name]
        if provider["check"]():
            response = provider["chat"](model, messages)
            if response:
                return response

    return {"message": {"content": '{"command": "", "params": "", "text": "Błąd: Żaden dostawca nie odpowiada"}'}}


def refine_query(text_input: str) -> str:
    messages = [
        {"role": "system", "content": CONVERT_QUERY_PROMPT},
        {"role": "user", "content": text_input}
    ]
    try:
        response = chat_with_providers(STT_MODEL, messages)
        return remove_chain_of_thought(response["message"]["content"])
    except Exception as e:
        print(f"Błąd przetwarzania zapytania: {e}")
        return text_input


def generate_response(conversation_history: list, functions_info: str = "") -> str:
    system_prompt = SYSTEM_PROMPT + (" Dostępne funkcje: " + functions_info if functions_info else "")
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    response = chat_with_providers(MAIN_MODEL, messages)
    return remove_chain_of_thought(response["message"]["content"])


def parse_response(response_text: str) -> dict:
    try:
        return json.loads(extract_json(response_text))
    except json.JSONDecodeError:
        return {"error": "Nieprawidłowa odpowiedź AI"}

# ai_module.py
import json
import re
import ollama
from config import STT_MODEL, MAIN_MODEL
from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT

def remove_chain_of_thought(text: str) -> str:
    pattern = r"<think>.*?</think>|<\|begin_of_thought\|>.*?<\|end_of_thought\|>|<\|begin_of_solution\|>.*?<\|end_of_solution\|>|<\|end\|>"
    return re.sub(pattern, "", text, flags=re.DOTALL)

def extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
        text = "\n".join(lines).strip()
    match = re.search(r'({.*})', text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def refine_query(text_input: str) -> str:
    try:
        response = ollama.chat(
            model=STT_MODEL,
            messages=[
                {"role": "system", "content": CONVERT_QUERY_PROMPT},
                {"role": "user", "content": text_input}
            ]
        )
        refined_query = response["message"]["content"].strip()
        return refined_query
    except Exception as e:
        print(f"Błąd przy refiningu zapytania: {e}")
        return text_input

def generate_response(conversation_history: list, functions_info: str = "") -> str:
    system_prompt = SYSTEM_PROMPT + ((" Dostępne funkcje: " + functions_info) if functions_info else "")
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    try:
        response = ollama.chat(model=MAIN_MODEL, messages=messages)
        return response["message"]["content"]
    except Exception as e:
        print(f"Błąd komunikacji z modelem: {e}")
        return '{"command": "", "params": "", "text": "Przepraszam, wystąpił błąd podczas komunikacji z AI."}'

def parse_response(response_text: str) -> dict:
    ai_response_extracted = extract_json(response_text)
    try:
        structured_output = json.loads(ai_response_extracted)
    except json.JSONDecodeError:
        structured_output = None
    return structured_output if isinstance(structured_output, dict) else {}

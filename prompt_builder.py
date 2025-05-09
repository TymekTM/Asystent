"""
prompt_builder.py

Centralized prompt building utilities for Asystent AI system.
All logic for constructing prompts for AI models, including system prompts, module prompts, and dynamic prompt generation, should be placed here.
"""

from typing import Optional, List # Added List
from prompts import (
    CONVERT_QUERY_PROMPT,
    SYSTEM_PROMPT,
    SEE_SCREEN_PROMPT,
    MODULE_RESULT_PROMPT,
    SEARCH_SUMMARY_PROMPT,
    DEEPTHINK_PROMPT,
)
import datetime

def get_current_date() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")

def build_system_prompt(name: str = "Jarvis", current_date: Optional[str] = None) -> str:
    """Build the main system prompt for the AI assistant."""
    if not current_date:
        current_date = get_current_date()
    # SYSTEM_PROMPT may use {name} and {current_date} if formatted
    return SYSTEM_PROMPT.format(name=name, current_date=current_date)

# --- Dynamic Prompt Builders ---
def build_language_info_prompt(detected_language: Optional[str], language_confidence: Optional[float]) -> str:
    if detected_language:
        confidence_str = f" (confidence: {language_confidence:.2f})" if language_confidence is not None else ""
        return f"\n\nUser query language was detected as: {detected_language} Confidence: {confidence_str}. Respond in the detected language unless the query explicitly asks for a different language or the confidence is very low."
    return ""

def build_tools_prompt(functions_info: str) -> str:
    return f"\n\nAvailable tools: {functions_info}"

def build_active_window_prompt(active_window_title: Optional[str]) -> str:
    """Builds the prompt segment for the currently active window."""
    if active_window_title:
        return f"\nUser is currently using: {active_window_title}."
    return ""

def build_convert_query_prompt(detected_language: str) -> str:
    """Builds the prompt for refining/correcting a user query based on detected language."""
    language_lock = (
        f"The user's language is {detected_language}. "
        "DO NOT translate. Only correct transcription errors."
    )
    return f"{language_lock}\n{CONVERT_QUERY_PROMPT}"

# --- General Prompt Construction ---
def build_full_system_prompt(
    system_prompt_override: Optional[str],
    detected_language: Optional[str],
    language_confidence: Optional[float],
    tools_description: str,
    active_window_title: Optional[str], # Added
    track_active_window_setting: bool, # Added to control inclusion
    tool_suggestion: Optional[str] = None # NEW
) -> str:
    """Builds the complete system prompt by assembling various components, with optional tool suggestion."""
    base_prompt_content = system_prompt_override if system_prompt_override else build_system_prompt()
    language_segment = build_language_info_prompt(detected_language, language_confidence)
    suggestion_segment = f"\n\nYou may want to use this tool: {tool_suggestion}" if tool_suggestion else ""
    tools_segment = build_tools_prompt(tools_description)
    active_window_segment = ""
    if track_active_window_setting:
        active_window_segment = build_active_window_prompt(active_window_title)
    
    return f"{base_prompt_content}{language_segment}{suggestion_segment}{tools_segment}{active_window_segment}"

# --- Utility for module result prompt ---
def build_module_result_prompt(module_result: str) -> str:
    return MODULE_RESULT_PROMPT.format(module_result=module_result)

# --- Utility for search summary prompt ---
def build_search_summary_prompt() -> str:
    return SEARCH_SUMMARY_PROMPT

# --- Utility for deepthink prompt ---
def build_deepthink_prompt() -> str:
    return DEEPTHINK_PROMPT

# --- Utility for see screen prompt ---
def build_see_screen_prompt() -> str:
    return SEE_SCREEN_PROMPT

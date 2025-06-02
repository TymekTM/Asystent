"""
Daily Briefing Module for Asystent
Provides proactive morning briefings with weather, calendar, holidays, and personalized information.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any
import requests
from pathlib import Path
import threading

# AI and memory integration imports
logger = logging.getLogger(__name__)

try:
    from ai_module import generate_response, detect_language_async
    AI_MODULE_AVAILABLE = True
except ImportError:
    AI_MODULE_AVAILABLE = False
    logger.warning("AI module not available - falling back to template-based briefings")

try:
    from modules.memory_module import retrieve_memories
    MEMORY_MODULE_AVAILABLE = True
except ImportError:
    MEMORY_MODULE_AVAILABLE = False
    logger.warning("Memory module not available - skipping memory integration")

class DailyBriefingModule:
    """Handles proactive daily briefings with weather, calendar, holidays, and memories."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.user_name = config.get('daily_briefing', {}).get('user_name', config.get('user_name', 'Tymek'))
        self.location = config.get('daily_briefing', {}).get('location', 'Warsaw,PL')
        self.enabled = config.get('daily_briefing', {}).get('enabled', True)
        self.briefing_time = config.get('daily_briefing', {}).get('briefing_time', '08:00')
        self.startup_briefing = config.get('daily_briefing', {}).get('startup_briefing', True)
        self.scheduled_briefing = config.get('daily_briefing', {}).get('scheduled_briefing', False)
        self.include_weather = config.get('daily_briefing', {}).get('include_weather', True)
        self.include_calendar = config.get('daily_briefing', {}).get('include_calendar', True)
        self.include_holidays = config.get('daily_briefing', {}).get('include_holidays', True)
        self.include_memories = config.get('daily_briefing', {}).get('include_memories', False)
        self.weekend_briefing = config.get('daily_briefing', {}).get('weekend_briefing', True)
        self.min_interval_hours = config.get('daily_briefing', {}).get('min_interval_hours', 12)
        self.briefing_style = config.get('daily_briefing', {}).get('briefing_style', 'normal')  # normal, funny, serious
        self.use_ai_generation = config.get('daily_briefing', {}).get('use_ai_generation', True) and AI_MODULE_AVAILABLE
        
        # Session tracking
        self.session_file = Path('user_data') / 'daily_briefing_session.json'
        self.session_file.parent.mkdir(exist_ok=True)
        
        # Scheduling
        self._scheduler_task = None
        self._scheduler_running = False
        self._stop_scheduler = False
        
        # Polish holidays API
        self.holidays_api_url = "https://date.nager.at/api/v3/PublicHolidays"
        
        # Day names in Polish
        self.polish_days = {
            0: 'poniedziałek', 1: 'wtorek', 2: 'środa', 3: 'czwartek',
            4: 'piątek', 5: 'sobota', 6: 'niedziela'
        }
        
        # Month names in Polish
        self.polish_months = {
            1: 'stycznia', 2: 'lutego', 3: 'marca', 4: 'kwietnia',
            5: 'maja', 6: 'czerwca', 7: 'lipca', 8: 'sierpnia',
            9: 'września', 10: 'października', 11: 'listopada', 12: 'grudnia'
        }
    
    def should_deliver_briefing(self, force_delivery: bool = False) -> bool:
        """Check if briefing should be delivered today."""
        if not self.enabled:
            logger.info("Daily briefing disabled in config")
            return False
        
        # Force delivery for manual requests
        if force_delivery:
            return True
        
        today = datetime.now().date()
        session_data = self._load_session_data()
        
        # Check if briefing was already delivered today
        last_briefing = session_data.get('last_briefing_date')
        if last_briefing == today.isoformat():
            logger.info("Daily briefing already delivered today")
            return False
        
        # Check weekend setting
        if today.weekday() >= 5 and not self.weekend_briefing:  # Saturday = 5, Sunday = 6
            logger.info("Weekend briefing disabled")
            return False
        
        # Check minimum interval
        if last_briefing:
            try:
                last_date = datetime.fromisoformat(last_briefing + 'T00:00:00')
                hours_since = (datetime.now() - last_date).total_seconds() / 3600
                if hours_since < self.min_interval_hours:
                    logger.info(f"Too soon for briefing, only {hours_since:.1f} hours since last")
                    return False
            except Exception as e:
                logger.warning(f"Error parsing last briefing date: {e}")
        
        return True
    
    def start_scheduler(self, assistant_callback=None):
        """Start the briefing scheduler."""
        if not self.scheduled_briefing or self._scheduler_running:
            return
        
        logger.info("Starting daily briefing scheduler...")
        self._stop_scheduler = False
        self._scheduler_running = True
        self._assistant_callback = assistant_callback
        
        # Start scheduler in a separate thread
        def run_scheduler():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._scheduler_loop())
            finally:
                loop.close()
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info(f"Daily briefing scheduler started for {self.briefing_time}")
    
    def stop_scheduler(self):
        """Stop the briefing scheduler."""
        if self._scheduler_running:
            logger.info("Stopping daily briefing scheduler...")
            self._stop_scheduler = True
            self._scheduler_running = False
    
    async def _scheduler_loop(self):
        """Main scheduler loop that checks for briefing time."""
        while not self._stop_scheduler:
            try:
                now = datetime.now()
                target_time = self._parse_briefing_time()
                
                if target_time and self._should_deliver_at_time(now, target_time):
                    logger.info("Scheduled briefing time reached")
                    
                    if self.should_deliver_briefing():
                        briefing_text = await self.deliver_briefing()
                        
                        # Deliver briefing through assistant callback if available
                        if briefing_text and self._assistant_callback:
                            try:
                                await self._assistant_callback(briefing_text)
                            except Exception as e:
                                logger.error(f"Error delivering scheduled briefing: {e}")
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    def _parse_briefing_time(self) -> Optional[time]:
        """Parse briefing time string into time object."""
        try:
            hour, minute = self.briefing_time.split(':')
            return time(int(hour), int(minute))
        except (ValueError, AttributeError):
            logger.error(f"Invalid briefing time format: {self.briefing_time}")
            return None
    
    def _should_deliver_at_time(self, now: datetime, target_time: time) -> bool:
        """Check if current time matches briefing time (within 1 minute window)."""
        current_time = now.time()
        target_minute = target_time.hour * 60 + target_time.minute
        current_minute = current_time.hour * 60 + current_time.minute
        
        # Allow 1-minute window for delivery
        return abs(current_minute - target_minute) <= 1
    
    def _load_session_data(self) -> Dict[str, Any]:
        """Load session tracking data."""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load session data: {e}")
        
        return {}
    
    def _save_session_data(self, data: Dict[str, Any]) -> None:
        """Save session tracking data."""
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Could not save session data: {e}")
    
    def _mark_briefing_delivered(self) -> None:
        """Mark that briefing was delivered today."""
        session_data = self._load_session_data()
        session_data['last_briefing_date'] = datetime.now().date().isoformat()
        session_data['briefing_count'] = session_data.get('briefing_count', 0) + 1
        session_data['last_delivery_time'] = datetime.now().isoformat()
        self._save_session_data(session_data)
    
    async def get_weather_data(self) -> Optional[Dict[str, Any]]:
        """Get current weather data."""
        if not self.include_weather:
            return None
            
        try:
            # Import weather module functions
            from modules.weather_module import _handle_current
            
            # Create parameters for weather functions  
            weather_params = {
                "location": self.location,
                "lang": "pl",
                "unit": "metric"
            }
            
            current_weather_text = _handle_current(weather_params)
            
            return {
                'current_text': current_weather_text,
                'location': self.location
            }
        except Exception as e:
            logger.error(f"Could not get weather data: {e}")
            return None
    
    async def get_polish_holidays(self) -> List[Dict[str, Any]]:
        """Get Polish holidays for current year."""
        if not self.include_holidays:
            return []
            
        try:
            current_year = datetime.now().year
            url = f"{self.holidays_api_url}/{current_year}/PL"
            
            response = await asyncio.to_thread(requests.get, url, timeout=10)
            response.raise_for_status()
            
            holidays = response.json()
            today = datetime.now().date()
            
            # Filter for today and upcoming holidays (next 7 days)
            relevant_holidays = []
            for holiday in holidays:
                holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d').date()
                if holiday_date == today:
                    holiday['is_today'] = True
                    relevant_holidays.append(holiday)
                elif today < holiday_date <= today + timedelta(days=7):
                    holiday['is_upcoming'] = True
                    relevant_holidays.append(holiday)
            
            return relevant_holidays
        except Exception as e:
            logger.error(f"Could not get Polish holidays: {e}")
            return []
    
    async def get_calendar_events(self) -> List[Dict[str, Any]]:
        """Get today's calendar events and reminders."""
        if not self.include_calendar:
            return []
            
        try:            # Import core module functions
            from modules.core_module import get_reminders_for_today
            
            reminders = get_reminders_for_today()
            return reminders or []
        except Exception as e:
            logger.error(f"Could not get calendar events: {e}")
            return []

    async def get_memories_data(self) -> List[Dict[str, Any]]:
        """Get relevant memories or historical data."""
        if not self.include_memories or not MEMORY_MODULE_AVAILABLE:
            return []
            
        try:
            memories = []
            
            # Get recent memories (last 30 days)
            recent_memories_result = retrieve_memories(
                query="", 
                limit=10,
                user=None  # Get memories from all users
            )
            
            if len(recent_memories_result) >= 2 and recent_memories_result[1]:  # success
                memories_text = recent_memories_result[0]
                if memories_text and "Nie znaleziono" not in memories_text:
                    # Parse the memories text to extract individual memories
                    memory_lines = memories_text.split('\n')
                    for line in memory_lines:
                        if line.strip() and not line.startswith("Znalezione"):
                            memories.append({
                                'content': line.strip(),
                                'type': 'recent_memory'
                            })
            
            # Get memories related to daily briefings
            briefing_memories_result = retrieve_memories(
                query="briefing dzień dobry pogoda",
                limit=5,
                user=None
            )
            
            if len(briefing_memories_result) >= 2 and briefing_memories_result[1]:  # success
                briefing_text = briefing_memories_result[0]
                if briefing_text and "Nie znaleziono" not in briefing_text:
                    memory_lines = briefing_text.split('\n')
                    for line in memory_lines:
                        if line.strip() and not line.startswith("Znalezione"):
                            memories.append({
                                'content': line.strip(),
                                'type': 'briefing_memory'
                            })
            
            return memories[:5]  # Limit to 5 most relevant memories
            
        except Exception as e:
            logger.error(f"Could not get memories data: {e}")
            return []
    
    def _format_date_polish(self, date: datetime) -> str:
        """Format date in Polish."""
        day_name = self.polish_days[date.weekday()]
        day = date.day
        month_name = self.polish_months[date.month]
        year = date.year
        
        return f"{day_name}, {day} {month_name} {year}"
    
    def _format_weather_info(self, weather_data: Optional[Dict[str, Any]]) -> str:
        """Format weather information for briefing."""
        if not weather_data or not weather_data.get('current_text'):
            return ""
        
        current_text = weather_data['current_text']
        if current_text and "Wystąpił błąd" not in current_text:
            return f"Jeśli chodzi o pogodę - {current_text.lower()}"
        
        return ""
    
    def _format_holidays_info(self, holidays: List[Dict[str, Any]]) -> str:
        """Format holidays information for briefing."""
        if not holidays:
            return ""
        
        today_holidays = [h for h in holidays if h.get('is_today')]
        upcoming_holidays = [h for h in holidays if h.get('is_upcoming')]
        
        info_parts = []
        
        if today_holidays:
            holiday_names = [h['localName'] for h in today_holidays]
            if len(holiday_names) == 1:
                info_parts.append(f"Dzisiaj obchodzimy {holiday_names[0]}.")
            else:
                info_parts.append(f"Dzisiaj obchodzimy: {', '.join(holiday_names)}.")
        
        if upcoming_holidays and len(upcoming_holidays) == 1:
            holiday = upcoming_holidays[0]
            holiday_date = datetime.strptime(holiday['date'], '%Y-%m-%d')
            days_diff = (holiday_date.date() - datetime.now().date()).days
            
            if days_diff == 1:
                info_parts.append(f"Jutro będzie {holiday['localName']}.")
            elif days_diff <= 3:
                info_parts.append(f"Za {days_diff} dni będzie {holiday['localName']}.")
        
        return " ".join(info_parts)
    
    def _format_events_info(self, events: List[Dict[str, Any]]) -> str:
        """Format calendar events and reminders for briefing."""
        if not events:
            return ""
        
        if len(events) == 1:
            return f"Masz dzisiaj jedno przypomnienie: {events[0].get('title', 'bez tytułu')}."
        elif len(events) <= 3:
            event_titles = [event.get('title', 'bez tytułu') for event in events]
            return f"Masz dzisiaj {len(events)} przypomnienia: {', '.join(event_titles)}."
        else:
            return f"Masz dzisiaj {len(events)} przypomnień do sprawdzenia."
    
    async def generate_briefing_content(self) -> Dict[str, Any]:
        """Generate the complete briefing content."""
        logger.info("Generating daily briefing content...")
        
        # Collect all data in parallel
        now = datetime.now()
        
        tasks = [
            self.get_weather_data(),
            self.get_polish_holidays(),
            self.get_calendar_events(),
            self.get_memories_data()
        ]
        
        weather_data, holidays, events, memories = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        if isinstance(weather_data, Exception):
            logger.error(f"Weather data error: {weather_data}")
            weather_data = None
        
        if isinstance(holidays, Exception):
            logger.error(f"Holidays data error: {holidays}")
            holidays = []
        
        if isinstance(events, Exception):
            logger.error(f"Events data error: {events}")
            events = []
        
        if isinstance(memories, Exception):
            logger.error(f"Memories data error: {memories}")
            memories = []
        
        # Build briefing content
        content = {
            'greeting': f"Hej {self.user_name}",
            'date': self._format_date_polish(now),
            'weather': self._format_weather_info(weather_data),
            'holidays': self._format_holidays_info(holidays),            'events': self._format_events_info(events),
            'memories': memories,
            'timestamp': now.isoformat()
        }
        
        return content
    
    async def generate_ai_briefing(self, content: Dict[str, Any]) -> Optional[str]:
        """Generate personalized briefing using AI with language detection."""
        if not self.use_ai_generation or not AI_MODULE_AVAILABLE:
            return None
        
        try:
            # Detect user language from previous interactions or use Polish as default
            user_language = 'Polish'  # Default for this assistant
            
            # Build context for AI generation
            briefing_context = {
                'user_name': self.user_name,
                'location': self.location,
                'date': content['date'],
                'weather': content['weather'],
                'holidays': content['holidays'],
                'events': content['events'],
                'memories': content['memories'],
                'style': self.briefing_style,
                'language': user_language
            }
            
            # Create AI prompt for briefing generation
            ai_prompt = self._build_ai_prompt(briefing_context)
            
            # Generate response using AI
            logger.info("Generating AI-powered daily briefing...")
            response = await generate_response(ai_prompt, context="daily_briefing")
            
            if response and isinstance(response, str):
                # Clean up the response
                cleaned_response = response.strip()
                if cleaned_response:
                    logger.info("AI briefing generated successfully")
                    return cleaned_response
            
            logger.warning("AI generation failed, falling back to template")
            return None
            
        except Exception as e:
            logger.error(f"Error generating AI briefing: {e}")
            return None
    
    def _build_ai_prompt(self, context: Dict[str, Any]) -> str:
        """Build AI prompt for briefing generation."""
        style_instructions = {
            'normal': "Napisz naturalny, przyjazny dzienny briefing w języku polskim.",
            'funny': "Napisz zabawny, energiczny dzienny briefing z humorem i emoji w języku polskim.",
            'serious': "Napisz profesjonalny, merytoryczny dzienny briefing w formalnym tonie w języku polskim."
        }
        
        style_instruction = style_instructions.get(context['style'], style_instructions['normal'])
        
        prompt = f"""
{style_instruction}

Informacje do uwzględnienia:
- Imię użytkownika: {context['user_name']}
- Data: {context['date']}
- Lokalizacja: {context['location']}

"""
        
        if context['weather']:
            prompt += f"- Pogoda: {context['weather']}\n"
        
        if context['holidays']:
            prompt += f"- Święta: {context['holidays']}\n"
        
        if context['events']:
            prompt += f"- Wydarzenia: {context['events']}\n"
        
        if context['memories'] and len(context['memories']) > 0:
            prompt += "- Wspomnienia/historie:\n"
            for memory in context['memories'][:3]:  # Limit to top 3
                prompt += f"  • {memory.get('content', '')}\n"
        
        prompt += f"""
Styl odpowiedzi: {context['style']}
Język: {context['language']}

Wygeneruj kompletny dzienny briefing (2-4 zdania) zawierający powitanie, informacje o dacie, pogodzie, świętach, wydarzeniach i zakończenie odpowiednie do stylu. Odpowiedz TYLKO briefingiem, bez dodatkowych komentarzy.
"""
        
        return prompt.strip()
    
    def build_briefing_text(self, content: Dict[str, Any]) -> str:
        """Build the final briefing text from content."""
        # Style-specific greetings
        if self.briefing_style == 'funny':
            greeting = f"Siema {content['greeting'].split()[1]}! 😄"
        elif self.briefing_style == 'serious':
            greeting = f"Dzień dobry, {content['greeting'].split()[1]}."
        else:
            greeting = content['greeting']
        
        parts = [
            f"{greeting}, dziś jest {content['date']}."
        ]
        
        if content['weather']:
            if self.briefing_style == 'funny':
                parts.append(f"Co się dzieje z pogodą? {content['weather'].replace('Jeśli chodzi o pogodę - ', '').capitalize()} 🌤️")
            else:
                parts.append(content['weather'])
        
        if content['holidays']:
            if self.briefing_style == 'funny':
                parts.append(f"O! {content['holidays']} 🎉")
            else:
                parts.append(content['holidays'])
        
        if content['events']:
            if self.briefing_style == 'funny':
                parts.append(f"Uwaga, uwaga! {content['events']} 📅")
            else:
                parts.append(content['events'])
        
        # Style-specific endings
        weekday = datetime.now().weekday()
        if self.briefing_style == 'funny':
            if weekday == 0:  # Monday
                parts.append("No to lecimy z tym poniedziałkiem! 💪")
            elif weekday == 4:  # Friday
                parts.append("Weekend już blisko - trzymaj się! 🎉")
            elif weekday >= 5:  # Weekend
                parts.append("Weekend mode: ON! Odpocznij sobie! 😎")
            else:
                parts.append("Dawaj z tym dniem! 🚀")
        elif self.briefing_style == 'serious':
            if weekday == 0:  # Monday
                parts.append("Życzę efektywnego i skoncentrowanego rozpoczęcia tygodnia pracy.")
            elif weekday == 4:  # Friday
                parts.append("Życzę satysfakcjonującego zakończenia tygodnia roboczego.")
            elif weekday >= 5:  # Weekend
                parts.append("Życzę regenerującego i przyjemnego weekendu.")
            else:
                parts.append("Życzę konstruktywnego i wydajnego dnia.")        else:
            # Normal style (existing logic)
            if weekday == 0:  # Monday
                parts.append("Życzę produktywnego początku tygodnia!")
            elif weekday == 4:  # Friday
                parts.append("Życzę udanego zakończenia tygodnia!")
            elif weekday >= 5:  # Weekend
                parts.append("Życzę miłego weekendu!")
            else:
                parts.append("Życzę miłego dnia!")
        
        return " ".join(parts)

    async def deliver_briefing(self, force_delivery: bool = False) -> Optional[str]:
        """Generate and deliver the daily briefing."""
        try:
            if not self.should_deliver_briefing(force_delivery=force_delivery):
                return None
            
            logger.info("Generating daily briefing...")
            
            # Generate briefing content
            content = await self.generate_briefing_content()
            
            # Try AI generation first if enabled
            briefing_text = None
            if self.use_ai_generation:
                ai_briefing = await self.generate_ai_briefing(content)
                if ai_briefing:
                    briefing_text = ai_briefing
                    logger.info("Using AI-generated briefing")
            
            # Fallback to template-based briefing if AI generation failed
            if not briefing_text:
                briefing_text = self.build_briefing_text(content)
                logger.info("Using template-based briefing")
            
            # Mark as delivered (only if not forced, to avoid blocking manual requests)
            if not force_delivery:
                self._mark_briefing_delivered()
            
            logger.info(f"Daily briefing generated: {briefing_text}")
            return briefing_text
            
        except Exception as e:
            logger.error(f"Error delivering daily briefing: {e}", exc_info=True)
            return "Przepraszam, wystąpił błąd podczas przygotowywania dzisiejszego briefingu."


# Module handler function for manual briefing requests
async def handler(params: str = '', conversation_history: list = None, assistant=None) -> str:
    """Handle manual daily briefing requests."""
    if not assistant or not hasattr(assistant, 'daily_briefing'):
        return "Daily briefing nie jest dostępny."
    
    try:
        briefing_module = assistant.daily_briefing
        
        # Force delivery for manual requests
        briefing_text = await briefing_module.deliver_briefing(force_delivery=True)
        
        if briefing_text:
            return briefing_text
        else:
            return "Nie udało się wygenerować daily briefingu."
            
    except Exception as e:
        logger.error(f"Error in manual daily briefing: {e}", exc_info=True)
        return "Wystąpił błąd podczas generowania daily briefingu."


# Registration function for the module system
def register():
    """Register the daily briefing module."""
    return {
        "name": "daily_briefing",
        "description": "Proaktywny system daily briefingu z pogodą, kalendarzem i świętami",
        "handler": handler,
        "sub_commands": {
            "now": {"function": handler, "description": "Pokaż dzisiejszy briefing", "aliases": ["teraz", "dzisiaj"]}
        },
        "aliases": ["briefing", "daily", "dzienny"]
    }


async def main():
    """Test function for the daily briefing module."""
    # Test configuration
    test_config = {
        'user_name': 'Tymek',
        'daily_briefing': {
            'enabled': True,
            'location': 'Warsaw,PL',
            'briefing_time': '08:00',
            'startup_briefing': True,
            'user_name': 'Tymek',
            'include_weather': True,
            'include_calendar': True,
            'include_holidays': True,
            'include_memories': False,
            'weekend_briefing': True,
            'min_interval_hours': 1  # For testing
        }
    }
    
    briefing = DailyBriefingModule(test_config)
    result = await briefing.deliver_briefing()
    
    if result:
        print("Daily Briefing:")
        print(result)
    else:
        print("No briefing delivered")


if __name__ == "__main__":
    asyncio.run(main())

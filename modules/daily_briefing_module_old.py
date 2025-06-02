"""
Daily Briefing Module for Asystent
Provides proactive morning briefings with weather, calendar, holidays, and personalized information.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class DailyBriefingModule:
    """Handles proactive daily briefings with weather, calendar, holidays, and memories."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.user_name = config.get('user_name', 'Tymek')
        self.location = config.get('daily_briefing', {}).get('location', 'Warsaw,PL')
        self.enabled = config.get('daily_briefing', {}).get('enabled', True)
        self.briefing_time = config.get('daily_briefing', {}).get('time', '08:00')
        self.startup_briefing = config.get('daily_briefing', {}).get('startup_briefing', True)
        
        # Session tracking
        self.session_file = Path('user_data') / 'daily_briefing_session.json'
        self.session_file.parent.mkdir(exist_ok=True)
        
        # Polish holidays API
        self.holidays_api_url = "https://date.nager.at/api/v3/PublicHolidays"
        
        # Day names in Polish
        self.polish_days = {
            0: 'poniedziałek', 1: 'wtorek', 2: 'środa', 3: 'czwartek',
            4: 'piątek', 5: 'sobota', 6: 'niedziela'
        }
        
        # Month names in Polish
        self.polish_months = {
            1: 'styczeń', 2: 'luty', 3: 'marzec', 4: 'kwiecień',
            5: 'maj', 6: 'czerwiec', 7: 'lipiec', 8: 'sierpień',
            9: 'wrzesień', 10: 'październik', 11: 'listopad', 12: 'grudzień'
        }
    
    def should_deliver_briefing(self) -> bool:
        """Check if briefing should be delivered today."""
        if not self.enabled:
            return False
        
        today = datetime.now().date()
        session_data = self._load_session_data()
        
        # Check if briefing was already delivered today
        last_briefing = session_data.get('last_briefing_date')
        if last_briefing == today.isoformat():
            return False
        
        # Check if startup briefing is enabled
        if self.startup_briefing:
            return True
        
        # TODO: Add scheduled time check
        return False
    
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
        session_data['briefing_count'] = session_data.get('briefing_count', 0) + 1        self._save_session_data(session_data)
    
    async def get_weather_data(self) -> Optional[Dict[str, Any]]:
        """Get current weather data."""
        try:
            # Import weather module functions
            from modules.weather_module import _handle_current, _handle_forecast
            
            # Create parameters for weather functions
            weather_params = {
                "location": self.location,
                "lang": "pl",
                "unit": "metric"
            }
            
            current_weather_text = _handle_current(weather_params)
            forecast_text = _handle_forecast(weather_params)
            
            # Parse the text responses to extract useful information
            return {
                'current_text': current_weather_text,
                'forecast_text': forecast_text
            }
        except Exception as e:
            logger.error(f"Could not get weather data: {e}")
            return None
    
    async def get_polish_holidays(self) -> List[Dict[str, Any]]:
        """Get Polish holidays for current year."""
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
        try:
            # Import core module functions
            from modules.core_module import get_reminders_for_today
            
            reminders = get_reminders_for_today()
            return reminders or []
        except Exception as e:
            logger.error(f"Could not get calendar events: {e}")
            return []
    
    async def get_memories_data(self) -> List[Dict[str, Any]]:
        """Get relevant memories or historical data."""
        try:
            # TODO: Integrate with memory module when available
            # For now, return empty list
            return []
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
            return "Nie udało się pobrać informacji o pogodzie."
        
        current_text = weather_data['current_text']
        
        # Extract basic weather info from the text response
        return f"Pogoda: {current_text}"
    
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
            else:
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
        
        # Collect all data
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
            'holidays': self._format_holidays_info(holidays),
            'events': self._format_events_info(events),
            'memories': memories,
            'timestamp': now.isoformat()
        }
        
        return content
    
    def build_briefing_text(self, content: Dict[str, Any]) -> str:
        """Build the final briefing text from content."""
        parts = [
            f"{content['greeting']}, dziś jest {content['date']}."
        ]
        
        if content['weather']:
            parts.append(content['weather'])
        
        if content['holidays']:
            parts.append(content['holidays'])
        
        if content['events']:
            parts.append(content['events'])
        
        # Add encouraging ending
        parts.append("Życzę miłego dnia!")
        
        return " ".join(parts)
    
    async def deliver_briefing(self) -> Optional[str]:
        """Generate and deliver the daily briefing."""
        try:
            if not self.should_deliver_briefing():
                logger.info("Daily briefing already delivered today or disabled")
                return None
            
            logger.info("Delivering daily briefing...")
            
            # Generate briefing content
            content = await self.generate_briefing_content()
            briefing_text = self.build_briefing_text(content)
            
            # Mark as delivered
            self._mark_briefing_delivered()
            
            logger.info("Daily briefing generated successfully")
            return briefing_text
            
        except Exception as e:
            logger.error(f"Error delivering daily briefing: {e}")
            return "Przepraszam, wystąpił błąd podczas przygotowywania dzisiejszego briefingu."


async def main():
    """Test function for the daily briefing module."""
    # Test configuration
    test_config = {
        'user_name': 'Tymek',
        'daily_briefing': {
            'enabled': True,
            'location': 'Warsaw,PL',
            'time': '08:00',
            'startup_briefing': True
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

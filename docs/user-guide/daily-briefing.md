# Daily Briefing Feature

The Daily Briefing feature is a comprehensive feature that provides personalized daily summaries with context-aware information.

## Overview

The daily briefing system generates AI-powered personalized reports that combine:
- Current weather information from wttr.in API
- Memory integration from your past interactions
- Calendar events and holidays
- Holiday information from international holiday APIs
- Personalized style adaptations based on preferences
- Proactive information delivery at scheduled times

## How to Use

To get your daily briefing, you can use any of these commands:
- "Give me my daily briefing"
- "What's my day looking like?"
- "Brief me on today"
- "Podsumowanie dnia" (Polish)
- "Co dziś planujemy?" (Polish)

## Features

### AI-Generated Content

The briefing is intelligently generated using:
- Contextual understanding of your preferences
- Information from past interactions
- Available external data sources
- Your preferred language
- Style variations (normal, funny, serious)
- Advanced prompt engineering with multi-part context
- Fallback to template-based generation if AI fails

### Weather Integration

The briefing includes current weather information from:
- Temperature and conditions from wttr.in API
- Weather forecasts for the day
- Weather-appropriate recommendations
- Location-specific details based on user preferences
- Automatic error handling with graceful fallbacks

### Memory Context

The system includes relevant information from your memory:
- Recent interactions and topics
- Previously mentioned events or plans
- Important dates or reminders
- Personalized content based on historical data
- Semantic search for relevant memories

### Language Support

The briefing automatically adapts to your preferred language:
- Detects your language from the request
- Defaults to Polish if no language is specified
- Full international date formatting
- Custom language templates for key components

### Scheduling Options

The briefing can be delivered in different ways:
- On-demand when requested
- Automatically at system startup
- Scheduled at specific times (e.g., 8:00 AM daily)
- Weekend scheduling options
- Minimum interval controls to prevent repetition
- Supports multiple languages for the full briefing

### Style Variations

You can request different briefing styles:
- Standard: Balanced, informative briefing
- Funny: More casual with light humor
- Serious: More formal and direct

Example: "Give me a funny daily briefing"

## Configuration

The Daily Briefing module can be configured in the web UI:
1. Navigate to the Modules page
2. Find "Daily Briefing Module" in the list
3. Toggle it on or off
4. Use the configuration options to customize the briefing style

Available configuration options:

```json
{
  "daily_briefing": {
    "enabled": true,
    "user_name": "Tymek",
    "location": "Warsaw,PL",
    "briefing_time": "08:00",
    "startup_briefing": true,
    "scheduled_briefing": false,
    "include_weather": true,
    "include_calendar": true,
    "include_holidays": true,
    "include_memories": true,
    "weekend_briefing": true,
    "min_interval_hours": 12,
    "briefing_style": "normal",
    "use_ai_generation": true
  }
}
```

- **enabled**: Turn the daily briefing function on/off
- **user_name**: Your name for personalized greetings
- **location**: Your location for weather (format: City,CountryCode)
- **briefing_time**: When scheduled briefings should occur (24h format)
- **startup_briefing**: Whether to show a briefing when the system starts up
- **scheduled_briefing**: Enable/disable time-based automatic briefings
- **include_weather**: Include weather information in briefings
- **include_calendar**: Include calendar events in briefings
- **include_holidays**: Include holiday information in briefings
- **include_memories**: Include your saved memories in briefings
- **weekend_briefing**: Whether briefings should run on weekends
- **min_interval_hours**: Minimum hours between briefings (prevents duplicates)
- **briefing_style**: Style preference ("normal", "funny", or "serious")
- **use_ai_generation**: Use AI for briefing generation (vs templates)

## Troubleshooting

If your briefing doesn't include specific information:
- Check that the memory module is enabled
- Ensure any API integrations are properly configured
- Verify internet connectivity for weather data

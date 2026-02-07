---
name: weather
description: Get weather information for locations
version: 1.0.0
author: ClawdBot
tags: [weather, information]
requires_bins: []
requires_env: []
---

# Weather Information

Get current weather and forecasts for any location.

## How to Use

Use the web_fetch tool to query weather APIs:

### OpenWeatherMap
```
https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}
```

### wttr.in (No API key required)
```
https://wttr.in/{location}?format=j1
```

## Response Format

Parse the JSON response and provide:
- Current temperature
- Weather conditions
- Humidity
- Wind speed
- Forecast (if available)

## Example

"What's the weather in San Francisco?"

1. Fetch: `https://wttr.in/San Francisco?format=j1`
2. Parse response
3. Format user-friendly response:
   "Current weather in San Francisco: 65°F, Partly Cloudy, Humidity: 70%, Wind: 10 mph"

---
name: weather
description: "Get weather information using wttr.in"
user-invocable: true
metadata:
  openclaw:
    emoji: "🌤️"
    homepage: "https://wttr.in"
    always: true
---

# Weather Information Skill

Use the `wttr.in` service to get weather information. This is a simple, no-API-key-required weather service.

## Basic Usage

```bash
# Get weather for current location
curl wttr.in

# Get weather for a specific location
curl "wttr.in/San+Francisco"

# Get weather in specific format
curl "wttr.in/London?format=%l:+%C+%t"
```

## Format Options

Use `?format=` to customize the output:

- `%l` - Location name
- `%C` - Weather condition
- `%t` - Temperature
- `%h` - Humidity
- `%w` - Wind
- `%m` - Moon phase
- `%M` - Moon day
- `%p` - Precipitation (mm)
- `%P` - Pressure (hPa)

Example format string:
```
wttr.in/Paris?format="%l:+%C+%t+%h+%w"
```

## Options

- `?0` - Current weather only
- `?1` - Current + today's forecast
- `?2` - Current + 2-day forecast
- `?m` - Metric units (default)
- `?u` - USCS units (Fahrenheit)
- `?M` - MPH wind speed
- `?lang=<code>` - Language (e.g., `?lang=fr`)

## Examples

```bash
# Simple current weather
curl "wttr.in/Tokyo?0"

# 2-day forecast in Fahrenheit
curl "wttr.in/NYC?2u"

# Custom format
curl "wttr.in/London?format=%l:+%C+%t+(feels+like+%f)"

# PNG image
curl "wttr.in/Paris.png" > weather.png
```

## Tips

- Use `+` for spaces in location names
- Service works worldwide
- No API key required
- Can return PNG images for embedding
- Supports many languages

## Common Locations

- Cities: "New York", "London", "Tokyo"
- Airports: "~LAX", "~JFK"
- Domains: "@github.com", "@google.com"
- Special: "Moon" (Moon phase info)

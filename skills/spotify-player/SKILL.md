---
name: spotify-player
description: Control Spotify playback and manage playlists
version: 1.0.0
author: ClawdBot
tags: [spotify, music, audio]
requires_bins: []
requires_env: [SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET]
requires_config: []
---

# Spotify Player Control

Control Spotify playback, search music, and manage playlists.

## Available Tools

- **web_fetch**: Access Spotify Web API
- **bash**: Use spotify-cli if installed

## Spotify Web API

Base URL: `https://api.spotify.com/v1/`

### Authentication

Get access token:
```
POST https://accounts.spotify.com/api/token
Headers:
  Authorization: Basic {base64(client_id:client_secret)}
Body: grant_type=client_credentials
```

### Common Endpoints

#### Get Currently Playing
```
GET https://api.spotify.com/v1/me/player/currently-playing
Headers:
  Authorization: Bearer {access_token}
```

#### Search
```
GET https://api.spotify.com/v1/search?q={query}&type=track,artist,album
```

#### Play Track
```
PUT https://api.spotify.com/v1/me/player/play
Body: {"uris": ["spotify:track:{track_id}"]}
```

#### Pause
```
PUT https://api.spotify.com/v1/me/player/pause
```

#### Next/Previous
```
POST https://api.spotify.com/v1/me/player/next
POST https://api.spotify.com/v1/me/player/previous
```

## Usage Examples

User: "Play Shape of You by Ed Sheeran"
1. Search for track using /v1/search
2. Get track URI
3. Play using /v1/me/player/play

User: "What's currently playing?"
1. Fetch from /v1/me/player/currently-playing
2. Parse track info
3. Present artist, track, album

User: "Pause Spotify"
1. Call /v1/me/player/pause

## Environment Setup

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
```

Get credentials from: https://developer.spotify.com/dashboard

## Scopes Required

For user playback control:
- `user-read-playback-state`
- `user-modify-playback-state`
- `user-read-currently-playing`

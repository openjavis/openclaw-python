---
name: github
description: GitHub integration for repository operations
version: 1.0.0
author: ClawdBot
tags: [github, git, vcs]
requires_bins: [git]
requires_env: [GITHUB_TOKEN]
---

# GitHub Integration

Integrate with GitHub repositories for various operations.

## Available Tools

- **bash**: Execute git commands
- **web_fetch**: Fetch GitHub API data

## Common Operations

### Clone Repository
```bash
git clone https://github.com/user/repo.git
```

### Check Status
```bash
git status
```

### Create Branch
```bash
git checkout -b feature-branch
```

### Commit Changes
```bash
git add .
git commit -m "Commit message"
```

### Push Changes
```bash
git push origin branch-name
```

## GitHub API

Use web_fetch with GitHub API:
- `https://api.github.com/repos/{owner}/{repo}`
- `https://api.github.com/repos/{owner}/{repo}/issues`
- `https://api.github.com/repos/{owner}/{repo}/pulls`

Include GITHUB_TOKEN in Authorization header for authenticated requests.

---
name: github
description: "GitHub operations via gh CLI - PRs, issues, repos, releases"
user-invocable: true
metadata:
  openclaw:
    emoji: "🐙"
    homepage: "https://cli.github.com/"
    requires:
      bins: ["gh"]
    install:
      - kind: brew
        formula: gh
        os: ["darwin", "linux"]
---

# GitHub Operations Skill

Use the `gh` CLI for all GitHub operations. This skill provides guidance for:

- Creating and managing pull requests
- Creating and managing issues
- Repository operations
- Release management
- Viewing repository information

## Prerequisites

- `gh` CLI must be installed and authenticated
- Run `gh auth login` to authenticate if needed

## Common Operations

### Pull Requests

```bash
# Create a PR
gh pr create --title "Title" --body "Description"

# List PRs
gh pr list

# View PR details
gh pr view <number>

# Checkout a PR
gh pr checkout <number>

# Merge a PR
gh pr merge <number>
```

### Issues

```bash
# Create an issue
gh issue create --title "Title" --body "Description"

# List issues
gh issue list

# View issue details
gh issue view <number>

# Close an issue
gh issue close <number>
```

### Repository Operations

```bash
# View repository info
gh repo view

# Clone a repository
gh repo clone <owner>/<repo>

# Create a repository
gh repo create <name>

# Fork a repository
gh repo fork
```

### Releases

```bash
# List releases
gh release list

# View release details
gh release view <tag>

# Create a release
gh release create <tag> --title "Title" --notes "Release notes"
```

## Tips

- Use `--help` flag with any command to see all options
- Use `--json` flag for machine-readable output
- Use `-R <owner>/<repo>` to target a specific repository
- Check authentication status with `gh auth status`

## Error Handling

If `gh` is not authenticated:
1. Run `gh auth login`
2. Follow the authentication flow
3. Retry the operation

If command fails, check:
- Repository permissions
- Authentication status
- Internet connectivity

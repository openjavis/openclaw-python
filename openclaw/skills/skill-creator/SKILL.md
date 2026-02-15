---
name: skill-creator
description: "Create new OpenClaw skills with proper structure"
user-invocable: true
metadata:
  openclaw:
    emoji: "🛠️"
    always: true
---

# Skill Creator

Create new OpenClaw skills with proper structure and frontmatter.

## Skill Structure

A skill is a directory containing a `SKILL.md` file with YAML frontmatter:

```
skills/
  my-skill/
    SKILL.md
    helper.py (optional)
    README.md (optional)
```

## SKILL.md Format

```markdown
---
name: skill-name
description: "Brief description of what the skill does"
user-invocable: true
disable-model-invocation: false
metadata:
  openclaw:
    emoji: "🎯"
    homepage: "https://example.com"
    requires:
      bins: ["required-binary"]
      env: ["REQUIRED_ENV_VAR"]
    install:
      - kind: brew
        formula: package-name
        os: ["darwin", "linux"]
---

# Skill Title

Detailed skill documentation goes here...
```

## Frontmatter Fields

### Required

- `name`: Skill name (must match directory name, kebab-case)
- `description`: Brief description (used by model to decide when to use skill)

### Optional

- `user-invocable`: Can user invoke via /command (default: true)
- `disable-model-invocation`: Only invocable by user, not model (default: false)

### Metadata (metadata.openclaw)

- `emoji`: Emoji icon for skill
- `homepage`: Homepage URL
- `always`: Always include skill regardless of requirements (default: false)
- `skillKey`: Config key (default: skill name)
- `primaryEnv`: Primary environment variable name (e.g., "OPENAI_API_KEY")
- `os`: Supported operating systems (["darwin", "linux", "win32"])
- `requires`: Requirements object
  - `bins`: Required binaries (all must exist)
  - `anyBins`: Required binaries (at least one must exist)
  - `env`: Required environment variables
  - `config`: Required config paths (dot notation, e.g., "api.keys.openai")
- `install`: Installation specifications
  - `kind`: "brew" | "node" | "go" | "uv" | "download"
  - Platform-specific install instructions

## Creating a Skill

### Step 1: Create Directory

```bash
mkdir -p ~/.openclaw/skills/my-skill
cd ~/.openclaw/skills/my-skill
```

### Step 2: Create SKILL.md

```bash
cat > SKILL.md << 'EOF'
---
name: my-skill
description: "Description of my skill"
metadata:
  openclaw:
    emoji: "🎯"
    requires:
      bins: ["required-tool"]
---

# My Skill

Documentation here...
EOF
```

### Step 3: Test Skill

```bash
openclaw skills list
openclaw skills info my-skill
```

## Skill Content Guidelines

1. **Clear Instructions**: Provide step-by-step guidance
2. **Examples**: Include practical examples
3. **Prerequisites**: List requirements clearly
4. **Error Handling**: Explain common errors and solutions
5. **Tips**: Provide best practices and tips

## Example Skills

### Simple Skill (no requirements)

```markdown
---
name: greeting
description: "Generate friendly greetings"
metadata:
  openclaw:
    always: true
    emoji: "👋"
---

# Greeting Skill

Generate friendly, contextual greetings.

Use warm, welcoming language...
```

### Tool-Dependent Skill

```markdown
---
name: docker-ops
description: "Docker container operations"
metadata:
  openclaw:
    emoji: "🐳"
    requires:
      bins: ["docker"]
    install:
      - kind: brew
        formula: docker
        os: ["darwin"]
---

# Docker Operations

Manage Docker containers...
```

### API-Dependent Skill

```markdown
---
name: openai-advanced
description: "Advanced OpenAI API operations"
metadata:
  openclaw:
    emoji: "🤖"
    primaryEnv: "OPENAI_API_KEY"
    requires:
      env: ["OPENAI_API_KEY"]
---

# OpenAI Advanced

Advanced OpenAI API operations...
```

## Skill Precedence

Skills are loaded with precedence:

1. Extra dirs (lowest)
2. Plugin dirs
3. Bundled skills
4. Managed skills (`~/.openclaw/skills`)
5. Workspace skills (`.openclaw/skills`) (highest)

Later skills override earlier ones by name.

## Tips

- Use clear, descriptive names
- Write comprehensive documentation
- Include practical examples
- Test on multiple platforms if using OS-specific features
- Keep skills focused on a single domain
- Use requirements to ensure tool availability

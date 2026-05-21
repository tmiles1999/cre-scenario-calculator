# Agent config (one repo, three tools)

Single source of truth for AI instructions shared across **Cursor**, **Claude Code**, and **OpenCode**.

## Layout

```
agent/
├── AGENTS.md              # Main project guide (synced to repo root)
├── manifest.json          # Rule/skill registry for sync.py
├── sync.py                # Regenerate tool-specific files
├── rules/                 # Rule bodies (markdown only, no tool frontmatter)
│   ├── project-core.md
│   └── domain-percent-money.md
└── skills/                # Canonical skills (symlinked into each tool)
    └── sync-agent-config/
        └── SKILL.md
```

## Generated outputs (do not edit by hand)

| Output | Tool |
|--------|------|
| `AGENTS.md` (root) | OpenCode (native), Claude Code (`@` import), Cursor (convention) |
| `CLAUDE.md` | Claude Code entry point |
| `opencode.json` | OpenCode `instructions` list |
| `.cursor/rules/*.mdc` | Cursor rules (`alwaysApply` / `globs`) |
| `.claude/rules/*.md` | Claude Code rules (`paths` frontmatter when scoped) |
| `.cursor/skills/*` → `agent/skills/*` | Cursor project skills |
| `.claude/skills/*` → `agent/skills/*` | Claude Code project skills |

## Workflow

1. Edit sources under `agent/` only.
2. Run `python3 agent/sync.py`.
3. Commit both `agent/` changes and generated files so clones work without running sync.

Use skill **`sync-agent-config`** when adding rules, skills, or changing agent settings.

## Tool-specific (not synced)

| File | Tool | Purpose |
|------|------|---------|
| `.cursorignore` | Cursor | Index exclusions |
| `.claude/settings.json` | Claude Code | Permissions / local settings |
| `opencode.json` extras | OpenCode | Merge into `agent/opencode.extra.json` later if needed |

## Adding a rule

1. Create `agent/rules/my-rule.md` (body only).
2. Register in `agent/manifest.json`:

```json
{
  "id": "my-rule",
  "description": "Short picker description",
  "always": true
}
```

For path-scoped rules, omit `"always"` and add `"paths": ["src/**/*.py"]`.

3. Run `python3 agent/sync.py`.

## Adding a skill

1. Create `agent/skills/my-skill/SKILL.md`.
2. Add `"my-skill"` to `manifest.json` → `"skills"`.
3. Run `python3 agent/sync.py`.

OpenCode reads Claude-format skills from `~/.claude/skills/` by default; project skills in `.claude/skills/` apply when using Claude compatibility mode.

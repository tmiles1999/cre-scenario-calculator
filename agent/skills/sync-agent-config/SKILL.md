---
name: sync-agent-config
description: >-
  Keeps Cursor, Claude Code, and OpenCode agent config in sync. Use when editing
  AGENTS.md, rules, skills, CLAUDE.md, opencode.json, .cursor/rules, or
  .claude/rules; when adding agent instructions; or when the user asks to sync
  AI helper files across tools.
---

# Sync agent config (Cursor + Claude Code + OpenCode)

## Source of truth

| Edit here | Never edit directly |
|-----------|---------------------|
| `agent/AGENTS.md` | Root `AGENTS.md` |
| `agent/rules/*.md` | `.cursor/rules/*.mdc`, `.claude/rules/*.md` |
| `agent/skills/*/SKILL.md` | `.cursor/skills/*`, `.claude/skills/*` (symlinks) |
| `agent/manifest.json` | — |

Generated wrappers: `CLAUDE.md`, `opencode.json`.

## Sync command

After any change under `agent/`:

```bash
python3 agent/sync.py
```

Verify: no diff in rule **bodies** between `agent/rules/` and generated files (only frontmatter differs).

## Checklist (every agent-config change)

1. Edit canonical file under `agent/`.
2. Update `agent/manifest.json` if adding/removing rules or skills.
3. Run `python3 agent/sync.py`.
4. Commit `agent/` **and** generated outputs together.
5. Do not duplicate content across tools — one body, many wrappers.

## Add a shared rule

1. `agent/rules/<id>.md` — markdown body only (no YAML frontmatter).
2. Register in `manifest.json`:

```json
{
  "id": "<id>",
  "description": "Shown in Cursor rule picker",
  "always": true
}
```

Path-scoped (Cursor `globs`, Claude `paths`, OpenCode via `opencode.json`):

```json
{
  "id": "streamlit-gui",
  "description": "Streamlit widget keys and tab patterns",
  "paths": ["**/gui_*.py"]
}
```

3. `python3 agent/sync.py`

## Add a shared skill

1. `agent/skills/<name>/SKILL.md` with standard frontmatter (`name`, `description`).
2. Append `"<name>"` to `manifest.json` → `"skills"`.
3. `python3 agent/sync.py` (creates symlinks in `.cursor/skills/` and `.claude/skills/`).

## Tool-specific settings (stay local)

Do **not** sync these via `agent/sync.py`:

- `.cursorignore` — Cursor indexing only
- `.claude/settings.json` — Claude Code permissions
- Future OpenCode model/MCP settings — extend sync to merge `agent/opencode.extra.json` if needed

Document new tool-only settings in this skill's "Tool-specific" section.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Edited `.cursor/rules/*.mdc` by mistake | Copy body back to `agent/rules/`, run sync |
| Skill missing in Cursor/Claude | Check `manifest.json` skills list, run sync |
| OpenCode not loading rules | Confirm `opencode.json` lists `agent/rules/*.md` |
| Windows symlink errors | Run sync on WSL/Linux or copy skill dirs instead of symlinks |

## Reference

Full layout: `agent/README.md`

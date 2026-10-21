---
name: publish-template-change
description: Change how Claude Agent Exchange works at the source — the folder layout, the CLAUDE.md snippet, or apply.py in the project repo (danielrosehill/Claude-Agent-Exchange, template/) — bump the template version, commit and push, then apply locally with update-exchange. Use when the user wants to change the exchange ("add a folder to the exchange", "change the exchange rules in CLAUDE.md", "update the template"), or when a local tweak should become the standard.
---

# Publish a change to the exchange template

Never make layout or snippet changes only in the local folder or in `~/CLAUDE.md`.
The next update overwrites the managed parts. Personal preferences (location,
bookmarks) belong in `~/.config/claude-agent-exchange/config.json`, not the template.

## 1. Work in a real clone, not the cache

```bash
T=$(find ~ -maxdepth 6 -type d -name Claude-Agent-Exchange -path '*repos*' 2>/dev/null | head -1)
[ -n "$T" ] || { T="${TMPDIR:-/tmp}/claude-agent-exchange-dev"; gh repo clone danielrosehill/Claude-Agent-Exchange "$T"; }
git -C "$T" pull --ff-only
```

Don't edit `~/.cache/claude-agent-exchange/repo`. The update skills reset it with
`reset --hard`.

## 2. Edit `template/`

| Change | Where |
| --- | --- |
| Rules Claude follows | `CLAUDE-snippet.md`. Keep `## File exchange folder` as the first line. `{root}` is replaced with the user's folder |
| Add a dir | `template.json` → `dirs`, plus `Claude-Exchange/<dir>/.gitkeep` |
| Rename a dir | `template.json` → `dirs`, plus `"renamed": {"old": "new"}`. **Major** version bump. Update the skills and the explorer (`explorer/agent_exchange/app.py` constants) in the same commit |
| A file installed into the folder | the file under `Claude-Exchange/`, plus its entry in `managed_files` |
| How applying works | `apply.py`. Test with `--dry-run --root <tmpdir> --claude-md <tmp copy>` |

Bump `version` in `template/template.json` (semver). If the plugin's skills change, also
bump `version` in `.claude-plugin/plugin.json` and the plugin's entry in the
`danielrosehill/Claude-Code-Plugins` marketplace.

## 3. Ship and apply

```bash
git -C "$T" add -A && git -C "$T" commit -m "Template <version>: <what changed>" && git -C "$T" push
```

Then run `update-exchange` on this machine.

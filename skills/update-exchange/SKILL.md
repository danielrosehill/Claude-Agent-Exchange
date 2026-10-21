---
name: update-exchange
description: Bring this machine's Claude Agent Exchange up to date with the project repo — the folder layout, the ~/CLAUDE.md block and the explorer app. Compares the installed template version in <root>/.template.json with the repo's, shows what would change, then applies. Never touches user files. Use when the user says "update the exchange", "pull the template", "update the exchange explorer", after publish-template-change, or when the installed version is behind.
---

# Update Claude Agent Exchange

## 1. Fetch the latest project

```bash
REPO="${XDG_CACHE_HOME:-$HOME/.cache}/claude-agent-exchange/repo"
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" fetch -q origin && git -C "$REPO" reset -q --hard origin/main
else
  mkdir -p "$(dirname "$REPO")" && git clone -q https://github.com/danielrosehill/Claude-Agent-Exchange "$REPO"
fi
X=$(python3 -I "$REPO/template/apply.py" --print-root)
echo "installed: $(cat "$X/.template.json" 2>/dev/null || echo none)"
echo "template:  $(python3 -I -c "import json;print(json.load(open('$REPO/template/template.json'))['version'])") $(git -C "$REPO" rev-parse --short HEAD)"
```

If nothing is installed (no `$X/.template.json`), run `setup-exchange` instead.

## 2. Dry run, then apply

```bash
"$REPO/install.sh" --dry-run
"$REPO/install.sh"            # add --no-app on machines without the explorer
```

- If the dry run shows no `renamed_dirs`, `created_dirs` or `updated_files`, and
  `claude_md: unchanged`, the folder is current. Still run `install.sh` if the
  explorer code changed (check the git log since the installed `commit`).
- `renamed` in `template.json` is applied automatically, and only when the new name
  doesn't exist yet. `rename_conflicts` means both exist: propose merging and do it
  only once the user agrees.
- For a major version bump, read the git log since the installed `commit` before
  applying.
- `orphan_dirs` lists dirs the template doesn't know. Report them and leave them alone.

## 3. Report

Give the old version → new version, what changed, and any conflicts or orphans.

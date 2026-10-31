---
name: setup-exchange
description: Set up Claude Agent Exchange on this machine — the exchange folder (default ~/Desktop/Claude-Exchange with from-human/ and from-agent/), the marked ~/CLAUDE.md block that makes Claude use it unprompted, and the dedicated explorer app with its desktop launcher. Use on first use on a machine, or when the user says "set up the exchange folder", "install the agent exchange", "create the drop folder", or another agent-exchange skill finds the folder missing.
---

# Set up Claude Agent Exchange

The project repo (`danielrosehill/Claude-Agent-Exchange`) is the source of truth.
Its `template/` folder holds the layout (`template.json`), the CLAUDE.md snippet, and
a deterministic `apply.py`. `install.sh` installs the explorer and launcher, then
runs `apply.py`. Running it again is safe. On an existing install it does the same as
`update-exchange`.

## 1. Fetch the project

```bash
REPO="${XDG_CACHE_HOME:-$HOME/.cache}/claude-agent-exchange/repo"
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" fetch -q origin && git -C "$REPO" reset -q --hard origin/main   # cache only, never a dev clone
else
  mkdir -p "$(dirname "$REPO")" && git clone -q https://github.com/danielrosehill/Claude-Agent-Exchange "$REPO"
fi
git -C "$REPO" log --oneline -1
```

## 2. Personal settings (optional)

Settings live in `~/.config/claude-agent-exchange/config.json`, never in the repo:

```json
{ "root": "~/Desktop/Claude-Exchange", "bookmarks": [ { "name": "Downloads", "path": "~/Downloads" } ] }
```

`root` moves the exchange folder (`$CLAUDE_EXCHANGE_DIR` overrides it). `bookmarks`
are the extra sidebar entries in the explorer, which also edits this file from its
toolbar. Create the file only if the user wants a non-default location or named
bookmarks.

## 3. Install

```bash
"$REPO/install.sh" --dry-run    # report what apply.py would change; installs nothing
"$REPO/install.sh"              # explorer (uv tool, else pipx) + launcher + folder + CLAUDE.md block
"$REPO/install.sh" --no-app     # folder and CLAUDE.md block only (headless machines)
```

`apply.py` prints a JSON report: `renamed_dirs`, `created_dirs`, `updated_files`,
`claude_md` (`appended block` / `replaced block` /
`converted unmarked section to marked block` / `unchanged`), `orphan_dirs`, and
`template_version` and `previous_version`. It backs up `CLAUDE.md` to
`CLAUDE.md.bak-<timestamp>` before changing it.

If the block doesn't exist in CLAUDE.md yet, show the dry run first. Otherwise install
directly.

## 3a. Drive exchange (recommended)

The primary transport is a Google Shared Drive with three folders: `fe` (inbox, which
the user uploads to from the phone share sheet), `from-agent` (outbox) and, optionally,
a folder shared with one other person. The user creates the Shared Drive. The agent
creates the folders (with a Drive MCP or `rclone mkdir`) and records the IDs:

```json
{ "drive": { "drive_id": "0A...", "inbox_id": "1...", "outbox_id": "1...",
             "shared_id": "1...", "rclone_remote": "<rclone drive remote>" } }
```

in `~/.config/claude-agent-exchange/config.json` (or as `AGENT_EXCHANGE_*` env vars,
which take precedence). It needs an rclone Drive remote with access to that Shared
Drive. Check with `python3 -I "$REPO/scripts/exchange_drive.py" list inbox`. On the
phone, Drive's share sheet ("Save to Drive") remembers the last folder, so after the
first time a share is three taps.

## 4. Report

Report the apply output in a line or two, and tell the user the launcher is in the
application menu as **Claude Agent Exchange** (command: `claude-agent-exchange`).

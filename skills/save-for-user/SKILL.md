---
name: save-for-user
description: Local-folder mode only, when no Drive exchange is configured (otherwise use send-to-drive). Save a file for the user in the exchange folder's from-agent/ directory (default ~/Desktop/Claude-Exchange/from-agent) with a dated, descriptive name, and tell them the full path. Use when the user says "save that for me", "give me the file", "export it", "put it somewhere I can grab it", or when Claude produces a file for the user and no other destination was named. Not for files that belong in a repo or on Drive.
---

# Save a file for the user

> **Local-folder mode.** When a Drive exchange is configured (`exchange_drive.py config` shows an `inbox_id`), use `fetch-from-drive` / `send-to-drive` instead. This skill is for machines without Drive.

```bash
X=$(python3 -I -c 'import json,os;c=os.path.expanduser("~/.config/claude-agent-exchange/config.json");r=os.environ.get("CLAUDE_EXCHANGE_DIR") or (json.load(open(c)).get("root") if os.path.exists(c) else None) or "~/Desktop/Claude-Exchange";print(os.path.abspath(os.path.expanduser(r)))')
[ -d "$X/from-agent" ] || echo "missing: run setup-exchange"
```

If the folder is missing, run `setup-exchange` first. It's idempotent, so don't ask.

## Naming

`YYYY-MM-DD_<slug>.<ext>`, using today's local date. The slug says what the file *is*:
lowercase, words separated by hyphens, at most about 6 words. For example
`2026-10-21_gpg-public-key-commits.asc` or `2026-10-21_hf-repo-inventory.json`.

- Use the real format's extension, not `.txt` for everything.
- Never overwrite. If the name exists, add `-2`, `-3` and so on before the extension.
- Several related files go in one subfolder named the same way
  (`2026-10-21_rewrite-dry-run/`), not as loose files.

## Writing

- Text you generated: write it straight to the final path.
- An existing file elsewhere (scratchpad, `/tmp`, a build output): **copy** it, don't
  move it, unless the source is your own scratch file.
- Something only on a remote (S3, Drive, a URL): download it into place.

The explorer app shows the file in bold under **From Agent** until the user opens it.

## Tell the user

Give the absolute path in one piece, for example
`/home/<user>/Desktop/Claude-Exchange/from-agent/2026-10-21_hf-repo-inventory.json`,
plus one line on what it is. Don't paste the file's contents unless asked.

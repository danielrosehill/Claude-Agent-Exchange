---
name: send-to-drive
description: Leave a file for the user in the exchange Shared Drive's from-agent folder (or the optional shared folder) with a dated name, verify the upload and give them the link. Use when the user says "send it to my phone", "put it on the drive", "save it for me", "share it with us", or when Claude produces a file for the user and no other destination was named.
---

# Send a file to the Drive

```bash
S="${CLAUDE_PLUGIN_ROOT:-$HOME/.cache/claude-agent-exchange/repo}/scripts/exchange_drive.py"
python3 -I "$S" config
```

## Target

- `outbox` (`from-agent/`, the default): for the user.
- `shared`: only when the user asks to share with the other person on the shared folder.

## Naming

`YYYY-MM-DD_<slug>.<ext>`, using today's local date. The slug says what the file is:
lowercase, hyphenated, at most about 6 words. Use the real extension. `send` refuses an
existing name, so add `-2`, `-3` and so on. For several related files, zip them or send
each one with a shared prefix.

## Send

Write generated text to the scratchpad first, then:

```bash
python3 -I "$S" send "<local file>" --to outbox --name "YYYY-MM-DD_<slug>.<ext>"
```

`send` checks the uploaded size and returns the Drive link. Give the user the link plus
one line on what it is. Don't paste the contents unless asked.

The Drive is an intermediate space. Anything meant to be kept long-term belongs in its
permanent home, not in `from-agent/`.

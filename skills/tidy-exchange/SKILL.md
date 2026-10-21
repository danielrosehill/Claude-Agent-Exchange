---
name: tidy-exchange
description: Archive old files out of the Claude exchange folder (default ~/Desktop/Claude-Exchange) — anything in from-human/ or from-agent/ older than 14 days (or a given age) moves to archive/YYYY-MM/<side>/. Never deletes. Use when the user says "tidy the exchange", "clear out the drop folder", "archive old exchange files", or the folders have grown long.
---

# Tidy the exchange folder

Moves files and never deletes. Default age is 14 days by modification time. Use the
user's figure if they give one.

## 1. Plan

```bash
X=$(python3 -I -c 'import json,os;c=os.path.expanduser("~/.config/claude-agent-exchange/config.json");r=os.environ.get("CLAUDE_EXCHANGE_DIR") or (json.load(open(c)).get("root") if os.path.exists(c) else None) or "~/Desktop/Claude-Exchange";print(os.path.abspath(os.path.expanduser(r)))'); DAYS=14
for side in from-human from-agent; do
  find "$X/$side" -mindepth 1 -maxdepth 1 ! -name '.*' -mtime +$DAYS -printf "$side\t%TY-%Tm\t%f\n"
done
```

Show the list: count per side, plus names if there are fewer than about 20. If nothing
is old enough, say so and stop. Run it without asking when the user asked for a tidy.
Ask first when you're tidying on your own initiative.

## 2. Move

Each top-level entry (a file or a whole subfolder) goes to
`$X/archive/<YYYY-MM of its mtime>/<side>/<name>`. Create directories as needed. On a
name clash, add `-2`, `-3` and so on. Use `mv -n` and check afterwards that the source
is gone and the target exists.

Also remove moved items from the manifests so they don't grow without limit:
`from-human/.seen.json` (what the agent has read) and `from-agent/.opened.json` (what
the human has opened in the explorer).

## 3. Report

Give the number moved per side and where they went. The archive is never pruned by
this skill. If the user wants it cleared, that's an explicit delete they confirm.

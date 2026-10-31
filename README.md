# Claude Agent Exchange

A two-way file exchange between you and Claude Code on your own machine, with its own
small file explorer.

```
~/Desktop/Claude-Exchange/
├── from-human/    you put files here for the agent
├── from-agent/    the agent saves files here for you
└── archive/       older files, by month (created when first needed)
```

The project has three parts that ship together:

| Part | What it is |
| --- | --- |
| **Explorer** (`explorer/`) | A Qt app locked to the exchange folder. The sidebar has two fixed places, **From Human** and **From Agent**, then Archive, then your own bookmarks. You can browse inside a place but not above it. Drop files on the window to send them to the agent. Agent files you haven't opened are **bold**, and From Agent shows a count. Files the agent has read get a ✓. It never deletes: you can archive or move to Trash, with confirmation. |
| **Template** (`template/`) | The folder layout (`template.json`), the `CLAUDE.md` snippet, and `apply.py`, which installs and updates both deterministically. |
| **Claude Code plugin** (`skills/`) | `setup-exchange`, `update-exchange`, `publish-template-change`, `save-for-user`, `read-from-human`, `tidy-exchange`. |

## Install

As a Claude Code plugin:

```
/plugin marketplace add danielrosehill/Claude-Agent-Exchange
/plugin install agent-exchange@claude-agent-exchange
```

Then ask Claude to "set up the agent exchange".

Or without Claude:

```bash
git clone https://github.com/danielrosehill/Claude-Agent-Exchange
cd Claude-Agent-Exchange && ./install.sh        # --no-app for folder + CLAUDE.md only, --dry-run to preview
```

`install.sh` installs the explorer with `uv tool` (or `pipx`), adds the launcher
**Claude Agent Exchange** to your application menu, creates the folder, and adds a
marked block to `~/CLAUDE.md`. Requirements: Python 3.10+, uv or pipx, and a Linux
desktop that reads `~/.local/share/applications` (KDE, GNOME and others). The
explorer itself is plain PySide6 and should run on macOS and Windows too, but the
installer is Linux-only for now.

## Drive exchange (primary since 1.1.0)

The local folder needs you at the computer. The Drive exchange doesn't: you share a
file from your phone into a Google Shared Drive, tell Claude "I just shared it", and
Claude downloads it, checks it, and moves the Drive copy to the trash. The Drive is an
intermediate space, not storage.

| Folder | Direction | Skill |
| --- | --- | --- |
| `fe` (first entry) | you → Claude, unsorted, bind your phone shortcuts here | `fetch-from-drive` |
| `from-agent` | Claude → you | `send-to-drive` |
| shared (optional) | Claude → you and one other person | `send-to-drive --to shared` |

Folders are addressed by ID, from `AGENT_EXCHANGE_DRIVE_ID` / `_INBOX_ID` /
`_OUTBOX_ID` / `_SHARED_ID` / `_RCLONE_REMOTE`, or from the `drive` section of the
config file. `scripts/exchange_drive.py` does the transfer with rclone, because Drive
MCP servers often run on another host and can't write to your disk. Deleting always
means the Drive trash, never a permanent delete.

## Configure it for yourself

Personal settings live in `~/.config/claude-agent-exchange/config.json`, never in
this repo:

```json
{
  "root": "~/Desktop/Claude-Exchange",
  "bookmarks": [
    { "name": "Downloads", "path": "~/Downloads" },
    { "name": "Scans", "path": "~/Documents/Scans" }
  ]
}
```

- `root` moves the exchange folder. `$CLAUDE_EXCHANGE_DIR` overrides it, and so does
  `--root` on the command line. Every component (explorer, `apply.py`, skills) resolves
  it the same way: `--root`, then the env var, then config, then the default.
- `bookmarks` are extra sidebar places. The explorer adds, renames and removes them
  for you (toolbar → *Bookmark this folder* / *Add bookmark…*, or right-click a
  bookmark). Each bookmark is its own jail too.

## How the agent side works

The `CLAUDE.md` block (between `<!-- file-exchange:begin -->` and
`<!-- file-exchange:end -->`) tells Claude:

- "Save it for me" means `from-agent/`. Files are named `YYYY-MM-DD_<what-it-is>.<ext>`,
  nothing is ever overwritten, and Claude tells you the full path.
- "I put it in the folder" means `from-human/`. Claude uses the newest file it hasn't
  seen, and asks if it's ambiguous.
- Claude never moves, changes or deletes what you gave it.

Two small manifests keep both sides in sync. Both are hidden dotfiles that the
explorer doesn't show:

| File | Written by | Means |
| --- | --- | --- |
| `from-human/.seen.json` | the agent (`read-from-human`) | which of your files the agent has read, by SHA-256 |
| `from-agent/.opened.json` | the explorer | which agent files you've opened, by mtime |

## Updating

The template has its own semver in `template/template.json`, and the installed version
is recorded in `<root>/.template.json`. `update-exchange` (or re-running
`./install.sh`) applies a newer template. Renamed dirs (`renamed` in the manifest) are
moved automatically when that's safe. Nothing is ever deleted: dirs the template no
longer lists are reported as orphans.

To change the layout or rules, edit `template/` and bump its version. The
`publish-template-change` skill walks through it.

## Design decisions

- **A plain folder plus a focused view, not an enclave.** Claude Code runs as your
  user, so a container or encrypted mount wouldn't contain it. It would just make
  dropping files in harder. The explorer narrows what *you* see so the exchange
  doesn't get lost in your home directory. It doesn't restrict the agent.
- **User-level, not per-project.** One folder serves every Claude session in every
  repo.
- **Direction is a folder.** It's obvious in any file manager, with or without the app.
- **Skills are self-contained shell.** They work whether the plugin is installed or
  read from elsewhere with `${CLAUDE_PLUGIN_ROOT}` unset. The only code they run is
  this repo's `template/apply.py` and `install.sh`, fetched into
  `~/.cache/claude-agent-exchange/repo`.

## Prior art

The folder pattern itself isn't new:

- A per-workspace `_inbox/` / `_outbox/` with a CLAUDE.md line, plus a small drop
  window that copies files in and flags new output, in
  [6 Claude Code workflows that have nothing to do with code](https://pub.towardsai.net/6-claude-code-workflows-that-have-nothing-to-do-with-code-937d1d327848).
- Patrick McKenzie's watched inbox folder that Claude Code files and renames
  ([digg](https://digg.com/tech/lh7sjft8)).
- Agent-to-agent mailboxes such as
  [CodexPigeon](https://dev.to/ademisler/why-i-built-a-mailbox-instead-of-injecting-messages-into-a-running-ai-agent-4l6c)
  and [agent-inbox](https://pypi.org/project/agent-inbox/) solve a different problem:
  messages between agents.

This project packages the pattern at user level. It adds a jailed explorer with read
receipts in both directions, a versioned template that updates the folder and
`CLAUDE.md` deterministically, and agent skills that follow the same rules.

## License

MIT

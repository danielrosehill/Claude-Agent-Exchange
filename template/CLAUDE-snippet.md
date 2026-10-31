## File exchange (Google Shared Drive)

The exchange between us is a Google Shared Drive, so I can drop files from my phone
without the computer being on. Folder IDs come from `AGENT_EXCHANGE_*` env vars or the
`drive` section of `~/.config/claude-agent-exchange/config.json`.

- **`fe/` (first entry)** is where I upload, usually via the phone share sheet. It's
  unsorted. "I just shared it", "it's in fe" or "check the drive" means: take the newest
  file there (ask if several are new and it's unclear), download it into the task's
  working location, then trash the Drive copy. Skill `fetch-from-drive`.
- **`from-agent/`** is where you leave files for me. Name them `YYYY-MM-DD_<what-it-is>.<ext>`,
  never overwrite, and give me the link. Skill `send-to-drive`.
- **The shared folder** (`shared_id`, if configured) is a second target for things meant
  for me and the person it's shared with. Send there only when asked.
- The Drive is an intermediate space, not storage. Once a file has been used, or filed
  in its permanent home, it doesn't stay here. Deleting means Drive trash (30-day
  recovery), never a permanent delete.

Skills: plugin `agent-exchange` (`fetch-from-drive`, `send-to-drive`; local-folder
skills `read-from-human`, `save-for-user` only when no Drive is configured).

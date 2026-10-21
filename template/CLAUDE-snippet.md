## File exchange folder

`{root}/` is the drop folder between us. `from-human/` is what I put in for you, and
`from-agent/` is where you save files for me.

- "Save it for me" with no other destination means `from-agent/`. Name files
  `YYYY-MM-DD_<what-it-is>.<ext>`, never overwrite, and tell me the full path.
- "I put it in the folder" means `from-human/`. Use the newest file you haven't seen.
  If several are new, ask which one.
- Never move, change or delete anything in `from-human/`, and never delete from either side.
  Old files go to `archive/YYYY-MM/` only when I ask for a tidy.

Skills: plugin `agent-exchange` (`save-for-user`, `read-from-human`, `tidy-exchange`,
`update-exchange`).

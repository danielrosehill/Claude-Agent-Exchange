#!/usr/bin/env python3
"""Install or update the agent exchange folder from this template.

    python3 -I apply.py [--root DIR] [--claude-md FILE] [--dry-run]
    python3 -I apply.py --print-root

Root resolution, first match wins: --root, $CLAUDE_EXCHANGE_DIR, "root" in
~/.config/claude-agent-exchange/config.json, then ~/Desktop/Claude-Exchange.

Touches only what template.json declares. It renames dirs listed in `renamed` (only
when the new name doesn't exist yet), creates `dirs`, overwrites `managed_files`,
replaces the marked block in CLAUDE.md, and writes <root>/.template.json. It never
deletes anything, and prints a JSON report on stdout.
"""
import argparse, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def expand(p):
    return os.path.abspath(os.path.expanduser(p))


def tilde(p):
    h = os.path.expanduser("~")
    return "~" + p[len(h):] if p == h or p.startswith(h + os.sep) else p


def resolve_root(t, cli=None):
    if cli:
        return expand(cli)
    if os.environ.get(t["root_env"]):
        return expand(os.environ[t["root_env"]])
    cfg = expand(t["config"])
    if os.path.exists(cfg):
        r = json.load(open(cfg)).get("root")
        if r:
            return expand(r)
    return expand(t["root_default"])


def main():
    t = json.load(open(os.path.join(HERE, "template.json")))
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--claude-md", default=t["claude_md"]["target"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print-root", action="store_true")
    a = ap.parse_args()
    root = resolve_root(t, a.root)
    if a.print_root:
        print(root)
        return
    cmd, dry = expand(a.claude_md), a.dry_run
    rep = {"root": root, "template_version": t["version"], "dry_run": dry, "renamed_dirs": [],
           "created_dirs": [], "updated_files": [], "unchanged_files": [],
           "claude_md": None, "orphan_dirs": [], "rename_conflicts": []}
    try:
        commit = subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip() or None
    except OSError:
        commit = None
    rep["template_commit"] = commit

    prev_path = os.path.join(root, ".template.json")
    rep["previous_version"] = json.load(open(prev_path)).get("version") if os.path.exists(prev_path) else None

    pending = set()  # rename targets that a dry run would create by renaming
    for old, new in t.get("renamed", {}).items():
        o, n = os.path.join(root, old), os.path.join(root, new)
        if os.path.isdir(o):
            if os.path.exists(n):
                rep["rename_conflicts"].append(f"{old} -> {new}: both exist, merge by hand")
            else:
                rep["renamed_dirs"].append(f"{old} -> {new}")
                pending.add(new)
                if not dry:
                    os.rename(o, n)

    for d in t["dirs"]:
        p = os.path.join(root, d)
        if not os.path.isdir(p) and d not in pending:
            rep["created_dirs"].append(d)
            if not dry:
                os.makedirs(p)

    for src, dst in t["managed_files"].items():
        s, d = os.path.join(HERE, src), os.path.join(root, dst)
        new = open(s, "rb").read()
        if os.path.exists(d) and open(d, "rb").read() == new:
            rep["unchanged_files"].append(dst)
        else:
            rep["updated_files"].append(dst)
            if not dry:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                open(d, "wb").write(new)

    c = t["claude_md"]
    snippet = open(os.path.join(HERE, c["source"])).read().rstrip("\n").replace("{root}", tilde(root))
    block = c["begin"] + "\n" + snippet + "\n" + c["end"]
    text = open(cmd).read() if os.path.exists(cmd) else ""
    pat = re.compile(re.escape(c["begin"]) + r".*?" + re.escape(c["end"]), re.S)
    heading = snippet.split("\n")[0]  # e.g. "## File exchange folder"
    if pat.search(text):
        new_text = pat.sub(lambda m: block, text, count=1)
        rep["claude_md"] = "unchanged" if new_text == text else "replaced block"
    elif heading in text:
        # unmarked section from before markers existed: replace heading .. next "## " heading
        i = text.index(heading)
        j = text.find("\n## ", i + len(heading))
        j = len(text) if j == -1 else j + 1
        new_text = text[:i] + block + "\n\n" + text[j:].lstrip("\n")
        rep["claude_md"] = "converted unmarked section to marked block"
    else:
        new_text = text.rstrip("\n") + "\n\n" + block + "\n"
        rep["claude_md"] = "appended block"
    if new_text != text and not dry:
        if os.path.exists(cmd):
            shutil.copy2(cmd, cmd + ".bak-" + time.strftime("%Y%m%d%H%M%S"))
        open(cmd, "w").write(new_text)
    rep["claude_md_path"] = cmd

    if os.path.isdir(root):
        known = set(t["dirs"]) | {"archive"} | (set(t.get("renamed", {})) if dry else set())
        rep["orphan_dirs"] = sorted(e for e in os.listdir(root)
                                    if os.path.isdir(os.path.join(root, e)) and not e.startswith(".") and e not in known)

    if not dry:
        json.dump({"version": t["version"], "commit": commit,
                   "applied": time.strftime("%Y-%m-%dT%H:%M:%S")}, open(prev_path, "w"), indent=1)
    json.dump(rep, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()

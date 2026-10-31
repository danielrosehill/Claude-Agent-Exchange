#!/usr/bin/env python3
"""Google Drive transport for the agent exchange. Stdlib + rclone only.

The exchange lives in a Google Shared Drive with three folders, addressed by ID:

  inbox   ("fe", first entry)  what the human uploads, usually from a phone share sheet
  outbox  ("from-agent")       files the agent leaves for the human
  shared  (optional)           a second target shared with another person

Configuration, first match wins per key:
  env  AGENT_EXCHANGE_DRIVE_ID, AGENT_EXCHANGE_INBOX_ID, AGENT_EXCHANGE_OUTBOX_ID,
       AGENT_EXCHANGE_SHARED_ID, AGENT_EXCHANGE_RCLONE_REMOTE
  file ~/.config/claude-agent-exchange/config.json -> "drive": {drive_id, inbox_id,
       outbox_id, shared_id, rclone_remote}

rclone does the byte transfer because Drive MCP servers usually run elsewhere and
cannot write to this machine's disk. Deletion is rclone's default for Drive: the
file goes to the Drive trash (recoverable for 30 days), never a permanent delete.

  exchange_drive.py config
  exchange_drive.py list   [inbox|outbox|shared]
  exchange_drive.py fetch  <name|--newest> <dest_dir> [--from inbox] [--keep]
  exchange_drive.py send   <local_file> [--to outbox|shared] [--name NAME]
  exchange_drive.py trash  <name> [--from inbox]

Output is JSON on stdout.
"""
import json, os, subprocess, sys, hashlib

CFG = os.path.expanduser("~/.config/claude-agent-exchange/config.json")
KEYS = ["drive_id", "inbox_id", "outbox_id", "shared_id", "rclone_remote"]


def config():
    f = {}
    if os.path.exists(CFG):
        f = json.load(open(CFG)).get("drive", {}) or {}
    c = {k: os.environ.get("AGENT_EXCHANGE_" + k.upper()) or f.get(k) for k in KEYS}
    c["rclone_remote"] = (c["rclone_remote"] or "gdrive").rstrip(":")
    return c


def die(msg, **kw):
    print(json.dumps({"ok": False, "error": msg, **kw}))
    sys.exit(1)


def rc(c, folder, *args):
    fid = c.get(folder + "_id")
    if not fid:
        die(f"{folder}_id not configured", hint="set AGENT_EXCHANGE_%s_ID or drive.%s_id in %s"
            % (folder.upper(), folder, CFG))
    base = ["rclone"]
    if c.get("drive_id"):
        base.append("--drive-team-drive=" + c["drive_id"])
    base.append("--drive-root-folder-id=" + fid)
    r = subprocess.run(base + list(args), capture_output=True, text=True)
    if r.returncode:
        die("rclone failed", stderr=r.stderr.strip()[-800:])
    return r.stdout


def remote(c, path=""):
    return c["rclone_remote"] + ":" + path


def listing(c, folder):
    items = json.loads(rc(c, folder, "lsjson", "--files-only", remote(c)) or "[]")
    items = [{"name": i["Name"], "bytes": i["Size"], "modified": i["ModTime"],
              "mime": i.get("MimeType"), "id": i.get("ID")} for i in items]
    return sorted(items, key=lambda i: i["modified"], reverse=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def opt(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


def main():
    a = sys.argv[1:]
    if not a:
        die("usage: see module docstring")
    cmd, a = a[0], a[1:]
    c = config()
    if cmd == "config":
        print(json.dumps({"ok": True, **c, "config_file": CFG}, indent=1))
    elif cmd == "list":
        folder = a[0] if a else "inbox"
        print(json.dumps({"ok": True, "folder": folder, "files": listing(c, folder)}, indent=1))
    elif cmd == "fetch":
        keep = "--keep" in a
        a = [x for x in a if x != "--keep"]
        folder = opt(a, "--from", "inbox")
        if len(a) != 2:
            die("fetch <name|--newest> <dest_dir>")
        name, dest = a
        files = listing(c, folder)
        if not files:
            die("folder is empty", folder=folder)
        if name == "--newest":
            f = files[0]
        else:
            f = next((x for x in files if x["name"] == name), None) or die("not found", name=name)
        os.makedirs(dest, exist_ok=True)
        local = os.path.join(dest, f["name"])
        if os.path.exists(local):
            die("destination exists; refusing to overwrite", path=local)
        rc(c, folder, "copy", remote(c, f["name"]), dest)
        size = os.path.getsize(local) if os.path.exists(local) else -1
        if size != f["bytes"]:
            die("size mismatch after download; remote copy left in place",
                expected=f["bytes"], got=size, path=local)
        trashed = False
        if not keep:
            rc(c, folder, "deletefile", remote(c, f["name"]))
            trashed = True
        print(json.dumps({"ok": True, "file": f["name"], "path": os.path.abspath(local),
                          "bytes": size, "sha256": sha(local), "trashed_remote": trashed,
                          "others_in_folder": len(files) - 1}, indent=1))
    elif cmd == "send":
        folder = opt(a, "--to", "outbox")
        name = opt(a, "--name")
        if len(a) != 1 or not os.path.isfile(a[0]):
            die("send <local_file>")
        src = a[0]
        name = name or os.path.basename(src)
        existing = {x["name"] for x in listing(c, folder)}
        if name in existing:
            die("name already exists in " + folder + "; pick another", name=name)
        rc(c, folder, "copyto", src, remote(c, name))
        got = next((x for x in listing(c, folder) if x["name"] == name), None)
        if not got or got["bytes"] != os.path.getsize(src):
            die("upload not verified", name=name)
        link = "https://drive.google.com/file/d/%s/view" % got["id"] if got.get("id") else None
        print(json.dumps({"ok": True, "folder": folder, "name": name, "bytes": got["bytes"],
                          "link": link}, indent=1))
    elif cmd == "trash":
        folder = opt(a, "--from", "inbox")
        if len(a) != 1:
            die("trash <name>")
        rc(c, folder, "deletefile", remote(c, a[0]))
        print(json.dumps({"ok": True, "trashed": a[0], "folder": folder}))
    else:
        die("unknown command " + cmd)


if __name__ == "__main__":
    main()

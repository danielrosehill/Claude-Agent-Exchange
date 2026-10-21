"""Claude Agent Exchange: a small file explorer locked to the agent exchange folder.

The sidebar holds two fixed places, From Human and From Agent, then Archive when it
exists, then the user's own bookmarks. Each place is a jail: you can browse inside it
but not above it. Files dropped on the window are copied into From Human. Files the
agent left that you haven't opened yet show in bold, and From Human shows which of
your files the agent has read.
"""
import argparse, json, os, shutil, sys, time

from PySide6.QtCore import QDir, QFileSystemWatcher, QModelIndex, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QFileSystemModel, QHBoxLayout, QInputDialog,
    QLabel, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QSplitter,
    QToolBar, QTreeView, QVBoxLayout, QWidget,
)

CONFIG = os.path.expanduser("~/.config/claude-agent-exchange/config.json")
DEFAULT_ROOT = "~/Desktop/Claude-Exchange"
HUMAN, AGENT, ARCHIVE = "from-human", "from-agent", "archive"
SEEN = ".seen.json"      # in from-human/, written by the agent's read-from-human skill
OPENED = ".opened.json"  # in from-agent/, written by this app when you open a file
ROLE_PATH = Qt.UserRole + 1


def expand(p):
    return os.path.abspath(os.path.expanduser(p))


def load_config():
    try:
        return json.load(open(CONFIG))
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    tmp = CONFIG + ".tmp"
    json.dump(cfg, open(tmp, "w"), indent=2)
    os.replace(tmp, CONFIG)


def resolve_root(cli=None):
    return expand(cli or os.environ.get("CLAUDE_EXCHANGE_DIR") or load_config().get("root") or DEFAULT_ROOT)


def read_json(p):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return {}


def inside(path, jail):
    path, jail = os.path.realpath(path), os.path.realpath(jail)
    return path == jail or path.startswith(jail + os.sep)


def unique_dest(d, name):
    base, ext = os.path.splitext(name)
    cand, n = os.path.join(d, name), 2
    while os.path.exists(cand):
        cand, n = os.path.join(d, f"{base}-{n}{ext}"), n + 1
    return cand


class ExchangeModel(QFileSystemModel):
    """QFileSystemModel that knows which agent files are new and which human files the agent has read."""

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.human, self.agent = os.path.join(root, HUMAN), os.path.join(root, AGENT)
        self.reload_state()

    def reload_state(self):
        self.seen = read_json(os.path.join(self.human, SEEN))
        self.opened = read_json(os.path.join(self.agent, OPENED))

    def is_new_from_agent(self, path):
        if not os.path.isfile(path) or not inside(path, self.agent):
            return False
        rec = self.opened.get(os.path.relpath(path, self.agent))
        return not rec or rec.get("mtime") != int(os.path.getmtime(path))

    def agent_has_seen(self, path):
        return os.path.isfile(path) and inside(path, self.human) and os.path.relpath(path, self.human) in self.seen

    def data(self, index, role=Qt.DisplayRole):
        if index.column() == 0 and role in (Qt.FontRole, Qt.ToolTipRole, Qt.DisplayRole):
            path = self.filePath(index)
            if role == Qt.FontRole and self.is_new_from_agent(path):
                f = QFont(); f.setBold(True); return f
            if role == Qt.DisplayRole and self.agent_has_seen(path):
                return super().data(index, role) + "  ✓"
            if role == Qt.ToolTipRole:
                if self.is_new_from_agent(path):
                    return "New from the agent: you haven't opened it yet"
                if self.agent_has_seen(path):
                    return "The agent has read this file"
        return super().data(index, role)

    def mark_opened(self, path):
        if not inside(path, self.agent) or not os.path.isfile(path):
            return
        p = os.path.join(self.agent, OPENED)
        d = read_json(p)
        d[os.path.relpath(path, self.agent)] = {"mtime": int(os.path.getmtime(path)),
                                                "opened": time.strftime("%Y-%m-%dT%H:%M:%S")}
        json.dump(d, open(p, "w"), indent=1)
        self.reload_state()


class Explorer(QMainWindow):
    def __init__(self, root):
        super().__init__()
        self.root = root
        for d in (HUMAN, AGENT):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        self.cfg = load_config()
        self.setWindowTitle("Claude Agent Exchange")
        self.setWindowIcon(QIcon.fromTheme("claude-agent-exchange", QIcon.fromTheme("folder-cloud")))
        self.resize(980, 600)
        self.setAcceptDrops(True)
        self.jail = os.path.join(root, AGENT)

        self.model = ExchangeModel(root)
        self.model.setRootPath(root)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)  # hides dotfiles, incl. the manifests
        self.model.setReadOnly(True)

        self.places = QListWidget()
        self.places.setMaximumWidth(240)
        self.places.currentItemChanged.connect(self.on_place)
        self.places.setContextMenuPolicy(Qt.CustomContextMenu)
        self.places.customContextMenuRequested.connect(self.place_menu)

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(3, Qt.DescendingOrder)  # newest first
        self.view.setColumnWidth(0, 420)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setDragEnabled(True)
        self.view.setDragDropMode(QAbstractItemView.DragOnly)
        self.view.doubleClicked.connect(self.activate)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.file_menu)

        self.crumb = QLabel()
        self.hint = QLabel("Drop files anywhere on this window to send them to the agent (From Human).")
        self.hint.setStyleSheet("color: gray")
        right = QWidget(); rl = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self.crumb); rl.addWidget(self.view); rl.addWidget(self.hint)
        split = QSplitter(); split.addWidget(self.places); split.addWidget(right); split.setStretchFactor(1, 1)
        self.setCentralWidget(split)

        tb = QToolBar(); tb.setMovable(False); self.addToolBar(tb)
        self.up_act = self.act(tb, "go-up", "Up", self.go_up, QKeySequence("Alt+Up"))
        self.act(tb, "document-send", "Send files to agent…", self.send_dialog)
        self.act(tb, "bookmark-new", "Bookmark this folder", self.add_bookmark_here)
        self.act(tb, "folder-add", "Add bookmark…", self.add_bookmark_dialog)
        self.act(tb, "system-file-manager", "Open in file manager", lambda: self.reveal(self.current_dir()))

        self.watch = QFileSystemWatcher()
        self.watch.fileChanged.connect(self.state_changed)
        self.watch.directoryChanged.connect(self.state_changed)
        self.timer = QTimer(self, interval=3000, timeout=self.refresh_counts); self.timer.start()

        self.build_places()
        self.places.setCurrentRow(1 if self.model_new_count() else 0)

    # ---- helpers
    def act(self, tb, icon, text, slot, key=None):
        a = QAction(QIcon.fromTheme(icon), text, self); a.triggered.connect(slot)
        if key: a.setShortcut(key)
        tb.addAction(a); return a

    def current_dir(self):
        return self.model.filePath(self.view.rootIndex()) or self.jail

    def selected_paths(self):
        return [self.model.filePath(i) for i in self.view.selectionModel().selectedRows(0)]

    def model_new_count(self):
        a = os.path.join(self.root, AGENT)
        try:
            return sum(self.model.is_new_from_agent(os.path.join(a, n)) for n in os.listdir(a) if not n.startswith("."))
        except OSError:
            return 0

    # ---- places
    def build_places(self):
        self.places.blockSignals(True)
        cur = self.places.currentItem().data(ROLE_PATH) if self.places.currentItem() else None
        self.places.clear()

        def add(label, path, icon, fixed):
            it = QListWidgetItem(QIcon.fromTheme(icon), label)
            it.setData(ROLE_PATH, path); it.setData(ROLE_PATH + 1, fixed)
            self.places.addItem(it); return it

        add("From Human", os.path.join(self.root, HUMAN), "folder-upload", True)
        n = self.model_new_count()
        add(f"From Agent ({n} new)" if n else "From Agent", os.path.join(self.root, AGENT), "folder-download", True)
        if os.path.isdir(os.path.join(self.root, ARCHIVE)):
            add("Archive", os.path.join(self.root, ARCHIVE), "folder-tar", True)
        bms = self.cfg.get("bookmarks", [])
        if bms:
            sep = QListWidgetItem("Bookmarks"); sep.setFlags(Qt.NoItemFlags)
            f = QFont(); f.setBold(True); sep.setFont(f); self.places.addItem(sep)
            for b in bms:
                p = expand(b["path"])
                it = add(b.get("name") or os.path.basename(p), p, "folder-bookmark", False)
                if not os.path.isdir(p):
                    it.setForeground(Qt.gray); it.setToolTip("Missing: " + p)
        for d in (os.path.join(self.root, HUMAN), os.path.join(self.root, AGENT)):
            self.watch.addPath(d)
            for m in (SEEN, OPENED):
                if os.path.exists(os.path.join(d, m)):
                    self.watch.addPath(os.path.join(d, m))
        if cur:
            for i in range(self.places.count()):
                if self.places.item(i).data(ROLE_PATH) == cur:
                    self.places.setCurrentRow(i)
        self.places.blockSignals(False)

    def on_place(self, item, _prev=None):
        if not item or not item.data(ROLE_PATH):
            return
        path = item.data(ROLE_PATH)
        if not os.path.isdir(path):
            self.statusBar().showMessage("Bookmark target is missing: " + path, 5000); return
        self.jail = path
        self.model.setRootPath(path)
        self.set_dir(path)

    def set_dir(self, path):
        self.view.setRootIndex(self.model.index(path))
        rel = os.path.relpath(path, self.jail)
        name = self.places.currentItem().text() if self.places.currentItem() else ""
        self.crumb.setText(f"<b>{name.split(' (')[0]}</b>" + ("" if rel == "." else " / " + rel.replace(os.sep, " / ")))
        self.up_act.setEnabled(os.path.realpath(path) != os.path.realpath(self.jail))

    def go_up(self):
        cur = self.current_dir()
        if os.path.realpath(cur) != os.path.realpath(self.jail):
            self.set_dir(os.path.dirname(cur))

    def place_menu(self, pos):
        it = self.places.itemAt(pos)
        if not it or it.data(ROLE_PATH + 1) or not it.data(ROLE_PATH):
            return
        m = QMenu(self)
        m.addAction("Rename bookmark…", lambda: self.rename_bookmark(it.data(ROLE_PATH)))
        m.addAction("Remove bookmark", lambda: self.remove_bookmark(it.data(ROLE_PATH)))
        m.exec(self.places.mapToGlobal(pos))

    # ---- bookmarks (persisted in the user's config, never in the project)
    def add_bookmark(self, path, name=None):
        bms = self.cfg.setdefault("bookmarks", [])
        if any(expand(b["path"]) == path for b in bms):
            return
        bms.append({"name": name or os.path.basename(path.rstrip(os.sep)) or path, "path": path})
        save_config(self.cfg); self.build_places()

    def add_bookmark_here(self):
        self.add_bookmark(self.current_dir())

    def add_bookmark_dialog(self):
        d = QFileDialog.getExistingDirectory(self, "Add bookmark", os.path.expanduser("~"))
        if d:
            self.add_bookmark(d)

    def rename_bookmark(self, path):
        for b in self.cfg.get("bookmarks", []):
            if expand(b["path"]) == path:
                name, ok = QInputDialog.getText(self, "Rename bookmark", "Name:", text=b.get("name", ""))
                if ok and name:
                    b["name"] = name; save_config(self.cfg); self.build_places()

    def remove_bookmark(self, path):
        self.cfg["bookmarks"] = [b for b in self.cfg.get("bookmarks", []) if expand(b["path"]) != path]
        save_config(self.cfg); self.places.setCurrentRow(0); self.build_places()

    # ---- files
    def activate(self, index: QModelIndex):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            if inside(path, self.jail):
                self.set_dir(path)
            else:
                self.statusBar().showMessage("That link leads outside this place", 4000)
        else:
            self.open_file(path)

    def open_file(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        self.model.mark_opened(path)
        self.view.viewport().update(); self.refresh_counts()

    def reveal(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path if os.path.isdir(path) else os.path.dirname(path)))

    def send_to_agent(self, paths):
        dest = os.path.join(self.root, HUMAN); sent = []
        for p in paths:
            if inside(p, dest):
                continue
            t = unique_dest(dest, os.path.basename(p.rstrip(os.sep)))
            (shutil.copytree if os.path.isdir(p) else shutil.copy2)(p, t)
            sent.append(os.path.basename(t))
        if sent:
            self.statusBar().showMessage(f"Sent to agent: {', '.join(sent)}", 6000)

    def send_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Send files to the agent", os.path.expanduser("~"))
        self.send_to_agent(files)

    def archive(self, paths):
        month = time.strftime("%Y-%m")
        for p in paths:
            side = HUMAN if inside(p, os.path.join(self.root, HUMAN)) else AGENT
            d = os.path.join(self.root, ARCHIVE, month, side); os.makedirs(d, exist_ok=True)
            shutil.move(p, unique_dest(d, os.path.basename(p)))
        self.build_places()

    def trash(self, paths):
        names = "\n".join(os.path.basename(p) for p in paths)
        if QMessageBox.question(self, "Move to Trash", f"Move to Trash?\n\n{names}") == QMessageBox.Yes:
            from PySide6.QtCore import QFile
            for p in paths:
                QFile.moveToTrash(p)

    def file_menu(self, pos):
        paths = self.selected_paths()
        if not paths:
            return
        m = QMenu(self)
        if len(paths) == 1:
            m.addAction(QIcon.fromTheme("document-open"), "Open", lambda: self.activate(self.view.indexAt(pos)))
            m.addAction(QIcon.fromTheme("edit-copy"), "Copy path",
                        lambda: QGuiApplication.clipboard().setText(paths[0]))
            m.addAction(QIcon.fromTheme("system-file-manager"), "Show in file manager", lambda: self.reveal(paths[0]))
        if not all(inside(p, os.path.join(self.root, HUMAN)) for p in paths):
            m.addAction(QIcon.fromTheme("document-send"), "Send to agent", lambda: self.send_to_agent(paths))
        sides = (os.path.join(self.root, HUMAN), os.path.join(self.root, AGENT))
        if all(os.path.dirname(p) in sides for p in paths):
            m.addAction(QIcon.fromTheme("folder-tar"), "Move to archive", lambda: self.archive(paths))
        m.addSeparator()
        m.addAction(QIcon.fromTheme("user-trash"), "Move to Trash…", lambda: self.trash(paths))
        m.exec(self.view.viewport().mapToGlobal(pos))

    # ---- drag and drop: everything dropped goes to From Human
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.send_to_agent([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    # ---- live state
    def state_changed(self, *_):
        self.model.reload_state(); self.view.viewport().update(); self.refresh_counts()

    def refresh_counts(self):
        self.model.reload_state()
        n = self.model_new_count()
        for i in range(self.places.count()):
            it = self.places.item(i)
            if it.data(ROLE_PATH) == os.path.join(self.root, AGENT):
                it.setText(f"From Agent ({n} new)" if n else "From Agent")
        self.view.viewport().update()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="claude-agent-exchange", description=__doc__.split("\n")[0])
    ap.add_argument("--root", help="exchange folder (default: $CLAUDE_EXCHANGE_DIR, config root, ~/Desktop/Claude-Exchange)")
    ap.add_argument("--print-root", action="store_true", help="print the resolved exchange folder and exit")
    a, qt_args = ap.parse_known_args(argv)
    root = resolve_root(a.root)
    if a.print_root:
        print(root); return 0
    app = QApplication([sys.argv[0]] + qt_args)
    app.setApplicationName("Claude Agent Exchange")
    app.setDesktopFileName("claude-agent-exchange")
    w = Explorer(root); w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

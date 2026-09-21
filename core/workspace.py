"""Session-owned repository workspaces."""
import shutil
import tempfile
from pathlib import Path


def workspace_base():
    return Path(tempfile.gettempdir()).resolve() / "neurotrace_workspaces"


def persist_workspace(source):
    base = workspace_base()
    base.mkdir(parents=True, exist_ok=True)
    target = Path(tempfile.mkdtemp(prefix="scan_", dir=base))
    try:
        shutil.copytree(source, target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".codedoctor_backups"))
    except Exception:
        cleanup_workspace(target)
        raise
    return str(target)


def cleanup_workspace(path):
    target = Path(path).resolve()
    # Only direct, session-specific children of our managed directory are owned.
    if target.parent != workspace_base() or not target.name.startswith("scan_"):
        raise ValueError("Refusing to remove a directory outside the managed workspace.")
    if target.exists():
        shutil.rmtree(target)

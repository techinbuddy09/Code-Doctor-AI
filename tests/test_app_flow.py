"""Exercise real Streamlit reruns with a local repository fixture (no API calls)."""
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest
from core.repository import Repository
from config import Config


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception


def test_scan_fix_report_revert_and_reset(tmp_path, monkeypatch):
    (tmp_path / "sample.py").write_text('TOKEN = "fakecredential123"\n')
    monkeypatch.setattr(Config, "_secrets_loaded", True)
    for key in ("AI_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setattr(Config, key, "")
    monkeypatch.setattr(Repository, "fetch", lambda *a, **k: Repository(tmp_path, "test", "repo", "main"))
    at = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=30).run()
    assert not at.exception
    at.text_input(key="repo_url_input").set_value("https://github.com/test/repo")
    click(at, "🚀 Start Analysis")
    assert at.session_state["stage"] == "dashboard"
    workspace = Path(at.session_state["repo_path"])
    assert at.session_state["test_result"] is None
    click(at, "🐛 View Issues")
    at.text_input(key="issue_search").set_value("does-not-match-any-finding").run()
    assert not at.exception
    assert not any(b.label == "🛠️ Apply Suggested Fix" for b in at.button)
    at.text_input(key="issue_search").set_value("sample.py").run()
    assert not at.exception
    at.button(key="nav_dashboard").click().run()
    assert at.session_state["stage"] == "dashboard"
    at.button(key="nav_issues").click().run()
    assert at.session_state["stage"] == "issues"
    click(at, "🛠️ Apply Suggested Fix")
    report = json.loads(at.session_state["json_report"])
    assert report["issues"][0]["verification_status"] == "PASS"
    assert report["overall_summary"]["total_issues"] == 0
    assert "import os" in (workspace / "sample.py").read_text()
    click(at, "↩️ Revert fix")
    assert (workspace / "sample.py").read_text() == (tmp_path / "sample.py").read_text()
    assert json.loads(at.session_state["json_report"])["overall_summary"]["total_issues"] == 1
    click(at, "🔄 New Scan")
    assert at.session_state["stage"] == "landing"
    assert not workspace.exists()
    assert at.session_state["applied_issues"] == {}

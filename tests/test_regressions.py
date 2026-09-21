import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.analyzer import CodeAnalyzer
from core.fixer import CodeFixer, _replace_all_secret_assignments
from core.reporter import Reporter
from core.repository import _extract_archive, RepositoryError
from core.test_runner import TestRunner
from core.verifier import Verifier
from core.workspace import persist_workspace, cleanup_workspace
from config import Config


def test_secret_fix_executes_and_preserves_future_imports(tmp_path, monkeypatch):
    source = '"""Module docstring."""\nfrom __future__ import annotations\ndef key():\n    TOKEN = "fakecredential123"\n    return TOKEN\n'
    path = tmp_path / "sample.py"
    path.write_text(source)
    issue = {"file": path.name, "line": 4, "title": "Hardcoded TOKEN", "source": "security"}
    result = CodeFixer().apply_fix_to_repo(tmp_path, issue, {})
    assert result["applied"]
    monkeypatch.setenv("TOKEN", "runtime-value")
    namespace = {}
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    assert namespace["key"]() == "runtime-value"
    assert "fakecredential123" not in str(result["changes"])
    assert Verifier(tmp_path).verify_fix(issue, result["changes"], run_tests=False)["status"] == "PASS"


def test_ordinary_strings_are_not_rewritten():
    code = 'NAME = "NeuroTrace"\nTOKEN = "fakecredential123"'
    fixed = _replace_all_secret_assignments(code)
    assert 'NAME = "NeuroTrace"' in fixed


def test_remaining_secret_cannot_verify(tmp_path):
    (tmp_path / "a.py").write_text('TOKEN = "fakecredential123"')
    result = Verifier(tmp_path).verify_fix(
        {"file": "a.py", "title": "Hardcoded TOKEN", "source": "security"},
        [{"file": "a.py"}], run_tests=False)
    assert result["status"] == "NOT_VERIFIED"


def test_passing_tests_do_not_prove_arbitrary_bug_fixed(tmp_path):
    (tmp_path / "a.py").write_text("value = 1")
    with patch.object(TestRunner, "available", return_value=True), patch.object(
        TestRunner, "run", return_value={"status": "PASS", "framework": "pytest", "passed": 1, "failed": 0}
    ):
        result = Verifier(tmp_path).verify_fix(
            {"file": "a.py", "title": "Wrong result", "source": "ai"}, [{"file": "a.py"}], run_tests=True)
    assert result["status"] == "NOT_VERIFIED"
    assert not result["verified"]


def test_backups_are_immutable_and_line_identity_survives(tmp_path):
    path = tmp_path / "a.py"
    source = 'TOKEN = "fakecredential123"\nPASSWORD = "fakepassword456"\n'
    path.write_text(source)
    analysis = CodeAnalyzer().analyze_repository(tmp_path, "test/repo", enable_ai=False)
    issues = [i for i in analysis["issues"] if i["source"] == "security"]
    fixer = CodeFixer()
    first = fixer.apply_fix_to_repo(tmp_path, issues[0], {})
    second = fixer.apply_fix_to_repo(tmp_path, issues[1], {})
    assert first["applied"] and second["applied"]
    assert first["backup"] != second["backup"]
    assert first["backup"].read_text() == source
    assert "fakepassword456" not in path.read_text()


def test_execution_requires_explicit_opt_in(tmp_path):
    with patch("core.test_runner.subprocess.run") as run:
        result = TestRunner(tmp_path, "pytest").run()
    assert result["status"] == "BLOCKED"
    run.assert_not_called()


@pytest.mark.parametrize("framework, output, expected", [
    ("jest", "Tests: 2 failed, 8 passed, 10 total", (10, 8, 2)),
    ("vitest", "Tests  2 failed | 8 passed (10)", (10, 8, 2)),
    ("mocha", "8 passing (1s)\n2 failing", (10, 8, 2)),
])
def test_framework_counts(framework, output, expected):
    assert TestRunner(Path("."), framework)._parse_summary(framework, output, "") == expected


def test_gradle_detection(tmp_path):
    (tmp_path / "build.gradle.kts").touch()
    assert TestRunner(tmp_path).framework == "gradle"


def test_workspaces_are_independent(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    first, second = persist_workspace(tmp_path), persist_workspace(tmp_path)
    try:
        assert first != second
        cleanup_workspace(first)
        assert (Path(second) / "a.py").exists()
        with pytest.raises(ValueError):
            cleanup_workspace(tmp_path)
    finally:
        cleanup_workspace(second)


@pytest.mark.parametrize("name", ["../escape.py", "/escape.py", "C:/escape.py"])
def test_archive_rejects_unsafe_paths(tmp_path, name):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr(name, "x")
    data.seek(0)
    with zipfile.ZipFile(data) as archive, pytest.raises(RepositoryError):
        _extract_archive(archive, tmp_path)


def test_archive_inflated_size_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "MAX_REPOSITORY_MB", 0)
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("repo/a.py", "x")
    data.seek(0)
    with zipfile.ZipFile(data) as archive, pytest.raises(RepositoryError):
        _extract_archive(archive, tmp_path)


def test_reports_redact_and_remove_sample_content():
    analysis = {"ai_sample_file": {"content": "rawsource"},
                "issues": [{"evidence": 'TOKEN = "fakecredential123"'}]}
    report = Reporter.generate_json_report(analysis)
    assert "rawsource" not in report
    assert "fakecredential123" not in report
    assert "[REDACTED]" in report
    assert "fakecredential123" not in Reporter.generate_markdown_report(analysis)

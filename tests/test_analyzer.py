"""Tests for analyzer module"""
from unittest.mock import Mock
from core.analyzer import CodeAnalyzer
from core.security_scanner import SecurityScanner


def make_provider():
    provider = Mock()
    provider.analyze_code.return_value = {"issues": [], "overall_quality": "GOOD"}
    provider.explain_code.return_value = "This code defines a function."
    return provider


def test_analyze_full_success():
    analyzer = CodeAnalyzer(make_provider())
    result = analyzer.analyze_full("def test(): pass", "python", enable_security=False)
    assert result["success"] is True
    assert "static_analysis" in result
    assert "overall_summary" in result


def test_analyze_full_with_security():
    analyzer = CodeAnalyzer(make_provider())
    result = analyzer.analyze_full("password = 'admin123'", "python", enable_security=True)
    assert result["success"] is True
    assert "security_scan" in result
    assert result["overall_summary"]["total_issues"] >= 0


def test_analyze_full_catches_syntax_error():
    analyzer = CodeAnalyzer(make_provider())
    result = analyzer.analyze_full("def broken(:\n  pass", "python", enable_security=False)
    issues = result["issues"]
    assert any(i["category"] == "BUG" and i["severity"] == "HIGH" for i in issues)


def test_explain_code():
    provider = make_provider()
    analyzer = CodeAnalyzer(provider)
    explanation = analyzer.explain_code("def test(): pass", "python")
    assert explanation


def test_analyze_repository(tmp_path):
    (tmp_path / "mod.py").write_text("import os\nAPI_KEY = 'sk-abc123'\ndef f():\n    return 1\n")
    analyzer = CodeAnalyzer(make_provider())
    result = analyzer.analyze_repository(tmp_path, "owner/repo", enable_security=True)
    assert result["success"] is True
    assert result["files_scanned"] >= 1
    assert result["overall_summary"]["total_issues"] >= 0
    assert any(i["severity"] == "HIGH" for i in result["security_issues"])


def test_language_breakdown(tmp_path):
    (tmp_path / "a.py").write_text("print(1)")
    (tmp_path / "b.js").write_text("console.log(1)")
    analyzer = CodeAnalyzer(make_provider())
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=False, enable_ai=False)
    breakdown = result["language_summary"]
    assert breakdown.get("python", 0) >= 1


def test_repository_ai_analysis_is_batched_single_call(tmp_path):
    """AI analysis over a repo uses ONE batched analyze call, not per-file."""
    (tmp_path / "a.py").write_text("def a():\n    return 1\n")
    (tmp_path / "b.py").write_text("def b():\n    return 2\n")
    (tmp_path / "c.py").write_text("def c():\n    return 3\n")
    provider = make_provider()
    provider.analyze_many_batched.return_value = {
        "issues": [{"file": "a.py", "title": "X", "line": 1}],
        "overall_quality": "GOOD",
        "batches_total": 1,
        "batches_succeeded": 1,
        "batch_errors": [],
        "partial": False,
    }
    analyzer = CodeAnalyzer(provider)
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=False, enable_ai=True)
    assert provider.analyze_many_batched.call_count == 1
    ai = [i for i in result["ai_issues"] if i.get("source") == "ai"]
    assert len(ai) == 1
    assert ai[0]["file"] == "a.py"


def test_repository_ai_graceful_fallback_on_error(tmp_path):
    """If the AI provider fails entirely, analysis still returns static results."""
    (tmp_path / "a.py").write_text("def a():\n    return 1\n")
    provider = make_provider()
    from core.ai_provider import RateLimitedError
    provider.analyze_many_batched.side_effect = RateLimitedError("rate limited")
    analyzer = CodeAnalyzer(provider)
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=False, enable_ai=True)
    assert result["success"] is True
    assert result["ai_status"].startswith("error:rate_limit")
    assert "files" in result


def test_repository_ai_partial_batch_timeout_keeps_merged_issues(tmp_path):
    """When one batch times out, the analyzer keeps successful-batch issues and reports partial status."""
    (tmp_path / "a.py").write_text("def a():\n    return 1\n")
    (tmp_path / "b.py").write_text("def b():\n    return 2\n")
    provider = make_provider()
    provider.analyze_many_batched.return_value = {
        "issues": [{"file": "a.py", "title": "Real AI finding", "line": 3}],
        "overall_quality": "GOOD",
        "batches_total": 2,
        "batches_succeeded": 1,
        "batch_errors": [{"kind": "timeout", "message": "Gemini API request timed out.",
                          "files": ["b.py"]}],
        "partial": True,
    }
    analyzer = CodeAnalyzer(provider)
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=False, enable_ai=True)
    ai = [i for i in result["ai_issues"] if i.get("source") == "ai"]
    assert len(ai) == 1
    assert ai[0]["title"] == "Real AI finding"
    assert result["ai_status"].startswith("error:timeout")
    assert "1/2 batch(es)" in result["ai_status"]


def test_repository_ai_retried_batch_status_is_actionable(tmp_path):
    """The partial-failure status must say batches were split/retried and that
    static/security/dependency results remain valid."""
    (tmp_path / "a.py").write_text("def a():\n    return 1\n")
    (tmp_path / "b.py").write_text("def b():\n    return 2\n")
    provider = make_provider()
    provider.analyze_many_batched.return_value = {
        "issues": [{"file": "a.py", "title": "Kept issue", "line": 3}],
        "overall_quality": "FAIR",
        "batches_total": 2,
        "batches_succeeded": 1,
        "batch_errors": [{"kind": "timeout", "message": "Gemini API request timed out.",
                          "files": ["b.py"], "retried": True, "splits": 1}],
        "partial": True,
    }
    analyzer = CodeAnalyzer(provider)
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=False, enable_ai=True)
    status = result["ai_status"]
    assert status.startswith("error:timeout")
    assert "split into smaller batches and retried" in status
    assert "Static, security, and dependency results remain valid" in status
    assert "no guesses were added" in status


def test_repository_ai_all_batches_fail_preserves_other_results(tmp_path):
    """When EVERY AI batch fails, static/security results are preserved and no
    AI issues are fabricated (empty ai_issues, actionable status message)."""
    (tmp_path / "a.py").write_text(
        "import os\nAPI_TOKEN = 'sk-a-real-looking-secret'\ndef a():\n    return 1\n"
    )
    (tmp_path / "b.py").write_text("def broken(:\n    return 2\n")
    provider = make_provider()
    provider.analyze_many_batched.return_value = {
        "issues": [],
        "overall_quality": "UNKNOWN",
        "batches_total": 2,
        "batches_succeeded": 0,
        "batch_errors": [
            {"kind": "timeout", "message": "Gemini API request timed out.",
             "files": ["a.py"], "retried": True, "splits": 1},
            {"kind": "timeout", "message": "Gemini API request timed out.",
             "files": ["b.py"], "retried": True, "splits": 1},
        ],
        "partial": True,
    }
    analyzer = CodeAnalyzer(provider)
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=True, enable_ai=True)

    assert result["success"] is True
    # No fabricated AI issues.
    assert [i for i in result["ai_issues"] if i.get("source") == "ai"] == []
    # Security + static (syntax bug) results survive a complete AI failure.
    assert len(result["security_issues"]) >= 1
    assert any(
        i["category"] == "BUG" and i["severity"] == "HIGH" for i in result["issues"]
    )
    status = result["ai_status"]
    assert status.startswith("error:timeout")
    assert "0/2 batch(es)" in status
    assert "split into smaller batches and retried" in status
    assert "Static, security, and dependency results remain valid" in status


def _ai_json_for(*paths):
    issues = ",".join(
        '{"file": "%s", "title": "AI finding in %s", "line": 2, "severity": "MEDIUM", "category": "CODE_QUALITY"}'
        % (p, p) for p in paths
    )
    return '{"issues": [%s], "overall_quality": "FAIR"}' % issues


class BatchRecordingProvider:
    """Real AIProvider subclass that records every request's files, then answers from a script."""

    def __init__(self, responses, batch_size=4):
        self.responses = list(responses)
        self.requests = []
        self.analyze_many_batched_calls = 0
        self.batch_size = batch_size

    def analyze_many_batched(self, files, max_chars_per_file=4000,
                             max_files_per_batch=4, max_chars_per_batch=16000,
                             max_split_depth=None, progress=None):
        from core.ai_provider import AIProvider, split_file_batches

        class _P(AIProvider):
            def _normalize_model(self):
                return "gemini-3.5-flash-lite"

            def __init__(self, batch, response):
                self.batch = batch
                self.response = response

            def complete(self, system, user_message, max_tokens=6000):
                return self.response

        self.analyze_many_batched_calls += 1
        batches = split_file_batches(
            files, max_chars_per_file=max_chars_per_file,
            max_files_per_batch=max_files_per_batch,
            max_chars_per_batch=max_chars_per_batch,
        )
        all_issues = []
        errors = []
        for i, batch in enumerate(batches):
            paths = [r["path"] for r in batch]
            self.requests.append(paths)
            if i < len(self.responses) and isinstance(self.responses[i], Exception):
                errors.append({"kind": "timeout", "message": "Gemini API request timed out.",
                               "files": paths})
                continue
            resp = self.responses[i] if i < len(self.responses) and self.responses[i] is not None else _ai_json_for(*paths)
            prov = _P(batch, resp)
            result = prov.analyze_many(batch, max_chars_per_file=max_chars_per_file)
            all_issues.extend(result["issues"])
        return {
            "issues": all_issues,
            "overall_quality": "FAIR",
            "batches_total": len(batches),
            "batches_succeeded": len(batches) - len(errors),
            "batch_errors": errors,
            "partial": bool(errors),
        }


def test_analyze_repository_splits_large_repo_into_bounded_requests(tmp_path):
    """A 12-file repo is analyzed via several small bounded requests, never one huge one."""
    for i in range(12):
        (tmp_path / f"mod{i}.py").write_text(
            "def func():\n    return %d\n\nclass Klass:\n    pass\n" % i + "x = 1\n" * 40
        )
    # Respond with an issue for every file in each batch (batch grouping is
    # determined by the provider, so we just return all 12 at once and let the
    # provider stub split them correctly).
    provider = BatchRecordingProvider([None])  # fallback: returns _ai_json_for per-batch
    analyzer = CodeAnalyzer(provider)
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=False, enable_ai=True)

    # At least 3 batches of ≤4 files for 12 files.
    assert len(provider.requests) >= 3
    assert all(len(req) <= 4 for req in provider.requests)
    # Every file sent exactly once across all batches.
    sent = [p for req in provider.requests for p in req]
    assert len(sent) == len(set(sent)) == 12
    assert result["success"] is True
    assert result["ai_status"] == "ok"
    # Every file has at least one AI issue attributed to it.
    assert {i["file"] for i in result["ai_issues"]} == {f"mod{i}.py" for i in range(12)}


def test_analyze_repository_timeout_preserves_security_and_partial_ai(tmp_path):
    """If one batch times out, security results are preserved and only successful AI batches are merged."""
    for i in range(8):
        if i == 0:
            code = "API_KEY = 'sk-secret-0'\n"
        else:
            code = "def func():\n    return %d\n" % i
        (tmp_path / f"mod{i}.py").write_text(code)
    # 8 files / AI_BATCH_MAX_FILES=3 = 3 batches.  Batch 1 (index 1) times out.
    # Batches 0 and 2 succeed; batch 2 falls back to per-file issues for its files.
    responses = [
        _ai_json_for("mod0.py", "mod1.py", "mod2.py", "mod3.py"),
        TimeoutError("socket timeout"),
    ]
    provider = BatchRecordingProvider(responses)
    analyzer = CodeAnalyzer(provider)
    result = analyzer.analyze_repository(tmp_path, "o/r", enable_security=True, enable_ai=True)

    # Static/security results survive even though an AI batch failed.
    assert result["success"] is True
    assert result["security_issues"], "security scan must still run"
    # AI status clearly names timeout + partial progress + validity of static results.
    assert result["ai_status"].startswith("error:timeout")
    assert "2/3 batch(es)" in result["ai_status"]
    assert "Static, security, and dependency results remain valid" in result["ai_status"]
    assert "no guesses were added" in result["ai_status"]
    # The successfully analyzed batches contributed real attributed issues.
    assert len({i["file"] for i in result["ai_issues"]}) == 5

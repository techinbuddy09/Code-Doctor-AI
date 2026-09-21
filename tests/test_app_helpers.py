"""Tests for app-level helper functions (AI status messaging, back-navigation)."""
import pytest


@pytest.fixture
def app_mod():
    from app import _friendly_ai_status, _back_target
    return _friendly_ai_status, _back_target


def test_friendly_ai_status_rate_limit():
    from app import _friendly_ai_status
    msg = _friendly_ai_status("error:rate_limit:Too Many Requests")
    assert "rate-limited" in msg
    assert "Too Many Requests" in msg


def test_friendly_ai_status_quota():
    from app import _friendly_ai_status
    msg = _friendly_ai_status("error:quota:Insufficient credits")
    assert "quota" in msg or "credits" in msg


def test_friendly_ai_status_generic():
    from app import _friendly_ai_status
    assert "error" in _friendly_ai_status("error:provider:boom")
    # Non-error statuses pass through untouched.
    assert _friendly_ai_status("ok") == "ok"


def test_back_target_prefers_results_views():
    from app import _back_target
    assert _back_target("issues") == "issues"
    assert _back_target("tests") == "tests"
    assert _back_target("dashboard") == "dashboard"


def test_back_target_fallback_dashboard():
    from app import _back_target
    assert _back_target("landing") == "landing"
    assert _back_target("scanning") == "dashboard"
    assert _back_target(None) == "dashboard"
    assert _back_target("report") == "dashboard"


def test_issues_view_handles_missing_issue_id():
    """Real AI results may contain issues without an 'issue_id'. The issues view
    must render unique Apply Suggested Fix / Revert buttons (not crash with a
    duplicate Streamlit element key for fix_None)."""
    import os
    from streamlit.testing.v1 import AppTest

    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
    issues = [
        {
            "issue_id": None,
            "title": "Duplicate utility logic A",
            "severity": "HIGH",
            "category": "CODE_QUALITY",
            "file": "svc_01.py",
            "line": 3,
            "source": "ai",
            "fixable": True,
            "confidence": "high",
            "description": "Repeated logic in module A.",
            "recommended_fix": "Extract shared helper.",
        },
        {
            "issue_id": None,
            "title": "Duplicate utility logic B",
            "severity": "MEDIUM",
            "category": "CODE_QUALITY",
            "file": "svc_02.py",
            "line": 5,
            "source": "ai",
            "fixable": True,
            "confidence": "medium",
            "description": "Repeated logic in module B.",
            "recommended_fix": "Extract shared helper.",
        },
    ]
    files_map = {
        f"{f}.py": {
            "path": f"{f}.py",
            "content": "line1\nline2\nline3\nline4\nline5\nline6\nline7\n",
            "language": "python",
        }
        for f in ("svc_01", "svc_02")
    }

    at = AppTest.from_file(app_path, default_timeout=60)
    at.session_state["stage"] = "issues"
    at.session_state["analysis"] = {"issues": issues}
    at.session_state["files_map"] = files_map
    at.session_state["applied_issues"] = {}
    at.run()

    assert not at.exception, f"issues view crashed: {at.exception}"
    apply_keys = [b.key for b in at.button if b.key.startswith("fix_")]
    assert len(apply_keys) == 2, f"expected 2 Apply buttons, got keys: {apply_keys}"
    assert len(set(apply_keys)) == 2, f"Apply button keys not unique: {apply_keys}"

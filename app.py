"""
Code Doctor AI — main Streamlit application.

A dark, cinematic, AI-powered GitHub repository debugging tool. Users paste a
repository URL, the app safely ingests and scans it, surfaces structured issues
with fixes, runs tests, verifies, and generates a professional report.
"""
import sys
import copy
import hashlib
from pathlib import Path

import streamlit as st

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent))

from config import Config  # noqa: E402
from core.ai_provider import create_ai_provider, classify_provider_error  # noqa: E402
from core.analyzer import CodeAnalyzer  # noqa: E402
from core.repository import Repository  # noqa: E402
from core.fixer import CodeFixer  # noqa: E402
from core.test_runner import TestRunner  # noqa: E402
from core.reporter import Reporter  # noqa: E402
from core.verifier import Verifier  # noqa: E402
from core.test_generator import TestGenerator  # noqa: E402
from ui.theme import inject_visuals  # noqa: E402
from ui import components as C  # noqa: E402

st.set_page_config(
    page_title="Code Doctor AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load secrets from Streamlit Cloud (safe to call on local dev too)
Config.load_from_secrets()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_defaults = {
    "stage": "landing",        # landing | dashboard | issues | report
    "repo_url": "",
    "repo_owner_repo": "",
    "repo_path": None,         # extracted repo root (stable dir)
    "repo_temp_dir": None,
    "analysis": None,
    "files_map": {},
    "applied_issues": {},      # issue_id -> verification
    "test_result": None,
    "test_framework": None,
    "error": None,
    "assistant_status": ("Ready. Paste a GitHub repository URL to begin.", "ready"),
    "raw_report": "",
    "json_report": "",
    "_provider_error": None,
    "_prev_stage": "landing",
    "generated_test": None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = copy.deepcopy(v)


def _set_status(text, kind="ready"):
    st.session_state.assistant_status = (text, kind)


# Valid in-app stages (used to validate back-navigation targets).
_VALID_STAGES = ("landing", "scanning", "dashboard", "issues", "tests", "report")


def _record_prev_stage():
    """Remember the current stage as the "previous" stage for back navigation."""
    cur = st.session_state.stage
    if cur in _VALID_STAGES:
        st.session_state._prev_stage = cur


def _back_target(prev_stage):
    """Compute the correct target stage for back-navigation from a stored previous stage."""
    if prev_stage in ("issues", "tests", "dashboard"):
        return prev_stage
    if prev_stage == "landing":
        return "landing"
    return "dashboard"


def _go_back():
    """Navigate to the previous appropriate scan/results view (not the browser back)."""
    prev = getattr(st.session_state, "_prev_stage", None)
    st.session_state.stage = _back_target(prev)
    st.rerun()


# ---------------------------------------------------------------------------
def build_ai_provider(enable_ai: bool):
    """Create an AI provider from config, or None if unavailable/disabled.

    Stores ``st.session_state._provider_error`` when creation fails so the UI
    can display a helpful message instead of silently disabling AI.
    """
    st.session_state._provider_error = None
    if not enable_ai:
        return None

    provider = Config.AI_PROVIDER
    api_key = Config.AI_API_KEY
    model = Config.effective_model(provider)
    extra_key = Config.OPENAI_API_KEY
    extra_model = Config.effective_model("openai")
    gemini_key = Config.GEMINI_API_KEY
    gemini_model = Config.GEMINI_MODEL

    # Auto-fallback: if primary provider has no key, try another one
    if provider == "gemini" and not gemini_key:
        if api_key:
            provider = "anthropic"
        elif extra_key:
            provider = "openai"
        else:
            return None
    elif provider == "anthropic" and not api_key:
        if gemini_key:
            provider = "gemini"
        elif extra_key:
            provider = "openai"
        else:
            return None
    elif provider == "openai" and not extra_key:
        if gemini_key:
            provider = "gemini"
        elif api_key:
            provider = "anthropic"
        else:
            return None

    model = Config.effective_model(provider)
    try:
        return create_ai_provider(
            provider, api_key, model,
            extra_key=extra_key, extra_model=extra_model,
            gemini_key=gemini_key, gemini_model=gemini_model,
        )
    except Exception as e:
        msg, kind = classify_provider_error(e)
        st.session_state["_provider_error"] = (msg, kind)
        return None


# ---------------------------------------------------------------------------
def setup_sidebar():
    """Sidebar config; returns analysis options dict."""
    with st.sidebar:
        if st.session_state.stage != "landing":
            if st.button("🩺 Code Doctor AI", key="sidebar_logo_btn", use_container_width=True):
                _cleanup_repo()
                for k in ("analysis", "files_map", "applied_issues", "test_result",
                          "test_framework", "error", "raw_report", "json_report",
                          "_provider_error"):
                    st.session_state[k] = copy.deepcopy(_defaults[k])
                st.session_state.stage = "landing"
                st.session_state.repo_url = ""
                st.rerun()
        else:
            st.markdown("<div class='cd-logo'><span class='nt-logo-mark'>≋</span> Code Doctor AI</div>", unsafe_allow_html=True)
        st.caption("Your code intelligence workspace")
        st.markdown("<div class='cd-side-title'>WORKSPACE</div>", unsafe_allow_html=True)
        for target, label in (("landing", "⌂  Overview"), ("dashboard", "◫  Analysis"),
                              ("issues", "◎  Issues"), ("tests", "◇  Tests"), ("report", "▤  Report")):
            available = target == "landing" or st.session_state.analysis is not None
            if st.button(label, key=f"nav_{target}", use_container_width=True,
                         disabled=not available or st.session_state.stage == "scanning",
                         type="primary" if st.session_state.stage == target else "secondary"):
                _record_prev_stage()
                st.session_state.stage = target
                st.rerun()
        st.divider()

        st.markdown("<div class='cd-side-title'>⚙️ Configuration</div>", unsafe_allow_html=True)
        Config.load_from_secrets()
        Config.validate()
        has_key = bool(Config.GEMINI_API_KEY or Config.AI_API_KEY or Config.OPENAI_API_KEY)

        if not has_key:
            st.warning(
                "No AI API key found. Static, security & dependency analysis "
                "will run locally. Add `GEMINI_API_KEY` (recommended), "
                "`AI_API_KEY`, or `OPENAI_API_KEY` "
                "to your Streamlit secrets (or `.env` locally) to enable AI code review."
            )

        enable_ai = st.checkbox("AI analysis", value=has_key and Config.ENABLE_AI_ANALYSIS, disabled=not has_key)
        enable_security = st.checkbox("Security scan", value=Config.ENABLE_SECURITY_SCAN)
        if st.session_state.pop("_reset_test_trust", False):
            st.session_state.allow_local_tests = False
        enable_tests = st.checkbox("Allow local test execution for this repository", value=False,
                                   key="allow_local_tests")
        st.caption("Tests execute repository code on this computer without a sandbox. Enable only for a repository you trust.")

        st.divider()
        st.markdown("<div class='cd-side-title'>🖥️ System Status</div>", unsafe_allow_html=True)
        ai_state = "online" if (has_key and enable_ai) else "offline"
        st.markdown(
            C.status_row([
                ("AI", ai_state),
                ("Security", "online" if enable_security else "offline"),
                ("Repository Scanner", "online"),
                ("Test Runner", "online" if enable_tests else "offline"),
            ]),
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown("<div class='cd-side-title'>ℹ️ About</div>", unsafe_allow_html=True)
        st.markdown(
            "Scans a public GitHub repo for bugs, security issues, dependency "
            "problems and quality gaps — with targeted fixes and verification."
        )

        if st.session_state.stage != "landing":
            st.divider()
            if st.button("🔄 New Scan", use_container_width=True, key="new_scan_btn"):
                _cleanup_repo()
                for k in ("analysis", "files_map", "applied_issues", "test_result",
                          "test_framework", "error", "raw_report", "json_report",
                          "_provider_error"):
                    st.session_state[k] = copy.deepcopy(_defaults[k])
                st.session_state.stage = "landing"
                st.session_state.repo_url = ""
                st.rerun()

        return {"enable_ai": enable_ai, "enable_security": enable_security,
                "enable_tests": enable_tests}


def _cleanup_repo():
    if st.session_state.repo_temp_dir:
        from core.workspace import cleanup_workspace
        cleanup_workspace(st.session_state.repo_temp_dir)
    # Also remove our managed dir marker
    st.session_state.repo_temp_dir = None
    st.session_state.repo_path = None
    st.session_state.generated_test = None
    st.session_state._reset_test_trust = True


# ---------------------------------------------------------------------------
def landing_view(opts):
    st.markdown(C.hero_html(), unsafe_allow_html=True)
    st.markdown(C.workflow_html(), unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(C.input_card_head(), unsafe_allow_html=True)
        url = st.text_input(
            "GitHub repository URL",
            value=st.session_state.repo_url,
            placeholder="https://github.com/owner/repo",
            key="repo_url_input",
            label_visibility="collapsed",
        )
        st.session_state.repo_url = url

        col1, col2 = st.columns([1, 2])
        with col1:
            start = st.button("🚀 Start Analysis", type="primary", use_container_width=True)
        with col2:
            st.markdown("_Only **public** repositories are supported._")

    with st.expander("What gets analyzed", expanded=False):
        st.markdown("""
- **Bugs & syntax errors** across supported languages
- **Security** — hardcoded secrets (masked), injection, unsafe calls, deserialization
- **Dependencies** — unpinned / invalid / EOL dependency declarations
- **Code quality** — TODOs, complexity, structure
- **Performance & configuration** patterns
- **Testing** — detects framework and runs your test suite after fixes
        """)

    st.markdown(C.feature_grid(), unsafe_allow_html=True)

    if start:
        if not url or not url.strip():
            st.error("Please enter a GitHub repository URL.")
            return
        is_valid, msg = _valid_url(url)
        if not is_valid:
            st.session_state.error = msg
            st.rerun()
        st.session_state.repo_url = url.strip()
        st.session_state.stage = "scanning"
        st.session_state.error = None
        _set_status("Connecting to repository…", "scanning")
        st.rerun()


def _valid_url(url):
    from utils.validators import Validators
    ok, msg = Validators.validate_github_url(url)
    return ok, ("" if ok else msg)


# ---------------------------------------------------------------------------
def scanning_view(opts):
    st.markdown(C.scan_panel_html(), unsafe_allow_html=True)

    status_holder = st.empty()
    progress = st.progress(0.0, text="Starting…")

    def _scan_msg(msg):
        status_holder.markdown(
            f"<div class='cd-scan-msg'>◉ {C.esc(msg)}</div>",
            unsafe_allow_html=True,
        )

    with st.status("Analyzing repository…", expanded=True) as st_state:
        steps = []

        _scan_msg("Connecting to repository…")
        repo = None
        try:
            repo = Repository.fetch(st.session_state.repo_url, timeout=Config.GITHUB_REQUEST_TIMEOUT)
        except Exception as e:
            st.session_state.error = f"Repository could not be loaded: {str(e)}"
            st_state.update(label="Failed to load repository", state="error")
            st.session_state.stage = "landing"
            st.rerun()

        owner_repo = repo.name
        repo_path = repo.safe_root
        progress.progress(0.08, text="Repository loaded")
        st.session_state.repo_owner_repo = owner_repo

        # Keep repo alive across reruns by extracting to a stable dir.
        stable = _persist_repo(repo_path, owner_repo)
        repo.cleanup()
        if stable is None:
            st.session_state.error = "Could not prepare repository workspace."
            st.session_state.stage = "landing"
            st.rerun()
        st.session_state.repo_temp_dir = stable
        st.session_state.repo_path = stable

        st.write("✅ Repository loaded")

        # Build analyzer
        provider = build_ai_provider(opts["enable_ai"])
        if provider is None and opts["enable_ai"]:
            prov_err = getattr(st.session_state, "_provider_error", None)
            if prov_err:
                err_msg, err_kind = prov_err
                _set_status(f"AI provider error: {err_msg}", "error")
                st.warning(f"⚠️ AI provider unavailable — {err_msg} "
                           "Proceeding with local scans only.")
        analyzer = CodeAnalyzer(provider)

        def report_progress(msg):
            _scan_msg(msg)
            steps.append(msg)
            return msg

        try:
            result = analyzer.analyze_repository(
                Path(stable), owner_repo,
                enable_security=opts["enable_security"],
                enable_ai=opts["enable_ai"],
                progress=report_progress,
            )
        except Exception as e:
            _cleanup_repo()
            st.session_state.error = f"Analysis failed: {e}"
            st.session_state.stage = "landing"
            st.rerun()
        progress.progress(0.7, text="Analysis complete")

        # Store results
        st.session_state.analysis = result
        st.session_state.files_map = {f.get("path"): f for f in result.get("files", [])}
        st.session_state.repo_path = stable

        report = Reporter.generate_markdown_report(result, repo=owner_repo)
        st.session_state.raw_report = report
        st.session_state.json_report = Reporter.generate_json_report(result)

        progress.progress(0.85, text="Preparing report")

        # Tests (optional, after fix can re-run)
        if opts["enable_tests"]:
            runner = TestRunner(Path(stable))
            st.session_state.test_framework = runner.framework
            if runner.available():
                st.write(f"🧪 Running {runner.framework} tests…")
                test_result = runner.run(allow_execution=True)
                st.session_state.test_result = test_result
                if test_result["status"] == "PASS":
                    st.success(f"✅ Tests passed: {test_result['passed']} passed")
                elif test_result["status"] == "FAIL":
                    st.error(f"❌ Tests failed: {test_result['failed']} failed")
                else:
                    st.warning(f"⚠️ Tests blocked: {test_result.get('reason')}")
                result["test_result"] = test_result
                st.session_state.analysis = result
            else:
                st.info(f"⚠️ No runnable test framework detected ({runner.framework}).")

        progress.progress(1.0, text="Done")

        _set_status(
            f"Analysis complete. {result['overall_summary']['total_issues']} issue(s) found.",
            "scan_complete",
        )
        st.session_state.stage = "dashboard"
        st.rerun()


def _persist_repo(repo_path, owner_repo):
    """Move the extracted repo into a stable directory we can revisit."""
    from core.workspace import persist_workspace
    try:
        return persist_workspace(repo_path)
    except Exception:
        return None


def _sync_results():
    """Refresh exports and tracked finding counts from current verification state."""
    analysis = st.session_state.analysis
    if not analysis:
        return
    for issue in analysis.get("issues", []):
        ver = st.session_state.applied_issues.get(issue.get("issue_id"), {})
        issue["verification_status"] = ver.get("status", "NOT_VERIFIED")
    remaining = [i for i in analysis.get("issues", []) if i.get("verification_status") != "PASS"]
    summary = analysis.setdefault("overall_summary", {})
    summary["total_issues"] = len(remaining)
    summary["resolved_issues"] = sum(i.get("verification_status") == "PASS" for i in analysis.get("issues", []))
    for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
        summary[severity.lower()] = sum(i.get("severity") == severity for i in remaining)
    summary["security_issues"] = sum(i.get("category") == "SECURITY" for i in remaining)
    summary["dependency_issues"] = sum(i.get("source") == "dependency" for i in remaining)
    analysis["test_result"] = st.session_state.test_result
    st.session_state.raw_report = Reporter.generate_markdown_report(analysis, repo=analysis.get("repo", ""))
    st.session_state.json_report = Reporter.generate_json_report(analysis)


# ---------------------------------------------------------------------------
def dashboard_view(opts):
    analysis = st.session_state.analysis
    if analysis is None:
        st.session_state.stage = "landing"
        st.rerun()

    summary = analysis["overall_summary"]
    health = Reporter.health_score(summary)

    st.markdown(
        C.page_head(
            "📊 Analysis Dashboard",
            f"Repository · <code>{C.esc(analysis.get('repo', ''))}</code>",
        ),
        unsafe_allow_html=True,
    )
    st.write("")

    # Health + metrics
    colA, colB = st.columns([1, 3])
    with colA:
        st.markdown(C.health_ring(health), unsafe_allow_html=True)
    with colB:
        C.metric_row({
            "Files Scanned": summary.get("files_scanned", 0),
            "Lines of Code": summary.get("lines_of_code", 0),
            "Issues": summary.get("total_issues", 0),
            "Critical": summary.get("critical", 0),
            "High": summary.get("high", 0),
            "Security": summary.get("security_issues", 0),
        })

    # AI / provider status note
    ai_status = analysis.get("ai_status", "disabled")
    rejected = analysis.get("ai_rejected_issues", [])
    if rejected:
        st.info(f"Excluded {len(rejected)} AI claims contradicted by full-file Python checks. These do not affect the score; details are in the report.")
    if isinstance(ai_status, str) and ai_status.startswith("error"):
        _msg = _friendly_ai_status(ai_status)
        st.warning(
            f"⚠️ AI analysis note: {_msg}. Static, security & dependency "
            "results below are unaffected."
        )
    elif opts["enable_ai"] and analysis.get("ai_issues"):
        st.success(f"🤖 AI analysis identified {len(analysis['ai_issues'])} issue(s).")
    elif not opts["enable_ai"]:
        st.info("AI analysis disabled — running local static/security/dependency scan only.")

    st.write("")
    C.section("Repository languages")
    lang_bd = analysis.get("language_summary", {})
    if lang_bd:
        C.lang_chips(lang_bd)
    else:
        st.markdown(
            C.empty_state_html("No source languages detected", None, "📁"),
            unsafe_allow_html=True,
        )

    st.write("")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🐛 View Issues", type="primary", use_container_width=True):
            _record_prev_stage()
            st.session_state.stage = "issues"
            st.rerun()
    with col2:
        if st.button("🧪 View Tests", use_container_width=True):
            _record_prev_stage()
            st.session_state.stage = "tests"
            st.rerun()
    with col3:
        if st.button("📄 View Report", use_container_width=True):
            _record_prev_stage()
            st.session_state.stage = "report"
            st.rerun()
    with col4:
        if st.button("🔧 Apply Suggested Fixes", use_container_width=True):
            _record_prev_stage()
            st.session_state.stage = "issues"
            st.session_state._auto_fix = True
            st.rerun()


# ---------------------------------------------------------------------------
def issues_view(opts):
    analysis = st.session_state.analysis
    if analysis is None:
        st.session_state.stage = "landing"
        st.rerun()
    issues = analysis.get("issues", [])

    st.markdown(C.page_head("🔍 Issue Explorer", "Code-quality &amp; security findings dashboard"), unsafe_allow_html=True)

    back_col, _ = st.columns([1, 5])
    with back_col:
        if _back_button(key="back_issues"):
            _go_back()

    st.write("")

    # Filters
    query = st.text_input("Search issues", placeholder="Search by title, file, or description…", key="issue_search")
    f1, f2, f3, f4 = st.columns(4)
    sev_opts = ["All"] + Config.SEVERITIES
    cat_opts = ["All"] + list(Config.CATEGORIES.keys())
    with f1:
        f_sev = st.selectbox("Severity", sev_opts)
    with f2:
        f_cat = st.selectbox("Category", cat_opts)
    with f3:
        f_fix = st.selectbox("Fixable", ["All", "Yes", "No"])
    with f4:
        f_src = st.selectbox("Source", ["All", "security", "dependency", "ai", "parser", "static"])

    filtered = []
    for iss in issues:
        if query and query.casefold() not in " ".join(str(iss.get(k, "")) for k in ("title", "file", "description")).casefold():
            continue
        if f_sev != "All" and iss.get("severity") != f_sev:
            continue
        if f_cat != "All" and iss.get("category") != f_cat:
            continue
        if f_fix == "Yes" and not iss.get("fixable"):
            continue
        if f_fix == "No" and iss.get("fixable"):
            continue
        if f_src != "All" and iss.get("source") != f_src:
            continue
        filtered.append(iss)

    st.markdown(
        f"<div class='cd-issue-count'>Showing <b>{len(filtered)}</b> of <b>{len(issues)}</b> issues.</div>",
        unsafe_allow_html=True,
    )
    st.write("")

    if not filtered:
        st.markdown(
            C.empty_state_html(
                "No issues match the current filters",
                "Try widening the filters to surface more findings.",
                "🎉",
            ),
            unsafe_allow_html=True,
        )
        return

    # Auto-fix mode
    if getattr(st.session_state, "_auto_fix", False):
        st.session_state._auto_fix = False
        _auto_apply_fixes(opts)
        st.rerun()

    for idx, iss in enumerate(filtered, 1):
        with st.expander(_issue_header(iss, idx), expanded=iss.get("severity") in ("CRITICAL", "HIGH")):
            _render_issue_details(iss, opts, idx)


def _issue_header(iss, idx):
    mark, _ = C.SEVERITY_LABEL.get(iss.get("severity", "INFO"), ("⚪", "#9aa0a6"))
    cat_e = Config.CATEGORIES.get(iss.get("category", "OTHER"), "📋")
    return f"{mark} #{idx} · {cat_e} {iss.get('title','Issue')} — {iss.get('severity')} · `{iss.get('file')}:{iss.get('line')}`"


def _render_issue_details(iss, opts, idx):
    st.markdown(C.issue_detail_html(iss), unsafe_allow_html=True)

    key = iss.get("file")
    rec = st.session_state.files_map.get(key) if key else None
    if rec and rec.get("content"):
        line = int(iss.get("line") or 1)
        st.markdown("<div class='cd-block-label'>Current Code</div>", unsafe_allow_html=True)
        C.code_view(rec, highlight_lines=[line], window=14)
        total_lines = len((rec.get("content") or "").splitlines())
        if total_lines > 44:
            with st.expander("Show full file", expanded=False):
                C.code_view(rec, highlight_lines=[line], window=None)

    st.markdown("<div class='cd-block-label'>Verification</div>", unsafe_allow_html=True)
    vid = iss.get("issue_id")
    if vid in st.session_state.applied_issues:
        ver = st.session_state.applied_issues[vid]
        status = ver.get("status", "")
        if status == "PASS":
            st.success(f"✅ Fix applied & verified — {C.esc(status)}")
        elif status == "FAIL":
            st.error(f"❌ Fix applied but verification failed — {C.esc(status)}")
        else:
            st.warning(f"⚠️ Fix applied — verification: {C.esc(status)}")
        for note in ver.get("notes", []):
            st.markdown(f"- {note}")
        if ver.get("test_result"):
            tr = ver["test_result"]
            st.markdown(f"- Tests: {tr.get('status')} ({tr.get('passed')} passed, {tr.get('failed')} failed)")
    else:
        st.markdown(
            "<div class='cd-issue' style='margin-top:0;'>"
            "<div class='cd-detail-body' style='margin-top:0;color:var(--cd-muted);'>"
            "No fix has been applied to this issue yet.</div></div>",
            unsafe_allow_html=True,
        )

    if iss.get("fixable"):
        if vid in st.session_state.applied_issues:
            if st.button(f"↩️ Revert fix", key=f"revert_{vid or 'u'}_{idx}", use_container_width=True):
                _revert_fix(iss)
                st.rerun()
        else:
            if st.button(f"🛠️ Apply Suggested Fix", key=f"fix_{vid or 'u'}_{idx}", type="primary", use_container_width=True):
                _apply_fix(iss, opts)
                st.rerun()


def _apply_fix(iss, opts):
    repo_path = st.session_state.repo_path
    if not repo_path:
        st.session_state.error = "No repository workspace. Start a new scan."
        return
    try:
        provider = build_ai_provider(opts["enable_ai"])
        fixer = CodeFixer(provider)
        with st.spinner("Applying suggested fix…"):
            result = fixer.apply_fix_to_repo(Path(repo_path), iss, st.session_state.files_map)
    except Exception as e:
        st.session_state.error = f"Unexpected error applying fix: {e}"
        return
    if not result.get("applied"):
        detail = result.get("error", "Unknown error")
        st.session_state.error = f"Fix could not be applied: {detail}"
        return
    # Verify
    try:
        with st.spinner("Verifying the fix…"):
            verifier = Verifier(Path(repo_path))
            ver = verifier.verify_fix(iss, result.get("changes", []), run_tests=opts["enable_tests"])
    except Exception as e:
        st.session_state.error = f"Fix was applied but verification failed: {e}"
        ver = {"status": "NOT_VERIFIED", "verified": False,
               "notes": ["Verification failed; the backup is available for revert."], "test_result": None}
    ver["backup"] = str(result["backup"])
    ver["file"] = iss["file"]
    ver["changes"] = result.get("changes", [])
    ver["post_hash"] = hashlib.sha256((Path(repo_path) / iss["file"]).read_bytes()).hexdigest()
    st.session_state.applied_issues[iss["issue_id"]] = ver
    st.session_state.test_result = ver.get("test_result")
    _set_status(f"Fix applied for '{iss.get('title')}'. Verification: {ver['status']}.", "scan_complete")
    # refresh files map
    _refresh_files_map(repo_path)


def _refresh_files_map(repo_path):
    from core.code_parser import CodeParser
    parser = CodeParser()
    files = parser.discover_files(Path(repo_path))
    files = parser.read_many(files)
    st.session_state.files_map = {f.get("path"): f for f in files}
    # A later fix/revert may invalidate a previous finding's resolution.
    for issue in (st.session_state.analysis or {}).get("issues", []):
        stored = st.session_state.applied_issues.get(issue.get("issue_id"))
        if stored:
            current = Verifier(Path(repo_path)).verify_fix(issue, stored.get("changes", []), run_tests=False)
            current["test_result"] = st.session_state.test_result
            if st.session_state.test_result and st.session_state.test_result.get("status") in ("FAIL", "BLOCKED"):
                current["status"] = st.session_state.test_result["status"]
                current["verified"] = False
            stored.update(current)


def _revert_fix(iss):
    repo_path = st.session_state.repo_path
    if not repo_path:
        return
    from core.fixer import _is_within
    ver = st.session_state.applied_issues.get(iss.get("issue_id"), {})
    backup_file = Path(ver.get("backup", ""))
    target = Path(repo_path) / iss.get("file", "")
    if (backup_file.is_file() and _is_within(Path(repo_path) / ".codedoctor_backups", backup_file)
            and target.is_file() and _is_within(Path(repo_path), target)):
        if hashlib.sha256(target.read_bytes()).hexdigest() != ver.get("post_hash"):
            st.session_state.error = "This file changed after the fix. Revert its latest fix first."
            return
        target.write_bytes(backup_file.read_bytes())
        for key, applied in list(st.session_state.applied_issues.items()):
            if applied.get("backup") == str(backup_file):
                st.session_state.applied_issues.pop(key)
        st.session_state.test_result = None
        _refresh_files_map(repo_path)


def _auto_apply_fixes(opts):
    """Apply deterministic (security) fixes automatically where safe, batching AI
    rewrites per file so we don't send a separate AI request for every issue."""
    analysis = st.session_state.analysis
    repo_path = st.session_state.repo_path
    if not repo_path:
        return
    from core.fixer import CodeFixer
    try:
        provider = build_ai_provider(opts["enable_ai"])
    except Exception as e:
        st.warning(f"⚠️ Could not initialise AI provider for auto-fix: {e}")
        provider = None
    fixer = CodeFixer(provider)
    verifier = Verifier(Path(repo_path))

    pending = [
        iss for iss in analysis.get("issues", [])
        if iss.get("fixable")
        and iss.get("issue_id") not in st.session_state.applied_issues
    ]
    if not pending:
        st.info("No unapplied fixable issues remain.")
        return

    try:
        results = fixer.apply_many_fixes_to_repo(Path(repo_path), pending, st.session_state.files_map)
    except Exception as e:
        st.error(f"Auto-fix failed unexpectedly: {e}")
        return
    applied = 0
    for res in results:
        vid = res.get("issue_id")
        if res.get("applied"):
            # Find the original issue to verify against it.
            iss = next((i for i in pending if i.get("issue_id") == vid), None)
            if iss is not None:
                ver = verifier.verify_fix(iss, res.get("changes", []), run_tests=False)
                ver.update(backup=str(res["backup"]), file=iss["file"],
                           post_hash=res.get("post_hash"), changes=res.get("changes", []))
                st.session_state.applied_issues[vid] = ver
                applied += 1
            else:
                st.session_state.applied_issues[vid] = {
                    "status": "NOT_VERIFIED", "verified": False,
                    "notes": ["Fix applied, verification skipped."],
                }
                applied += 1
    if applied:
        st.session_state.test_result = None
        _refresh_files_map(repo_path)
        _set_status(f"Automatically applied {applied} fix(es).")
        st.info(f"Applied {applied} fix(es) automatically "
                f"({len(results) - applied} could not be applied).")
    else:
        st.info("No fixes could be applied automatically.")


# ---------------------------------------------------------------------------
def tests_view(opts):
    st.markdown(C.page_head("🧪 Testing &amp; Verification", "Run your suite and verify fixes"), unsafe_allow_html=True)

    back_col, _ = st.columns([1, 5])
    with back_col:
        if _back_button(key="back_tests"):
            _go_back()

    st.write("")

    with st.expander("Generate a test draft"):
        files = st.session_state.files_map
        candidates = [p for p, f in files.items() if f.get("language") in
                      ("python", "javascript", "typescript", "java", "go", "rust")]
        if candidates:
            selected = st.selectbox("Source file", candidates)
            if st.button("Generate tests", disabled=not opts["enable_ai"]):
                from core.test_generator import detect_test_framework
                record = files[selected]
                framework = detect_test_framework(Path(st.session_state.repo_path), record["language"])
                with st.spinner("Generating test draft…"):
                    draft = TestGenerator(build_ai_provider(True)).generate_for_file(
                        record["content"], record["language"], framework, selected)
                st.session_state.generated_test = draft
            draft = st.session_state.generated_test
            if draft and draft.get("file_path") == selected and draft.get("success"):
                st.code(draft["test_code"], language=files[selected]["language"])
                st.download_button("Download test draft", draft["test_code"],
                                   file_name="test_" + Path(selected).name)
                st.caption("Review this draft before adding it to your repository.")
            elif draft and not draft.get("success"):
                st.error(draft.get("error", "Test generation failed."))
        else:
            st.info("No supported source files available for test generation.")

    test_result = st.session_state.test_result
    if test_result:
        C.metric_row({
            "Status": test_result["status"],
            "Tests": test_result.get("tests", 0),
            "Passed": test_result.get("passed", 0),
            "Failed": test_result.get("failed", 0),
        })
        st.markdown(f"**Framework:** {test_result.get('framework')} · **Duration:** {test_result.get('duration_ms')}ms")
        if test_result.get("stderr"):
            with st.expander("Test output (stderr)"):
                st.code(test_result["stderr"], language="")
        if test_result.get("stdout"):
            with st.expander("Test output (stdout)"):
                st.code(test_result["stdout"], language="")
    else:
        st.markdown(
            C.empty_state_html(
                "No tests have been run yet",
                "Run the suite from this view, or enable 'Run tests' on your next scan.",
                "🧪",
            ),
            unsafe_allow_html=True,
        )

    st.write("")
    if st.button("▶️ (Re)run Tests", type="primary", disabled=not opts["enable_tests"]):
        repo_path = st.session_state.repo_path
        if not repo_path:
            st.error("No repository workspace.")
            return
        runner = TestRunner(Path(repo_path))
        st.session_state.test_framework = runner.framework
        if not runner.available():
            st.warning(f"Test framework '{runner.framework}' not runnable here.")
            return
        with st.spinner("Running tests…"):
            res = runner.run(allow_execution=opts["enable_tests"])
        st.session_state.test_result = res
        _refresh_files_map(repo_path)
        if st.session_state.analysis is not None:
            st.session_state.analysis["test_result"] = res
        _set_status(f"Tests: {res['status']} ({res.get('passed')} passed, {res.get('failed')} failed).", "scan_complete")
        st.rerun()


# ---------------------------------------------------------------------------
def _back_button(label="← Back", key=None):
    """Render a consistent in-app 'Back' button styled for the dark/gold theme.

    ``key`` must be a stable, unique string per call site so the button never
    collides with other ``← Back`` buttons rendered in the same run (e.g. the
    error banner's back button), which would raise StreamlitDuplicateElementId.
    """
    return st.button(label, key=key, use_container_width=False)


def _friendly_ai_status(ai_status: str) -> str:
    """Turn an ``error:<kind>:<msg>`` status string into a user-friendly message."""
    if not isinstance(ai_status, str):
        return "AI provider unavailable."
    if ai_status.startswith("error:"):
        parts = ai_status.split(":", 2)
        kind = parts[1] if len(parts) > 1 else "provider"
        detail = parts[2] if len(parts) > 2 else ""
        friendly = {
            "rate_limit": "the AI provider is temporarily rate-limited",
            "quota": "the AI provider's quota/credits are exhausted",
            "authentication": "AI provider authentication failed (check the API key)",
            "model_unavailable": "the requested AI model is unavailable",
            "timeout": "the AI request timed out (the repository may be too large for AI analysis)",
            "provider": "the AI provider returned an error",
            "dependency": "an AI dependency is missing",
        }.get(kind, "the AI provider is unavailable")
        if detail:
            friendly = f"{friendly} ({detail})"
        return friendly
    return ai_status


def report_view(opts):
    st.markdown(C.page_head("📄 Final Report", "Professional repository health analysis"), unsafe_allow_html=True)

    back_col, _ = st.columns([1, 5])
    with back_col:
        if _back_button(key="back_report"):
            _go_back()

    st.write("")

    analysis = st.session_state.analysis
    if analysis is None:
        st.session_state.stage = "landing"
        st.rerun()

    summary = analysis["overall_summary"]
    health = Reporter.health_score(summary)

    colR, colM = st.columns([1, 2.5])
    with colR:
        st.markdown(C.health_ring(health), unsafe_allow_html=True)
    with colM:
        C.metric_row({
            "Health": f"{health:.0f}/100",
            "Issues": summary["total_issues"],
            "Security": summary["security_issues"],
            "Fixed": len(st.session_state.applied_issues),
            "Tests": (st.session_state.test_result or {}).get("status", "n/a"),
            "Files Scanned": summary.get("files_scanned", 0),
            "Lines of Code": summary.get("lines_of_code", 0),
        })

    tab1, tab2 = st.tabs(["📄 Markdown Report", "🔧 JSON Report"])
    with tab1:
        st.markdown("**Executive summary**")
        st.markdown(
            f"- **Repository:** `{analysis.get('repo')}`\n"
            f"- **Files scanned:** {summary.get('files_scanned',0)} / {summary.get('file_total',0)}\n"
            f"- **Lines of code:** {summary.get('lines_of_code',0)}\n"
            f"- **Total issues:** {summary.get('total_issues',0)} "
            f"(Critical {summary.get('critical',0)}, High {summary.get('high',0)}, "
            f"Medium {summary.get('medium',0)}, Low {summary.get('low',0)})\n"
            f"- **Security issues:** {summary.get('security_issues',0)}\n"
            f"- **Dependency issues:** {summary.get('dependency_issues',0)}\n"
            f"- **Fixes verified:** {sum(v.get('status') == 'PASS' for v in st.session_state.applied_issues.values())}\n",
        )
        md = st.session_state.raw_report
        st.download_button(
            "💾 Download Markdown Report", md, file_name="code_doctor_ai_report.md", mime="text/markdown",
        )
        with st.expander("Full markdown report"):
            st.markdown(md)
    with tab2:
        js = st.session_state.json_report
        st.download_button("💾 Download JSON Report", js, file_name="code_doctor_ai_report.json", mime="application/json")
        with st.expander("Full JSON report"):
            st.code(js, language="json")


# ---------------------------------------------------------------------------
def _inject_buddy_bar():
    status, kind = st.session_state.assistant_status
    st.markdown(inject_visuals(status, kind), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
def main():
    _inject_buddy_bar()
    opts = setup_sidebar()
    _sync_results()
    st.markdown(C.workspace_bar(st.session_state.stage, st.session_state.repo_owner_repo), unsafe_allow_html=True)

    if st.session_state.error:
        st.error(st.session_state.error)
        if st.session_state.stage != "landing":
            if st.button("← Back", key="error_back"):
                st.session_state.error = None
                st.session_state.stage = "landing"
                st.rerun()

    stage = st.session_state.stage
    if stage == "landing":
        landing_view(opts)
    elif stage == "scanning":
        scanning_view(opts)
    elif stage == "dashboard":
        dashboard_view(opts)
    elif stage == "issues":
        issues_view(opts)
    elif stage == "tests":
        tests_view(opts)
    elif stage == "report":
        report_view(opts)
    else:
        landing_view(opts)
    st.markdown('<div class="nt-footer"><span>≋ Code Doctor AI · Built for curious developers</span>'
                '<span>Discover → Review → Verify</span></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()

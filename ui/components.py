"""
Reusable UI components for Code Doctor AI.

These render consistent, themed Streamlit elements (glass cards, metric grids,
the health ring, professional issue cards, IDE-style code viewers, status
indicators) so app.py stays clean and the look stays consistent with the
premium black/gold/cyan identity. Only presentation lives here; the backend
data is never fabricated or modified.
"""
import html as _html

import streamlit as st

from config import Config

SEVERITY_LABEL = {
    "CRITICAL": ("🔴", "#ff5c5c"),
    "HIGH": ("🟠", "#ff9f43"),
    "MEDIUM": ("🟡", "#f2c14e"),
    "LOW": ("🔵", "#7fb3d5"),
    "INFO": ("⚪", "#9aa0a6"),
}

# Pygments is an existing dependency; use it only if importable.
try:
    from pygments import highlight as _pygments_highlight
    from pygments.lexers import Lexer, get_lexer_by_name, TextLexer
    from pygments.formatters import HtmlFormatter as _HtmlFormatter
    _PYGMENTS_HTML = _HtmlFormatter(nowrap=True, style="monokai")
    _PYGMENTS = True
except Exception:  # pragma: no cover - optional dependency
    _PYGMENTS = False

_LANG_LEXER = {
    "python": "python", "javascript": "javascript", "typescript": "typescript",
    "java": "java", "c": "c", "cpp": "cpp", "csharp": "csharp",
    "go": "go", "rust": "rust", "php": "php", "ruby": "ruby",
    "swift": "swift", "kotlin": "kotlin", "html": "html", "css": "css",
    "sql": "sql", "shell": "bash", "json": "json", "yaml": "yaml",
    "toml": "toml", "xml": "xml", "markdown": "markdown",
    "dockerfile": "dockerfile", "make": "make",
}


def _esc(value) -> str:
    return _html.escape(str(value), quote=True)


def esc(value) -> str:
    """Public alias of the HTML escaping helper used by app-level markup."""
    return _esc(value)


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.0f}" if value == int(value) else f"{value:,.1f}"
    return _esc(value)


# ---------------------------------------------------------------------------
# Cards & metrics
# ---------------------------------------------------------------------------
def card(title: str = "", key=None):
    """Open a themed card container. Kept for API compatibility."""
    return st.container(border=False)


_METRIC_ICONS = {
    "health": "💖", "issue": "🐛", "issues": "🐛", "total": "🌀",
    "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "➕",
    "security": "🛡️", "files": "📁", "files scanned": "📁",
    "fixed": "✅", "tests": "🧪", "passed": "✅", "failed": "❌",
    "status": "◉", "lines": "📄", "lines of code": "📄",
    "dependency": "📦", "dependencies": "📦", "complexity": "⚙️",
    "framework": "🔬", "duration": "⏱️",
}


def metric_row(metrics: dict, icons: dict = None):
    """Render a responsive row of metric cards as pure HTML."""
    if not metrics:
        return
    icons = icons or {}
    cells = []
    for label, value in metrics.items():
        icon = icons.get(label) or _METRIC_ICONS.get(str(label).strip().lower(), "✦")
        cells.append(
            '<div class="cd-metric">'
            '<div class="cd-metric-icon">' + icon + "</div>"
            '<div class="cd-metric-val">' + _fmt(value) + "</div>"
            '<div class="cd-metric-label">' + _esc(label) + "</div>"
            "</div>"
        )
    st.markdown('<div class="cd-metrics">' + "".join(cells) + "</div>", unsafe_allow_html=True)
    st.write("")


def health_ring(score: float) -> str:
    """Render a CSS ring gauge around a real health score (0-100)."""
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    pct = max(0.0, min(100.0, score))
    if pct >= 75:
        color = "#a5b0ff"
    elif pct >= 50:
        color = "#f2c14e"
    else:
        color = "#ff6b6b"
    return (
        '<div class="cd-ring-wrap">'
        '<div class="cd-ring" style="background:conic-gradient(' + color + " " + f"{pct:.0f}" + '%,rgba(255,255,255,.07) 0);">'
        '<div class="cd-ring-inner">'
        f'<div class="cd-ring-num">{pct:.0f}</div>'
        '<div class="cd-ring-cap">/ 100</div>'
        '<div class="cd-ring-lbl">CODE HEALTH</div>'
        "</div></div></div>"
    )


# ---------------------------------------------------------------------------
# Status indicators & chips
# ---------------------------------------------------------------------------
def status_indicator(label: str, state: str = "offline") -> str:
    """Small glowing status dot + label. State: online|busy|error|offline."""
    state = state if state in ("online", "busy", "error", "offline") else "offline"
    return (
        '<div class="cd-status cd-status-' + state + '">'
        '<span class="cd-s-dot"></span>'
        '<span class="cd-s-label">' + _esc(label) + "</span></div>"
    )


def status_row(items) -> str:
    """items: list of (label, state). Returns sidebar-ready status HTML grid."""
    return '<div class="cd-status-grid">' + "".join(status_indicator(label, state) for label, state in items) + "</div>"


def chip(text: str) -> str:
    return '<span class="cd-chip">' + _esc(text) + "</span>"


def lang_chips(lang_summary: dict):
    """Render detected languages as glowing chips."""
    if not lang_summary:
        return
    cells = []
    for lang, count in sorted(lang_summary.items(), key=lambda kv: kv[1], reverse=True):
        cells.append(
            '<span class="cd-chip"><span class="cd-lang-dot"></span>'
            + _esc(lang) + " <b>" + f"{count:,}" + "</b></span>"
        )
    st.markdown('<div class="cd-chips-row">' + "".join(cells) + "</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero & workflows
# ---------------------------------------------------------------------------
def hero_html() -> str:
    return (
        '<section class="nt-hero"><div class="nt-hero-copy">'
        '<div class="nt-eyebrow"><i></i> YOUR CODE. A CLEARER PICTURE.</div>'
        '<h1>Less guesswork.<br><em>More clarity.</em></h1>'
        '<p>Turn a GitHub repository into an organized workspace for findings, '
        'suggested fixes, and verification.</p>'
        '<div class="nt-hero-note">Explore the code. Understand the next move.</div></div>'
        '<div class="nt-scene" aria-hidden="true"><div class="nt-stack">'
        '<div class="nt-plane back"></div><div class="nt-plane mid"></div>'
        '<div class="nt-plane front"><div class="nt-window"><i></i><i></i><i></i>'
        '<span>code doctor ai / workspace</span></div>'
        '<div class="nt-code-art"><small>// follow the signal</small><br>'
        'repository <b>{</b><br>&nbsp; discover();<br>&nbsp; review();<br>'
        '&nbsp; verify();<br><b>}</b></div></div>'
        '<div class="nt-float-tag">◇ &nbsp; Trace. Understand. Improve.</div>'
        '</div></div></section>'
    )


def workspace_bar(stage: str, repo: str = "") -> str:
    labels = {"landing": "Overview", "scanning": "Scanning", "dashboard": "Analysis",
              "issues": "Issues", "tests": "Tests", "report": "Report"}
    return ('<div class="nt-topbar"><div>Workspace &nbsp; / &nbsp; <b>'
            + _esc(labels.get(stage, "Overview")) + '</b></div><span>'
            + _esc(repo or "CODE DOCTOR AI · CODE INTELLIGENCE") + '</span></div>')


def feature_grid() -> str:
    cards = [("01 / DISCOVER", "Give your code a second look", "Explore AI findings, security patterns, and dependency declarations in one place."),
             ("02 / UNDERSTAND", "From finding to context", "Filter by severity, inspect the source, and review the reasoning behind each suggestion."),
             ("03 / IMPROVE", "Make the next move", "Review suggested fixes, run trusted tests, and export a report you can share.")]
    return '<div class="nt-feature-grid">' + ''.join(
        '<article class="nt-feature"><small>' + _esc(k) + '</small><h3>'
        + _esc(t) + '</h3><p>' + _esc(d) + '</p></article>' for k, t, d in cards) + '</div>'


def workflow_html() -> str:
    steps = [
        ("🐙", "GitHub Repository"),
        ("📡", "Analyze"),
        ("🔍", "Detect Issues"),
        ("🛠️", "Fix"),
        ("🧪", "Run Tests"),
        ("✅", "Verify"),
    ]
    items = []
    for i, (ic, label) in enumerate(steps):
        if i:
            items.append('<span class="cd-flow-arrow">→</span>')
        items.append('<div class="cd-flow-step"><span class="cd-flow-ic">' + ic + "</span><span>" + _esc(label) + "</span></div>")
    return '<div class="cd-flow">' + "".join(items) + "</div>"


def input_card_head() -> str:
    return (
        '<div class="cd-upload-head">'
        '<div class="cd-upload-title">GitHub Repository</div>'
        '<div class="cd-upload-hint">Paste a public GitHub repository URL to start the scan.</div>'
        "</div>"
    )


def page_head(title: str, sub_html: str = "") -> str:
    sub = f'<div class="cd-page-sub">{sub_html}</div>' if sub_html else ""
    return f'<div class="cd-page-head"><div class="cd-page-title">{_esc(title)}</div>{sub}</div>'


# ---------------------------------------------------------------------------
# Code viewer (IDE-style)
# ---------------------------------------------------------------------------
def _highlight(code: str, lang: str) -> str:
    if _PYGMENTS:
        try:
            name = _LANG_LEXER.get(str(lang or "").lower())
            lexer = get_lexer_by_name(name) if name else TextLexer()
            return _pygments_highlight(code, lexer, _PYGMENTS_HTML).rstrip("\n")
        except Exception:
            pass
    return _esc(code)


def _editor_block(code: str, lang: str, hl_lines, base: int = 1, file: str = "", note: str = "") -> str:
    hl = set(hl_lines or [])
    lines = code.split("\n")
    tokens = _highlight(code, lang).split("\n")
    if len(tokens) < len(lines):
        tokens += [""] * (len(lines) - len(tokens))
    out = ['<div class="cd-code">']
    if file:
        out.append(
            '<div class="cd-code-head">'
            '<span class="cd-code-fname">' + (_esc(lang) + " " if lang else "") + _esc(file) + "</span>"
            '<span class="cd-code-fmeta">' + _esc(str(note)) + "</span></div>"
        )
    for i, line in enumerate(lines):
        n = base + i
        cls = "cd-code-l hl" if n in hl else "cd-code-l"
        body = tokens[i] if i < len(tokens) else _esc(line)
        if not body.strip():
            body = "&nbsp;"
        out.append('<div class="' + cls + '"><span class="cd-code-n">' + str(n) + "</span><code class=\"cd-code-c\">" + body + "</code></div>")
    out.append("</div>")
    return "".join(out)


def code_view(record: dict, highlight_lines=None, window: int = None):
    """Render a file's source as a modern IDE block with line numbers.

    ``window`` optionally shows only a few lines around the highlighted line
    to keep issue contexts light.
    """
    from utils.redaction import redact_text
    content = redact_text((record.get("content") or "").rstrip("\n")).split("\n")
    hl = set(highlight_lines or [])
    if not content or content == [""]:
        st.info("No source content available for this file.")
        return
    total = len(content)
    prefix = (record.get("path") or "")
    lang = record.get("language", "")
    if window and hl:
        target = min(sorted(hl))
        start = max(1, target - window)
        end = min(total, target + window)
        show = content[start - 1:end]
        hi = {l - start + 1 for l in hl if start <= l <= end}
        base = start
        note = f"· lines {start}–{end} of {total}"
    else:
        show, hi, base = content, hl, 1
        note = f"· {total} lines"
    st.markdown(_editor_block("\n".join(show), lang, hi, base=base, file=prefix, note=note), unsafe_allow_html=True)
    st.write("")


def before_after(original: str, new: str, language: str = "python"):
    """Render original vs proposed fix side by side."""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='cd-block-label' style='margin-top:0;'>Before</div>", unsafe_allow_html=True)
        st.code(original, language=language)
    with col2:
        st.markdown("<div class='cd-block-label' style='margin-top:0;'>After</div>", unsafe_allow_html=True)
        st.code(new, language=language)


# ---------------------------------------------------------------------------
# Issue cards
# ---------------------------------------------------------------------------
def _sev_class(severity: str) -> str:
    return "cd-sev-" + severity.lower()


def issue_badge(severity: str) -> str:
    sev = severity if severity in SEVERITY_LABEL else "INFO"
    mark, _ = SEVERITY_LABEL[sev]
    return f'<span class="cd-issue-badge cd-badge-{sev.lower()}">{_esc(mark)} {_esc(sev)}</span>'


def issue_detail_html(issue: dict) -> str:
    """Rich HTML body for one issue. Uses only real backend fields."""
    sev = issue.get("severity", "INFO")
    cat = issue.get("category", "OTHER")
    cat_emoji = Config.CATEGORIES.get(cat, "📋")
    title = issue.get("title", "Untitled issue")
    file = issue.get("file", "?")
    line = issue.get("line", "?")
    conf = issue.get("confidence", "n/a")
    source = issue.get("source", "")
    desc = issue.get("description", "")
    why = issue.get("why_it_matters", "")
    rec_fix = issue.get("recommended_fix", "")
    vm = issue.get("verification_method", "")

    parts = ['<div class="cd-issue ' + _sev_class(sev) + '">']
    parts.append(
        '<div class="cd-issue-head">' + issue_badge(sev)
        + '<span class="cd-issue-title">' + _esc(cat_emoji + " ") + _esc(title) + "</span></div>"
    )
    parts.append(
        '<div class="cd-issue-meta">'
        + chip("📁 " + file)
        + chip("→ " + str(line))
        + chip("🏷️ " + cat)
        + (chip("🎯 " + source) if source else "")
        + chip("◉ " + str(conf))
        + "</div>"
    )
    if desc:
        parts.append('<div class="cd-issue-desc">' + _esc(desc) + "</div>")
    if why:
        parts.append(
            '<div class="cd-detail"><div class="cd-detail-label">Why this matters</div>'
            '<div class="cd-detail-body">' + _esc(why).replace("\n", "<br/>") + "</div></div>"
        )
    if rec_fix:
        parts.append(
            '<div class="cd-detail"><div class="cd-detail-label">Suggested fix</div>'
            '<div class="cd-fix-block"><code>' + _esc(rec_fix) + "</code></div></div>"
        )
    if vm:
        parts.append(
            '<div class="cd-detail"><div class="cd-detail-label">Verification method</div>'
            '<div class="cd-detail-body">' + _esc(vm) + "</div></div>"
        )
    parts.append("</div>")
    return "".join(parts)


def issue_card(issue: dict, index: int):
    """Backward-compatible single-issue renderer. Returns the header string."""
    sever = issue.get("severity", "INFO")
    mark, _ = SEVERITY_LABEL.get(sever, ("⚪", "#9aa0a6"))
    cat = issue.get("category", "OTHER")
    cat_emoji = Config.CATEGORIES.get(cat, "📋")
    title = issue.get("title", "Untitled issue")
    file = issue.get("file", "?")
    line = issue.get("line", "?")
    header = f"{mark} **#{index}** {cat_emoji} {title} — {sever} · `{file}:{line}`"
    with st.expander(header, expanded=sever in ("CRITICAL", "HIGH")):
        st.markdown(issue_detail_html(issue), unsafe_allow_html=True)
        if issue.get("evidence"):
            st.markdown("<div class='cd-block-label'>Evidence</div>", unsafe_allow_html=True)
            st.code(issue["evidence"], language="")
    return header


# ---------------------------------------------------------------------------
# Scanning panel / misc
# ---------------------------------------------------------------------------
def scan_panel_html() -> str:
    return (
        '<div class="cd-scan">'
        '<div class="cd-scan-ring"><span></span><span></span><span></span></div>'
        '<div class="cd-scan-title">Code Doctor AI is Analyzing…</div>'
        '<div class="cd-scan-target">Live repository deep-scan in progress</div>'
        "</div>"
    )


def empty_state_html(title: str, hint: str = "", icon: str = "🌌") -> str:
    """Glass empty/error-state panel for honest 'nothing here yet' outcomes."""
    hint_html = f'<div class="cd-empty-hint">{_esc(hint)}</div>' if hint else ""
    return (
        '<div class="cd-empty">'
        f'<div class="cd-empty-ic">{icon}</div>'
        f'<div class="cd-empty-title">{_esc(title)}</div>'
        + hint_html
        + "</div>"
    )


def status_badge(status: str) -> str:
    colors = {"PASS": "#2ecc71", "FAIL": "#ff5c5c", "BLOCKED": "#f2c14e", "NOT_VERIFIED": "#9aa0a6"}
    color = colors.get(status, "#9aa0a6")
    return '<span class="cd-issue-badge" style="background:rgba(255,255,255,.06);color:' + color + ';border:1px solid ' + color + ';">' + _esc(status) + "</span>"


def progress_lines(stages: list):
    """Backward-compatible progress checklist renderer."""
    for done, label in stages:
        icon = "✅" if done else ("⏳" if not done and label else "○")
        st.markdown(f"{icon} {label}")


def section(title: str, emoji: str = ""):
    icon = emoji + " " if emoji else ""
    st.markdown('<div class="cd-section">' + icon + _esc(title) + "</div>", unsafe_allow_html=True)
    st.write("")

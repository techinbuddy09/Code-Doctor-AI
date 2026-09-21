"""
Fix engine for Code Doctor AI.

Applies MINIMAL, targeted changes rather than rewriting whole files. Provides a
backup mechanism, syntax validation after edits, and a deterministic patch model
for fixing security issues (masked secrets replaced with env-var references),
as well as an optional AI-driven whole-snippet rewrite for complex fixes.
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from .ai_provider import AIProvider, classify_provider_error


@dataclass
class AppliedChange:
    file: str
    line: int
    original: str
    new: str
    reason: str
    risk: str = "low"
    verification: str = "NOT_VERIFIED"


class CodeFixer:
    """Apply fixes to files (or snippet text) and validate them."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai_provider = ai_provider

    # ------------------------------------------------------------------
    # Repository-level fixing
    # ------------------------------------------------------------------
    def apply_fix_to_repo(self, repo_root: Path, issue: Dict[str, Any],
                          files_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Apply a single deterministic fix for the given issue."""
        repo_root = repo_root.resolve()
        rel_path = issue.get("file")
        if not rel_path:
            return {"applied": False, "error": "Issue has no associated file."}

        absolute = (repo_root / rel_path).resolve() if rel_path != "<input>" else None
        if absolute is None or not absolute.exists() or not _is_within(repo_root, absolute):
            return {"applied": False, "error": "Unsafe or missing target file path."}

        source = issue.get("source")
        result = {"applied": False, "changes": []}

        # Attempt a deterministic fix for a known issue source.
        if source == "security":
            fix_result = self._fix_security(repo_root, absolute, issue)
            if fix_result["applied"]:
                return fix_result

        # Fallback: AI full-file rewrite for fixable issues.
        if self.ai_provider is not None:
            return self._ai_fix_repo(repo_root, absolute, issue)

        return {"applied": False, "error": "No deterministic or AI fix available."}

    def apply_many_fixes_to_repo(self, repo_root: Path,
                                 issues: List[Dict[str, Any]],
                                 files_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply fixes for MANY issues, batching AI rewrites per file.

        Deterministic security fixes are applied individually. AI-driven rewrites
        are grouped by file so a single ``fix_code`` request handles every AI-fixable
        issue in that file (instead of one request per issue), reducing API/rate-limit
        pressure. ``files_map`` is the parsed file records; the list returned matches
        the input ``issues`` order with an ``applied``/``error`` result per issue.
        """
        repo_root = repo_root.resolve()
        results: List[Dict[str, Any]] = []
        security_batches: List[Dict[str, Any]] = []
        ai_batches: Dict[str, List[Dict[str, Any]]] = {}  # file -> issues

        for issue in issues:
            if issue.get("source") == "security":
                security_batches.append(issue)
            else:
                fpath = issue.get("file")
                if fpath:
                    ai_batches.setdefault(fpath, []).append(issue)

        applied_by_id: Dict[str, bool] = {}

        # Deterministic security fixes insert lines (e.g. an env-var read plus a
        # TODO comment), which shifts the stored line numbers of later issues in
        # the SAME file. Group by file and track a cumulative line offset so every
        # issue is fixed at the correct (currently valid) line.
        from collections import defaultdict as _defaultdict
        security_by_file: Dict[Optional[str], List[Dict[str, Any]]] = _defaultdict(list)
        for issue in security_batches:
            security_by_file[issue.get("file")].append(issue)

        for _fpath, batch in security_by_file.items():
            offset = 0
            for issue in sorted(batch, key=lambda i: i.get("line", 1)):
                if offset:
                    issue = dict(issue)
                    base = issue.get("line", 1)
                    issue["line"] = base + offset
                    if issue.get("line_end"):
                        issue["line_end"] = issue["line_end"] + offset
                target = (repo_root / issue.get("file", "")).resolve() if issue.get("file") else None
                before = _count_lines(target) if target and _is_within(repo_root, target) else 0
                res = self.apply_fix_to_repo(repo_root, issue, files_map)
                if res.get("applied"):
                    import hashlib
                    res["post_hash"] = hashlib.sha256(target.read_bytes()).hexdigest()
                applied_by_id[issue.get("issue_id")] = res.get("applied", False)
                results.append({"issue_id": issue.get("issue_id"), **res})
                if res.get("applied"):
                    after = _count_lines(target) if target and _is_within(repo_root, target) else before
                    offset += max(0, after - before)

        for fpath, batch in ai_batches.items():
            absolute = (repo_root / fpath).resolve()
            if absolute is None or not absolute.exists() or not _is_within(repo_root, absolute):
                for issue in batch:
                    applied_by_id[issue.get("issue_id")] = False
                    results.append({"issue_id": issue.get("issue_id"),
                                    "applied": False, "changes": [],
                                    "error": "Unsafe or missing target file path."})
                continue
            batch_res = self._ai_fix_many(repo_root, absolute, batch)
            if batch_res.get("applied"):
                import hashlib
                batch_res["post_hash"] = hashlib.sha256(absolute.read_bytes()).hexdigest()
            # Apply the same file-level result to each issue in the batch.
            if batch_res.get("applied"):
                for issue in batch:
                    applied_by_id[issue.get("issue_id")] = True
                    results.append({"issue_id": issue.get("issue_id"), **batch_res,
                                    "changes": batch_res.get("changes", [])})
            else:
                for issue in batch:
                    applied_by_id[issue.get("issue_id")] = False
                    results.append({"issue_id": issue.get("issue_id"), **batch_res})

        return results

    def _ai_fix_many(self, repo_root: Path, absolute: Path,
                     issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI-rewrite a single file to fix ALL of its issues in one request."""
        try:
            original_text = absolute.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"applied": False, "error": f"Could not read file: {e}"}

        language = issues[0].get("language") if issues else "text"
        try:
            fixed = self.ai_provider.fix_code(original_text, language, issues)
        except Exception as e:
            msg, kind = classify_provider_error(e)
            return {"applied": False, "error": _fix_error_message(msg, kind)}

        if not fixed or fixed.strip() == original_text.strip():
            return {"applied": False, "error": "AI produced no change."}

        if not self._validate_syntax(fixed, issues[0].get("file") if issues else None):
            return {"applied": False, "error": "AI fix produced invalid syntax; not applied."}

        backup = self._backup(repo_root, absolute)
        absolute.write_text(fixed, encoding="utf-8")
        return {
            "applied": True,
            "backup": backup,
            "changes": [{"file": issues[0].get("file"), "line": issues[0].get("line"),
                         "original": "<file rewritten>", "new": "<rewritten>",
                         "reason": f"AI-driven fix applied for {len(issues)} issue(s).",
                         "risk": "medium", "verification": "NOT_VERIFIED"}],
        }

    def _fix_security(self, repo_root: Path, absolute: Path,
                      issue: Dict[str, Any]) -> Dict[str, Any]:
        """Replace hardcoded secret literals with environment-variable reads."""
        if "credential" not in issue.get("title", "").lower() and \
           "hardcoded" not in issue.get("title", "").lower():
            return {"applied": False, "error": "not_a_secret_fix"}
        if absolute.suffix.lower() != ".py":
            return {"applied": False, "error": "Deterministic credential fixes support Python only."}

        try:
            original_text = absolute.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"applied": False, "error": f"Could not read file: {e}"}

        text = original_text
        changes: List[AppliedChange] = []
        line = issue.get("line", 1)
        lines = text.split("\n")
        if issue.get("source_line_hash"):
            import hashlib
            matches = [i + 1 for i, value in enumerate(lines)
                       if hashlib.sha256(value.encode()).hexdigest() == issue["source_line_hash"]]
            if len(matches) != 1:
                return {"applied": False, "error": "Source changed or is ambiguous. Rescan before applying this fix."}
            line = matches[0]
        if line < 1 or line > len(lines):
            return {"applied": False, "error": "Line out of range."}

        old_line = lines[line - 1]
        new_line = _replace_secret_assignment(old_line)

        if new_line == old_line:
            return {"applied": False, "error": "Could not locate a secret to replace."}

        lines[line - 1] = new_line
        text = _ensure_os_import("\n".join(lines))

        if not self._validate_syntax(text, issue.get("file")):
            return {"applied": False, "error": "Fix produced invalid syntax; not applied."}

        backup = self._backup(repo_root, absolute)
        absolute.write_text(text, encoding="utf-8")

        changes.append(AppliedChange(
            file=issue.get("file"), line=line,
            original="<credential redacted>", new=new_line,
            reason="Replaced hardcoded credential with environment variable read.",
            risk="low", verification="NOT_VERIFIED",
        ))
        return {"applied": True, "backup": backup, "changes": [asdict(c) for c in changes]}

    def _ai_fix_repo(self, repo_root: Path, absolute: Path,
                     issue: Dict[str, Any]) -> Dict[str, Any]:
        try:
            original_text = absolute.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"applied": False, "error": f"Could not read file: {e}"}

        try:
            fixed = self.ai_provider.fix_code(original_text, issue.get("language", "text"), [issue])
        except Exception as e:
            msg, kind = classify_provider_error(e)
            return {"applied": False, "error": _fix_error_message(msg, kind)}

        if not fixed or fixed.strip() == original_text.strip():
            return {"applied": False, "error": "AI produced no change."}

        if not self._validate_syntax(fixed, issue.get("file")):
            return {"applied": False, "error": "AI fix produced invalid syntax; not applied."}

        backup = self._backup(repo_root, absolute)
        absolute.write_text(fixed, encoding="utf-8")
        return {
            "applied": True,
            "backup": backup,
            "changes": [{"file": issue.get("file"), "line": issue.get("line"),
                         "original": "<file rewritten>", "new": "<rewritten>",
                         "reason": "AI-driven fix applied.", "risk": "medium",
                         "verification": "NOT_VERIFIED"}],
        }

    def _backup(self, repo_root: Path, absolute: Path) -> Path:
        repo_root = repo_root.resolve()
        backup_dir = repo_root / ".codedoctor_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        from uuid import uuid4
        backup = backup_dir / f"{uuid4().hex}.bak"
        # Do not change the source if a recoverable backup cannot be written.
        backup.write_bytes(absolute.read_bytes())
        return backup

    # ------------------------------------------------------------------
    # Snippet-level fixing (legacy / paste flow)
    # ------------------------------------------------------------------
    def fix_code(self, code: str, language: str, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a fixed snippet. Deterministic secret-fix first, AI fallback."""
        result = {"success": False, "fixed_code": "", "explanation": "", "changes": []}

        if not issues:
            result.update(success=True, fixed_code=code,
                          explanation="No issues found. Code looks good!")
            return result

        # Try deterministic replacement of secret literals.
        new_code = code
        if language.lower() == "python":
            try:
                new_code = _replace_all_secret_assignments(code)
            except SyntaxError:
                pass  # Syntax problems require a separate fix, not a credential patch.
        if new_code != code:
            result["success"] = True
            result["fixed_code"] = new_code
            result["explanation"] = "Replaced hardcoded credentials with environment variable reads."
            result["changes"] = ["Replaced hardcoded secret(s) with os.environ lookups."]
            return result

        if self.ai_provider is None:
            result["error"] = "AI provider not configured for non-deterministic fixes."
            return result

        try:
            fixed = self.ai_provider.fix_code(code, language, issues)
            result["success"] = True
            result["fixed_code"] = fixed
            result["explanation"] = f"Fixed {len(issues)} issue(s)."
            result["changes"] = _diff_lines(code, fixed)
        except Exception as e:
            msg, _ = classify_provider_error(e)
            result["error"] = msg
        return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_syntax(self, text: str, filename: Optional[str]) -> bool:
        name = (filename or "").lower()
        if name.endswith(".py"):
            return _validate_python(text)
        if name.endswith((".js", ".ts", ".jsx", ".tsx", ".json")):
            return _validate_json(text) if name.endswith(".json") else True
        return True


def _validate_python(text: str) -> bool:
    try:
        compile(text, "<fixer>", "exec")
        return True
    except SyntaxError:
        return False


def _validate_json(text: str) -> bool:
    import json
    try:
        json.loads(text)
        return True
    except Exception:
        return False


def _replace_secret_assignment(line: str) -> str:
    """Replace a `KEY = "secret"` line with an os.environ lookup. Python-targeted."""
    import re
    m = re.match(r'^(\s*)([A-Za-z_][\w]*)\s*=\s*(["\'])([^"\'\n]{2,})\3\s*(?:#.*)?$', line)
    if not m:
        return line
    var = m.group(2)
    if not re.search(r'(?i)(password|passwd|pwd|secret|api_?key|token|auth|private_?key)', var):
        return line
    indent = m.group(1)
    env_var = var.upper()
    return (
        f"{indent}{var} = os.environ.get(\"{env_var}\", \"\")\n"
        f"{indent}# TODO: set {env_var} in your environment / CI"
    )


def _replace_all_secret_assignments(code: str) -> str:
    lines = code.split("\n")
    changed = False
    for i, line in enumerate(lines):
        new = _replace_secret_assignment(line)
        if new != line:
            lines[i] = new
            changed = True
    text = "\n".join(lines)
    return _ensure_os_import(text) if changed else text


def _ensure_os_import(code: str) -> str:
    """Insert a module import after the docstring and future imports."""
    import ast
    tree = ast.parse(code)
    if any(isinstance(n, ast.Import) and any(
        a.name == "os" and a.asname in (None, "os") for a in n.names
    ) for n in tree.body):
        return code
    position = 0
    for i, node in enumerate(tree.body):
        if (i == 0 and isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            position = node.end_lineno
        elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
            position = node.end_lineno
        else:
            break
    lines = code.splitlines(keepends=True)
    lines.insert(position, "import os\n")
    return "".join(lines)


def _diff_lines(original: str, fixed: str) -> List[str]:
    changes = []
    orig = original.split("\n")
    fix = fixed.split("\n")
    for i, (o, f) in enumerate(zip(orig, fix), 1):
        if o != f:
            changes.append(f"Line {i} modified.")
    if len(orig) != len(fix):
        changes.append(f"Line count changed from {len(orig)} to {len(fix)}.")
    return changes[:20]


def _is_within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _count_lines(path: Path) -> int:
    """Return the number of lines in a file (0 when unreadable)."""
    if path is None:
        return 0
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").split("\n"))
    except OSError:
        return 0


def _fix_error_message(msg: str, kind: str) -> str:
    """Return a clear, graceful error message for a failed AI fix.

    Rate-limits are transient and should not read as a broken fix — we tell the
    user to retry shortly while reassuring them the rest of the app still works.
    Other provider errors keep their original detail.
    """
    if kind == "rate_limit":
        return (
            "AI fix is temporarily rate-limited by the provider. Please try again "
            "shortly. All static, security & dependency results remain available."
        )
    if kind == "quota":
        return (
            "AI fix could not run: the provider's quota/credits are exhausted. "
            "Local static, security & dependency fixes are unaffected."
        )
    if kind == "authentication":
        return (
            "AI fix could not run: provider authentication failed. Check the "
            "API key. Local static, security & dependency fixes are unaffected."
        )
    if kind == "timeout":
        return (
            "AI fix timed out — the file may be too large for a single AI request. "
            "Try fixing a smaller file, or increase AI_REQUEST_TIMEOUT. "
            "Local static, security & dependency fixes are unaffected."
        )
    return f"AI fix failed: {msg}"

"""
Verification engine for Code Doctor AI.

Distinguishes PASS / FAIL / BLOCKED / NOT_VERIFIED. After a fix is applied it
(optionally) validates syntax, then re-runs the relevant test suite to confirm
the change did not break anything.
"""
from pathlib import Path
from typing import Dict, Any, Optional

from .test_runner import TestRunner


class Verifier:
    """Verify that a fix resolved an issue without breaking the project."""

    def __init__(self, root: Path):
        self.root = root

    def verify_fix(self, issue: Dict[str, Any], applied_changes: list,
                   run_tests: bool = False) -> Dict[str, Any]:
        verification_method = issue.get("verification_method", "")
        verified = False
        notes = []

        # Metadata and passing unrelated tests are not evidence of resolution.
        from .fixer import _is_within
        target = (self.root / issue.get("file", "")).resolve()
        if applied_changes and _is_within(self.root, target) and target.is_file():
            code = target.read_text(encoding="utf-8")
            if not self.verify_syntax(code, target.name):
                return {"status": "FAIL", "verified": False,
                        "notes": ["Changed file has invalid syntax."],
                        "test_result": None, "method": verification_method}
            if issue.get("source") == "security":
                from .security_scanner import SecurityScanner, PATTERNS
                from .code_parser import CodeParser
                language = CodeParser().detect_language(target)
                remaining = SecurityScanner().scan_code(code, language, path=issue.get("file"))
                title = issue.get("title", "")
                if title.lower().startswith("hardcoded"):
                    verified = not any(i.get("title", "").lower().startswith("hardcoded") for i in remaining)
                elif title in {p["title"] for p in PATTERNS}:
                    verified = not any(i.get("title") == title for i in remaining)
                notes.append("Re-ran the security check on the changed file.")
            elif issue.get("source") == "parser" and issue.get("title") == "Syntax error":
                verified = target.suffix.lower() in (".py", ".json")
            if not verified:
                notes.append("Issue resolution has not been established by a deterministic check.")
        else:
            notes.append("No applied change and readable target file available to verify.")

        # Run tests to confirm nothing broke.
        test_result = None
        if run_tests:
            runner = TestRunner(self.root)
            if runner.available():
                test_result = runner.run(allow_execution=True)
                if test_result["status"] in ("PASS", "FAIL"):
                    notes.append(
                        f"Ran '{test_result['framework']}': {test_result['passed']} "
                        f"passed, {test_result['failed']} failed."
                    )
                else:
                    notes.append(f"Tests blocked: {test_result.get('reason')}")
            else:
                notes.append("No testable framework detected; skipped test run.")

        status = self._final_status(verified, test_result, issue)
        return {
            "status": status,
            "verified": verified and status == "PASS",
            "notes": notes,
            "test_result": test_result,
            "method": verification_method,
        }

    def _final_status(self, verified: bool, test_result: Optional[Dict], issue) -> str:
        if test_result is not None and test_result.get("status") == "BLOCKED":
            return "BLOCKED"
        if test_result is not None and test_result.get("status") == "FAIL":
            # Fix made tests fail -> not verified.
            return "FAIL"
        if verified:
            return "PASS"
        return "NOT_VERIFIED"

    def verify_syntax(self, code: str, filename: str) -> bool:
        name = (filename or "").lower()
        if name.endswith(".py"):
            try:
                compile(code, "<verify>", "exec")
                return True
            except SyntaxError:
                return False
        if name.endswith(".json"):
            import json
            try:
                json.loads(code)
                return True
            except Exception:
                return False
        return True

from unittest.mock import Mock

import pytest

from core.ai_provider import AIProvider
from core.analyzer import CodeAnalyzer
from core.security_scanner import SecurityScanner


@pytest.mark.parametrize("title", ["Syntax Error / Truncated Code", "Truncated source code file", "SyntaxError"])
def test_full_source_overrules_ai_syntax_claim(tmp_path, title):
    (tmp_path / "app.py").write_text("def ready():\n    return True\n")
    provider = Mock()
    provider.analyze_many_batched.return_value = {"issues": [
        {"file": "app.py", "line": 2, "title": title, "severity": "CRITICAL"},
        {"file": "app.py", "line": 2, "title": "Incorrect return value", "severity": "HIGH"},
    ]}
    result = CodeAnalyzer(provider).analyze_repository(tmp_path, "o/r")
    assert len(result["ai_issues"]) == 1
    assert result["ai_issues"][0]["title"] == "Incorrect return value"
    assert len(result["ai_rejected_issues"]) == 1
    assert result["overall_summary"]["critical"] == 0


def test_genuine_python_syntax_error_is_retained(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:\n")
    provider = Mock()
    provider.analyze_many_batched.return_value = {"issues": [
        {"file": "broken.py", "line": 1, "title": "Syntax error", "severity": "CRITICAL"}]}
    result = CodeAnalyzer(provider).analyze_repository(tmp_path, "o/r")
    assert not result["ai_rejected_issues"]
    assert result["ai_issues"]
    assert any(i["source"] == "parser" for i in result["issues"])


def test_excerpt_has_coverage_and_complete_lines():
    provider = Mock()
    provider.complete.return_value = '{"issues": []}'
    provider._extract_json = lambda text, default: {"issues": []}
    AIProvider.analyze_many(provider, [{"path": "a.py", "content": "x = 1\ny = 2\nz = 3\n"}], max_chars_per_file=10)
    system, prompt = provider.complete.call_args.args
    assert "PARTIAL EXCERPT" in prompt
    assert "Never report truncation" in system
    assert "x = 1\n" in prompt
    assert "y = " not in prompt


def test_strings_and_comments_are_not_executable_calls():
    code = 'rule = "Avoid eval() and exec()"\n# os.system(user)\nresult = eval(user)\n'
    issues = SecurityScanner().scan_code(code, "python", path="rules.py")
    assert [(i["title"], i["line"]) for i in issues] == [("Use of eval()", 3)]


def test_sql_rule_string_is_not_a_query():
    code = "rules = " + repr({"regex": r'''['"].*SELECT.*['"].*\+'''})
    assert not SecurityScanner().scan_code(code, "python", path="rules.py")


def test_dynamic_syntax_error_claim_is_not_discarded():
    record = {"success": True, "language": "python", "path": "a.py", "content": 'eval("broken(")'}
    issue = {"title": "SyntaxError from eval()", "description": "The dynamically evaluated string is invalid."}
    assert not CodeAnalyzer._contradicts_python_syntax(issue, record)


def test_dynamic_execution_in_test_file_is_still_high():
    issues = SecurityScanner().scan_code("eval(user_input)", "python", path="tests/test_real.py")
    assert issues[0]["severity"] == "HIGH"


def test_fstring_interpolation_is_not_hidden():
    issues = SecurityScanner().scan_code('message = f"{eval(user_input)}"', "python", path="a.py")
    assert any(i["title"] == "Use of eval()" for i in issues)


def test_placeholder_is_informational_but_real_looking_key_stays_high():
    scanner = SecurityScanner()
    examples = scanner.scan_code('OPENAI_API_KEY=sk-your-openai-key-here', "markdown", path="SETUP.md")
    assert examples and all(i["severity"] == "INFO" and not i["fixable"] for i in examples)
    real = scanner.scan_code('API_KEY = "sk-ZxYqPnRtVmAbCdEfGhIjKlMn"', "python", path="tests/test_keys.py")
    assert real and all(i["severity"] == "HIGH" for i in real)


def test_synthetic_test_secret_remains_visible_as_info():
    issues = SecurityScanner().scan_code('TOKEN = "ghp_1234567890abcdefghij"', "python", path="tests/test_keys.py")
    assert issues and all(i["severity"] == "INFO" for i in issues)


@pytest.mark.parametrize("title, code, rejected", [
    ("Reference to Undefined Function `_is_within`", "def caller():\n    return _is_within()\ndef _is_within():\n    return True\n", True),
    ("Reference to Undefined Function `_is_within`", "def caller():\n    return _is_within()\n", False),
    ("Reference to Undefined Function `_is_within`", "def caller():\n    print(_is_within())\n    _is_within = 1\ndef _is_within():\n    return True\n", False),
    ("Unused Import `asdict`", "from dataclasses import asdict\ndef serialize(item):\n    return asdict(item)\n", True),
    ("Unused Import `asdict`", "from dataclasses import asdict\nvalue = 1\n", False),
    ("Unused Import `asdict`", "from dataclasses import asdict\ndef serialize(asdict):\n    return asdict\n", False),
])
def test_complete_file_symbol_validation(title, code, rejected):
    from core.python_validation import contradicted_symbol_claim
    record = {"language": "python", "success": True, "content": code, "path": "a.py"}
    assert bool(contradicted_symbol_claim({"title": title}, record)) == rejected


def test_symbol_claims_are_recorded_as_excluded(tmp_path):
    (tmp_path / "a.py").write_text("from dataclasses import asdict\ndef serialize(item):\n    return asdict(item)\n")
    provider = Mock()
    provider.analyze_many_batched.return_value = {"issues": [
        {"file": "a.py", "line": 1, "title": "Unused Import `asdict`", "severity": "LOW"}]}
    result = CodeAnalyzer(provider).analyze_repository(tmp_path, "o/r")
    assert not result["ai_issues"]
    assert "asdict" in result["ai_rejected_issues"][0]["rejection_reason"]

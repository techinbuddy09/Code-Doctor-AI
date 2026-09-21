"""Tests for the AI provider factory and provider configuration."""
import pytest

from core.ai_provider import (
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    AIProvider,
    create_ai_provider,
    AuthenticationError,
    ModelUnavailableError,
    classify_provider_error,
)
from core.ai_provider import ProviderError


def test_create_openai_provider_honors_extra_model():
    """OPENAI_MODEL (extra_model) must take precedence over the generic model."""
    provider = create_ai_provider(
        "openai",
        "",                       # AI_API_KEY empty
        "",                       # AI_MODEL empty
        extra_key="sk-test-openai-key",
        extra_model="gpt-4o-mini",
    )
    assert isinstance(provider, OpenAIProvider)
    assert provider.provider_name == "openai"
    assert provider.model == "gpt-4o-mini"


def test_create_openai_provider_falls_back_to_generic_model():
    """When OPENAI_MODEL is empty, fall back to the generic model."""
    provider = create_ai_provider(
        "openai",
        "",
        "gpt-4-turbo",            # generic model
        extra_key="sk-test-openai-key",
        extra_model="",
    )
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4-turbo"


def test_create_openai_provider_default_model():
    """With no models configured, default to gpt-4o."""
    provider = create_ai_provider(
        "openai",
        "",
        "",
        extra_key="sk-test-openai-key",
        extra_model="",
    )
    assert provider.model == "gpt-4o"


def test_create_provider_missing_key_raises():
    """No key anywhere should raise AuthenticationError (no silent misconfig)."""
    with pytest.raises(AuthenticationError):
        create_ai_provider("openai", "", "", extra_key="", extra_model="")


def test_openai_provider_requires_package(monkeypatch):
    """Simulate the openai package being missing -> ProviderError, not raw crash."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    # Re-import the module so its module-level `openai` reference is not cached.
    import importlib
    import core.ai_provider as ap
    importlib.reload(ap)

    with pytest.raises(ap.ProviderError):
        ap.OpenAIProvider("sk-test-key", "gpt-4o")

    monkeypatch.undo()


def test_classify_model_unavailable_requires_not():
    """'model ... not ... found' should classify as model_unavailable."""
    class Fake:
        def __init__(self, msg):
            self.message = msg
        def __str__(self):
            return self.message
    msg, kind = classify_provider_error(Fake("anthropic: model not found"))
    assert kind == "model_unavailable"


def test_classify_rate_limit():
    class Fake:
        def __str__(self):
            return "Rate limit hit: 429 too many requests"
    msg, kind = classify_provider_error(Fake())
    assert kind == "rate_limit"


def test_classify_authentication_error_passthrough():
    import core.ai_provider as ap
    err = ap.AuthenticationError("bad key")
    msg, kind = classify_provider_error(err)
    assert kind == "authentication"
    assert "key" in msg.lower()


def test_model_unavailable_error_kind():
    import core.ai_provider as ap
    err = ap.ModelUnavailableError()
    assert err.kind == "model_unavailable"


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

def test_create_gemini_provider_defaults():
    """Gemini provider defaults to gemini-3.5-flash-lite model."""
    provider = GeminiProvider("sk-gemini-test-key")
    assert isinstance(provider, GeminiProvider)
    assert provider.provider_name == "gemini"
    assert provider.model == "gemini-3.5-flash-lite"


def test_create_gemini_provider_timeout_applied_in_milliseconds():
    """HttpOptions.timeout is in MILLISECONDS in google-genai >=2.23; a 180s
    config must translate to 180000ms, otherwise every request times out."""
    from core.ai_provider import GeminiProvider
    from config import Config

    provider = GeminiProvider("sk-gemini-test-key")  # uses Config.AI_REQUEST_TIMEOUT
    ms = provider.client._api_client._http_options.timeout
    assert ms == int(Config.AI_REQUEST_TIMEOUT * 1000)
    assert ms >= 1000, "timeout must be at least 1 second, not milliseconds-as-seconds"


def test_create_gemini_provider_custom_timeout_in_milliseconds():
    """An explicit timeout=30 (seconds) must be stored as 30000ms on the SDK client."""
    from core.ai_provider import GeminiProvider

    provider = GeminiProvider("sk-gemini-test-key", timeout=30)
    ms = provider.client._api_client._http_options.timeout
    assert ms == 30000


def test_create_gemini_provider_custom():
    provider = GeminiProvider("sk-gemini-test-key", model="gemini-2.5-flash")
    assert provider.model == "gemini-2.5-flash"


def test_create_gemini_missing_key_raises():
    import core.ai_provider as ap
    with pytest.raises(ap.AuthenticationError):
        ap.GeminiProvider("")


def test_create_gemini_requires_package(monkeypatch):
    """Missing google-genai package -> ProviderError, not a raw crash."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "google" or name == "google.genai":
            raise ImportError("No module named 'google'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    import importlib
    import core.ai_provider as ap
    importlib.reload(ap)

    with pytest.raises(ap.ProviderError):
        ap.GeminiProvider("sk-gemini-test-key")

    monkeypatch.undo()


def test_factory_gemini_via_key():
    """Factory returns a GeminiProvider when gemini_key is provided."""
    import core.ai_provider as ap
    provider = ap.create_ai_provider(
        "gemini",
        "", "", "",
        gemini_key="sk-gemini-test-key",
    )
    assert isinstance(provider, ap.GeminiProvider)
    assert provider.model == "gemini-3.5-flash-lite"


def test_factory_gemini_uses_model():
    import core.ai_provider as ap
    provider = ap.create_ai_provider(
        "gemini",
        "", "", "",
        gemini_key="sk-gemini-test-key",
        gemini_model="gemini-2.5-flash",
    )
    assert isinstance(provider, ap.GeminiProvider)
    assert provider.model == "gemini-2.5-flash"


def test_factory_auto_prefers_gemini():
    """With 'auto', the Gemini key is chosen first."""
    import core.ai_provider as ap
    provider = ap.create_ai_provider(
        "auto",
        "sk-ant-test", "claude-x",
        extra_key="sk-openai-test",
        gemini_key="sk-gemini-test-key",
    )
    assert isinstance(provider, ap.GeminiProvider)


def test_classify_gemini_rate_limit():
    import core.ai_provider as ap
    class Fake:
        status_code = 429
        def __str__(self):
            return "429 Too Many Requests"
    err = ap.GeminiProvider._classify(Fake())
    assert err.kind == "rate_limit"
    assert isinstance(err, ap.RateLimitedError)


def test_classify_gemini_authentication():
    import core.ai_provider as ap
    class Fake:
        status_code = 401
        def __str__(self):
            return "Permission denied"
    err = ap.GeminiProvider._classify(Fake())
    assert err.kind == "authentication"
    assert isinstance(err, ap.AuthenticationError)


def test_gemini_complete_uses_generate_content_config():
    """complete() calls the google-genai models API with a GenerateContentConfig."""
    import core.ai_provider as ap
    from google.genai import types

    class FakeResponse:
        text = "done"

    class FakeModels:
        def generate_content(self, model, contents=None, config=None):
            recorded["model"] = model
            recorded["contents"] = contents
            recorded["config"] = config
            return FakeResponse()

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    recorded = {}
    provider = ap.GeminiProvider("sk-gemini-test-key")
    provider.client = FakeClient()
    out = provider.complete("You are the analyst", "scan this", max_tokens=2048)
    assert out == "done"
    assert recorded["model"] == "gemini-3.5-flash-lite"
    assert recorded["contents"] == "scan this"
    assert isinstance(recorded["config"], types.GenerateContentConfig)
    assert recorded["config"].system_instruction == "You are the analyst"
    assert recorded["config"].max_output_tokens == 2048
    assert recorded["config"].automatic_function_calling.disable is True
    assert recorded["config"].http_options.retry_options.attempts == 1


def test_gemini_complete_empty_text_returns_empty_string():
    """A response with no text yields an empty string, not a crash."""
    import core.ai_provider as ap

    class FakeResponse:
        text = ""

    class FakeModels:
        def generate_content(self, model, contents=None, config=None):
            return FakeResponse()

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    provider = ap.GeminiProvider("sk-gemini-test-key")
    provider.client = FakeClient()
    assert provider.complete("sys", "msg") == ""


# ---------------------------------------------------------------------------
# Rate-limit retry / backoff
# ---------------------------------------------------------------------------

def test_retry_with_backoff_retries_on_rate_limit(monkeypatch):
    """A 429 rate-limit error is retried and eventually succeeds."""
    import core.ai_provider as ap
    calls = {"n": 0}

    def classify(e):
        return ap.RateLimitedError() if isinstance(e, RuntimeError) else e

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 rate limit")
        return "ok"

    sleeps = []
    monkeypatch.setattr(ap.time, "sleep", lambda s: sleeps.append(s))
    result = ap._retry_with_backoff(fn, classify, max_attempts=3,
                                    initial_delay=0.0, backoff=2.0)
    assert result == "ok"
    assert calls["n"] == 3
    assert sleeps == [0.0, 0.0]


def test_retry_with_backoff_raises_after_exhaustion():
    """Persistent rate-limit raises RateLimitedError after max attempts."""
    import core.ai_provider as ap

    def classify(e):
        return ap.RateLimitedError()

    def fn():
        raise RuntimeError("429 rate limit")

    import pytest
    with pytest.raises(ap.RateLimitedError):
        ap._retry_with_backoff(fn, classify, max_attempts=2,
                               initial_delay=0.0, backoff=2.0)


def test_retry_with_backoff_passthrough_other_errors(monkeypatch):
    """Non-rate-limit errors are classified and raised without retry."""
    import core.ai_provider as ap

    def classify(e):
        return ap.AuthenticationError("bad key")

    def fn():
        raise RuntimeError("unauthorized")

    monkeypatch.setattr(ap.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("no sleep")))
    with pytest.raises(ap.AuthenticationError):
        ap._retry_with_backoff(fn, classify, max_attempts=3,
                               initial_delay=0.0, backoff=2.0)


def test_retry_with_backoff_honors_retry_after(monkeypatch):
    """When a 429 carries a Retry-After value, we sleep that amount, not the default."""
    import core.ai_provider as ap
    calls = {"n": 0}

    def classify(e):
        return ap.RateLimitedError(retry_after=5.0)

    def fn():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("429 rate limit")
        return "ok"

    sleeps = []
    monkeypatch.setattr(ap.time, "sleep", lambda s: sleeps.append(s))
    result = ap._retry_with_backoff(fn, classify, max_attempts=2,
                                    initial_delay=1.0, backoff=2.0)
    assert result == "ok"
    assert sleeps == [5.0]


def test_retry_after_seconds_parses_numeric_header():
    """Numeric Retry-After headers on an error are read and capped."""
    import core.ai_provider as ap

    class FakeResp:
        headers = {"retry-after": "7"}

    class Fake:
        response = FakeResp()
        status_code = 429

    assert ap._retry_after_seconds(Fake()) == 7.0


def test_retry_after_seconds_absent_returns_none():
    """No Retry-After header -> None (so default backoff is used)."""
    import core.ai_provider as ap

    class FakeResp:
        headers = {}

    class Fake:
        response = FakeResp()

    assert ap._retry_after_seconds(Fake()) is None


def test_classify_gemini_rate_limit_carries_retry_after():
    """429 classification attaches the parsed Retry-After to the error."""
    import core.ai_provider as ap

    class FakeResp:
        headers = {"retry-after": "12"}

    class Fake:
        status_code = 429
        response = FakeResp()
        def __str__(self):
            return "429 Too Many Requests"

    err = ap.GeminiProvider._classify(Fake())
    assert isinstance(err, ap.RateLimitedError)
    assert err.retry_after == 12.0


# ---------------------------------------------------------------------------
# Timeout classification
# ---------------------------------------------------------------------------

def test_classify_gemini_timeout_error():
    """A built-in TimeoutError must classify as 'timeout', not a generic error."""
    import core.ai_provider as ap

    class FakeTimeout:
        __name__ = "TimeoutException"

    err = ap.GeminiProvider._classify(TimeoutError("The read operation timed out"))
    assert err.kind == "timeout"
    assert "timed out" in err.message.lower()
    assert isinstance(err, ap.ProviderError)


def test_classify_gemini_sdk_timeout_style():
    """httpx/httpcore-style timeout exceptions (named TimeoutException) classify as timeout."""
    import core.ai_provider as ap

    class FakeTimeoutObj:
        def __str__(self):
            return "timed out"

    err = ap.GeminiProvider._classify(FakeTimeoutObj())
    assert err.kind == "timeout"


def test_classify_gemini_deadline_message():
    """Messages mentioning 'deadline' classify as timeout."""
    import core.ai_provider as ap

    class Fake:
        code = 504
        def __str__(self):
            return "Deadline exceeded before response could be completed"

    err = ap.GeminiProvider._classify(Fake())
    assert err.kind == "timeout"


def test_classify_provider_error_timeout():
    """classify_provider_error also maps timeout-wrapped messages."""
    from core.ai_provider import classify_provider_error
    import core.ai_provider as ap
    err = ap.GeminiProvider._classify(TimeoutError("socket timeout"))
    msg, kind = classify_provider_error(err)
    assert kind == "timeout"
    assert "timed out" in msg.lower()


# ---------------------------------------------------------------------------
# Batched multi-file analysis
# ---------------------------------------------------------------------------

def test_analyze_many_attributes_files_and_dedupes():
    """analyze_many batches files into one request and tags issues by file."""
    from core.ai_provider import AIProvider

    class P(AIProvider):
        provider_name = "gemini"
        def __init__(self):
            self.calls = 0
        def _normalize_model(self):
            return "gemini-3.5-flash-lite"
        def complete(self, system, user_message, max_tokens=4000):
            self.calls += 1
            return ('{"issues": ['
                    '{"file": "a.py", "title": "X", "line": 1},'
                    '{"file": "b.py", "title": "Y"},'
                    '{"file": "missing.py", "title": "Z"}], '
                    '"overall_quality": "GOOD"}')

    provider = P()
    files = [{"path": "a.py", "content": "a"}, {"path": "b.py", "content": "b"}]
    result = provider.analyze_many(files)
    assert provider.calls == 1  # exactly one batched request
    assert result["issues"][0]["file"] == "a.py"
    assert result["issues"][1]["file"] == "b.py"
    # Unknown file falls back to the last provided file.
    assert result["issues"][2]["file"] == "b.py"


# ---------------------------------------------------------------------------
# Large-repository batching (analyze_many_batched)
# ---------------------------------------------------------------------------

def _records(paths_with_len):
    """Build file records; path -> {'path', 'content': 'x'*len}."""
    return [{"path": p, "content": "x" * n} for p, n in paths_with_len.items()]


def test_split_file_batches_respects_max_files():
    from core.ai_provider import split_file_batches

    files = _records({f"f{i}.py": 100 for i in range(10)})
    batches = split_file_batches(files, max_files_per_batch=4, max_chars_per_batch=10 ** 9)
    sizes = [len(b) for b in batches]
    assert sizes == [4, 4, 2]


def test_split_file_batches_respects_char_budget():
    from core.ai_provider import split_file_batches

    # 3 files of 800 chars each with a 1600-char budget: pairs split at 2 files.
    files = _records({"a.py": 800, "b.py": 800, "c.py": 800})
    batches = split_file_batches(files, max_files_per_batch=100,
                                 max_chars_per_batch=1600)
    assert [len(b) for b in batches] == [2, 1]


def test_split_file_batches_oversized_file_alone():
    from core.ai_provider import split_file_batches

    giant = _records({"huge.py": 50000, "a.py": 50, "b.py": 50})
    batches = split_file_batches(giant, max_chars_per_file=4000,
                                 max_chars_per_batch=1600)
    # The huge file exceeds the budget even when capped -> its own batch;
    # the small files still pack together.
    assert [b[0]["path"] for b in batches] == ["huge.py", "a.py"]
    assert [[r["path"] for r in b] for b in batches] == [["huge.py"], ["a.py", "b.py"]]


def test_split_file_batches_no_duplicates():
    from core.ai_provider import split_file_batches

    files = _records({f"f{i}.py": 2000 for i in range(12)})
    batches = split_file_batches(files, max_files_per_batch=3,
                                 max_chars_per_batch=5000)
    seen = [r["path"] for b in batches for r in b]
    assert sorted(seen) == sorted(files[i]["path"] for i in range(12))
    assert len(seen) == len(set(seen))


class BatchRecorder(AIProvider):
    """AIProvider stub that records every request's file list.

    Responses are consumed in order; once exhausted the LAST response is
    repeated so a failing batch keeps failing across split-retries.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []  # list of file-path lists, one per complete() call

    def _normalize_model(self):
        return "gemini-3.5-flash-lite"

    def complete(self, system, user_message, max_tokens=4000):
        import re
        paths = re.findall(r"### FILE:\s*([^\n]+)", user_message)
        self.requests.append(paths)
        idx = min(len(self.requests) - 1, len(self.responses) - 1)
        response = self.responses[idx]
        if isinstance(response, Exception):
            raise response
        return response


def _ai_json_for(*paths):
    issues = ",".join(
        '{"file": "%s", "title": "bug in %s", "line": 1}' % (p, p)
        for p in paths
    )
    return '{"issues": [%s], "overall_quality": "FAIR"}' % issues


def test_analyze_many_batched_large_repo_splits_requests_and_merges():
    """A large repo is sent as several small bounded requests, never one huge one."""
    from core.ai_provider import AIProvider

    files = _records({f"mod{i}.py": 3000 for i in range(9)})
    provider = BatchRecorder([
        _ai_json_for("mod0.py", "mod1.py", "mod2.py"),
        _ai_json_for("mod3.py", "mod4.py", "mod5.py"),
        _ai_json_for("mod6.py", "mod7.py", "mod8.py"),
    ])
    result = provider.analyze_many_batched(files, max_files_per_batch=3,
                                           max_chars_per_batch=10 ** 9)

    assert len(provider.requests) == 3          # three bounded requests
    assert max(len(r) for r in provider.requests) <= 3  # never oversized
    # No duplicate request: every file sent exactly once across all requests.
    sent = [p for req in provider.requests for p in req]
    assert len(sent) == len(set(sent)) == 9
    assert result["batches_total"] == 3
    assert result["batches_succeeded"] == 3
    assert result["partial"] is False
    # Issues from every successful batch are merged.
    assert {i["file"] for i in result["issues"]} == {f"mod{i}.py" for i in range(9)}
    assert result["overall_quality"] == "FAIR"


def test_analyze_many_batched_continues_on_batch_failure():
    """A failing middle batch must not abort the remaining batches."""
    from core.ai_provider import AIProvider

    files = _records({f"mod{i}.py": 1000 for i in range(5)})
    provider = BatchRecorder([
        _ai_json_for("mod0.py", "mod1.py"),
        ProviderError("analysis exploded", "provider"),
        _ai_json_for("mod4.py"),
    ])
    result = provider.analyze_many_batched(files, max_files_per_batch=2,
                                           max_chars_per_batch=10 ** 9)

    assert result["batches_total"] == 3
    assert result["batches_succeeded"] == 2
    assert result["partial"] is True
    assert len(result["batch_errors"]) == 1
    assert result["batch_errors"][0]["files"] == ["mod2.py", "mod3.py"]
    # Only the successful batches contributed issues — nothing fabricated.
    assert {i["file"] for i in result["issues"]} == {"mod0.py", "mod1.py", "mod4.py"}


def test_analyze_many_batched_timeout_splits_and_keeps_other_batches(monkeypatch):
    """A timed-out batch is split & retried; other batches are unaffected."""
    from core.ai_provider import AIProvider
    from config import Config
    monkeypatch.setattr(Config, "AI_BATCH_SPLIT_DEPTH", 2)

    files = _records({f"mod{i}.py": 1000 for i in range(6)})
    # Requests: [0,1] ok | [2,3] timeout -> split -> [2] timeout, [3] timeout | [4,5] ok
    provider = BatchRecorder([
        _ai_json_for("mod0.py", "mod1.py"),
        TimeoutError("socket timeout after 180s"),
        TimeoutError("socket timeout after 180s"),
        TimeoutError("socket timeout after 180s"),
        _ai_json_for("mod4.py", "mod5.py"),
    ])
    result = provider.analyze_many_batched(files, max_files_per_batch=2,
                                           max_chars_per_batch=10 ** 9)

    assert result["partial"] is True
    assert result["batches_total"] == 3
    assert result["batches_succeeded"] == 2
    # The timed-out batch was split into single-file leaves, both timing out.
    assert len(result["batch_errors"]) == 2
    for err in result["batch_errors"]:
        assert err["kind"] == "timeout"
        assert err["retried"] is True
        assert err["splits"] == 1
        assert len(err["files"]) == 1
    # Successful batches still contributed issues — nothing fabricated.
    assert {i["file"] for i in result["issues"]} == {"mod0.py", "mod1.py", "mod4.py", "mod5.py"}


def test_analyze_many_batched_split_recovers_when_children_succeed(monkeypatch):
    """A timed-out batch splits; both smaller halves analyze successfully."""
    from core.ai_provider import AIProvider
    from config import Config
    monkeypatch.setattr(Config, "AI_BATCH_SPLIT_DEPTH", 2)

    files = _records({f"mod{i}.py": 1000 for i in range(4)})
    provider = BatchRecorder([
        TimeoutError("socket timeout"),            # full batch [mod0..mod3] times out
        _ai_json_for("mod0.py", "mod1.py"),        # left half succeeds
        _ai_json_for("mod2.py", "mod3.py"),        # right half succeeds
    ])
    result = provider.analyze_many_batched(files, max_files_per_batch=4,
                                           max_chars_per_batch=10 ** 9)

    assert result["partial"] is False
    assert result["batches_total"] == 1
    assert result["batches_succeeded"] == 1
    assert result["batch_errors"] == []
    assert {i["file"] for i in result["issues"]} == {f"mod{i}.py" for i in range(4)}
    # 1 original request + 2 split retries; the retries partition the files
    # into disjoint halves (a retry re-sends the timed-out batch, which is the
    # intended smaller-payload retry, but never overlaps with other batches).
    assert len(provider.requests) == 3
    assert provider.requests[0] == [f"mod{i}.py" for i in range(4)]
    halves = provider.requests[1:]
    assert set(halves[0]).isdisjoint(set(halves[1]))
    assert set(halves[0]) | set(halves[1]) == {f"mod{i}.py" for i in range(4)}


def test_analyze_many_batched_split_partial_recovery(monkeypatch):
    """One half recovers after a split; the other still fails -> partial + retried info."""
    from core.ai_provider import AIProvider
    from config import Config
    monkeypatch.setattr(Config, "AI_BATCH_SPLIT_DEPTH", 2)

    files = _records({f"mod{i}.py": 1000 for i in range(4)})
    provider = BatchRecorder([
        TimeoutError("socket timeout"),            # full batch times out
        _ai_json_for("mod0.py", "mod1.py"),        # left half succeeds
        TimeoutError("still timing out"),          # right half times out
    ])
    result = provider.analyze_many_batched(files, max_files_per_batch=4,
                                           max_chars_per_batch=10 ** 9)

    assert result["partial"] is True
    assert len(result["batch_errors"]) == 2        # mod2, mod3 fail as single files
    assert all(e["retried"] is True and e["splits"] == 2 for e in result["batch_errors"])
    assert {i["file"] for i in result["issues"]} == {"mod0.py", "mod1.py"}


def test_analyze_many_batched_single_file_timeout_not_split():
    """A single-file batch that times out cannot be split; recorded as-is."""
    from core.ai_provider import AIProvider

    files = _records({"solo.py": 1000})
    provider = BatchRecorder([TimeoutError("socket timeout")])
    result = provider.analyze_many_batched(files, max_files_per_batch=4,
                                           max_chars_per_batch=10 ** 9)

    assert result["partial"] is True
    assert len(result["batch_errors"]) == 1
    err = result["batch_errors"][0]
    assert err["kind"] == "timeout"
    assert err["retried"] is False
    assert err["files"] == ["solo.py"]


def test_analyze_many_batched_all_batches_fail_reports_errors_no_fabrication():
    """When every batch times out, no issues are fabricated and each failed leaf is reported."""
    from core.ai_provider import AIProvider

    files = _records({f"mod{i}.py": 1000 for i in range(6)})
    # Responses: [mod0,1] timeout | [mod2,3] timeout | [mod4,5] timeout. The
    # recorder repeats the last response, so every split leaf keeps timing out.
    provider = BatchRecorder([
        TimeoutError("socket timeout"),
        TimeoutError("socket timeout"),
        TimeoutError("socket timeout"),
    ])
    result = provider.analyze_many_batched(files, max_files_per_batch=2,
                                           max_chars_per_batch=10 ** 9,
                                           max_split_depth=2)

    assert result["partial"] is True
    assert result["batches_total"] == 3
    assert result["batches_succeeded"] == 0
    assert result["issues"] == []          # nothing fabricated
    # 3 initial batches split into 6 single-file leaves, all failing.
    assert len(result["batch_errors"]) == 6
    assert all(e["kind"] == "timeout" for e in result["batch_errors"])
    assert all(e["retried"] is True and e["splits"] == 1 for e in result["batch_errors"])
    covered = [f for e in result["batch_errors"] for f in e["files"]]
    assert sorted(covered) == [f"mod{i}.py" for i in range(6)]


def test_analyze_many_batched_non_timeout_errors_not_split_retried():
    """Non-timeout provider errors are NOT split-and-retried; reported once per batch."""
    from core.ai_provider import AIProvider

    files = _records({f"mod{i}.py": 1000 for i in range(4)})
    provider = BatchRecorder([
        ProviderError("analysis exploded", "provider"),
        TypeError("unknown failure"),
    ])
    result = provider.analyze_many_batched(files, max_files_per_batch=2,
                                           max_chars_per_batch=10 ** 9,
                                           max_split_depth=2)

    assert result["partial"] is True
    assert result["batches_succeeded"] == 0
    assert result["issues"] == []
    assert len(result["batch_errors"]) == 2
    assert all(e["retried"] is False and e["splits"] == 0 for e in result["batch_errors"])
    # Each error names exactly the files of its own batch (no cross-batch overlap).
    err_files = [e["files"] for e in result["batch_errors"]]
    assert sorted(f for files in err_files for f in files) == [f"mod{i}.py" for i in range(4)]


def test_split_batch_in_half_preserves_order_and_parts():
    from core.ai_provider import split_batch_in_half

    batch = _records({"a.py": 10, "b.py": 10, "c.py": 10})
    left, right = split_batch_in_half(batch)
    assert [r["path"] for r in left] == ["a.py", "b.py"]
    assert [r["path"] for r in right] == ["c.py"]
    assert left + right == batch


def test_analyze_many_batched_split_depth_is_bounded():
    """Splitting does not retry forever: a split-depth cap stops recursion."""
    from core.ai_provider import AIProvider

    files = _records({f"mod{i}.py": 1000 for i in range(4)})
    provider = BatchRecorder([TimeoutError("socket timeout")])  # always times out
    result = provider.analyze_many_batched(files, max_files_per_batch=4,
                                           max_chars_per_batch=10 ** 9,
                                           max_split_depth=1)
    # depth 1: split 4->2+2, both 2-file leaves cannot split again -> 2 errors.
    assert len(result["batch_errors"]) == 2
    assert all(e["splits"] == 1 for e in result["batch_errors"])
    assert {p for e in result["batch_errors"] for p in e["files"]} == {f"mod{i}.py" for i in range(4)}
    assert len(provider.requests) == 3  # 1 original + 2 halves, no unbounded retrying


def test_analyze_many_batched_empty_input():
    """No files -> empty result and zero requests."""
    provider = BatchRecorder([])
    result = provider.analyze_many_batched([])
    assert result["issues"] == []
    assert result["batches_total"] == 0
    assert result["partial"] is False
    assert provider.requests == []

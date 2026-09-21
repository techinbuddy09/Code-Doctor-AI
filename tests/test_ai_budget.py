from unittest.mock import Mock
import pytest
from core.ai_provider import AIProvider, GeminiProvider, ProviderError, RateLimitedError, _retry_with_backoff
from config import Config


class SlowProvider(AIProvider):
    def __init__(self, clock):
        self.clock = clock
        self.calls = 0

    def _normalize_model(self):
        return "test"

    def complete(self, *args, **kwargs):
        self.calls += 1
        self.clock[0] += 10
        return '{"issues": []}'


def test_budget_skips_later_batches_and_restores_deadline(monkeypatch):
    clock = [0]
    monkeypatch.setattr("core.ai_provider.time.monotonic", lambda: clock[0])
    monkeypatch.setattr(Config, "AI_ANALYSIS_TIMEOUT", 5)
    provider = SlowProvider(clock)
    progress = []
    result = provider.analyze_many_batched(
        [{"path": "a.py", "content": "x=1"}, {"path": "b.py", "content": "x=2"}],
        max_files_per_batch=1, progress=progress.append)
    assert provider.calls == 1
    assert result["partial"] and result["batches_succeeded"] == 1
    assert "budget" in result["batch_errors"][0]["message"]
    assert len(progress) == 2
    assert provider._analysis_deadline is None


def test_retry_does_not_sleep_past_deadline(monkeypatch):
    monkeypatch.setattr("core.ai_provider.time.monotonic", lambda: 0)
    sleep = Mock()
    monkeypatch.setattr("core.ai_provider.time.sleep", sleep)
    call = Mock(side_effect=RateLimitedError(retry_after=60))
    with pytest.raises(ProviderError, match="budget"):
        _retry_with_backoff(call, lambda error: error, max_attempts=2, deadline=5)
    assert call.call_count == 1
    sleep.assert_not_called()


def test_gemini_request_timeout_uses_remaining_budget(monkeypatch):
    provider = GeminiProvider("test-key", timeout=45)
    monkeypatch.setattr("core.ai_provider.time.monotonic", lambda: 100)
    provider._analysis_deadline = 103
    provider.client = Mock()
    provider.client.models.generate_content.return_value.text = "ok"
    assert provider.complete("system", "message") == "ok"
    config = provider.client.models.generate_content.call_args.kwargs["config"]
    assert config.http_options.timeout == 3000

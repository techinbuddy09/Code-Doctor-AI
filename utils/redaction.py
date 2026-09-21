"""Best-effort masking for recognized credential formats at output boundaries."""
import re


def redact_text(text):
    from core.security_scanner import SECRET_PATTERNS, ASSIGNMENT_PATTERNS
    text = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                  "[REDACTED PRIVATE KEY]", text, flags=re.DOTALL)
    for pattern in ASSIGNMENT_PATTERNS:
        def replace(match):
            start, end = match.span(2)
            return match.group(0)[:start - match.start()] + "[REDACTED]" + match.group(0)[end - match.start():]
        text = pattern.sub(replace, text)
    for pattern, _ in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def redact_data(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_data(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_data(item) for key, item in value.items()}
    return value

# Code Doctor AI — Code Intelligence Lab

Trace the cause. Review the fix.

A local Streamlit application for analyzing public GitHub repositories, inspecting findings, applying suggested fixes, and exporting reports. Based on [Code Doctor AI](https://github.com/ashwinsk9841-bot/code-doctor-ai), under the original MIT license in LICENSE.

## Run on this computer

The complete project and its installed virtual environment are in:

`C:\Users\Dell\Documents\ChatGPT\code_doctor_ai`

From PowerShell in that folder:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Open http://localhost:8501. Alternatively run `./run.ps1` if local script execution is enabled. The original `E:\coddy\app.py` was left untouched; it matched upstream exactly and was used as the starting entry point here.

No API key is needed for local static, security, and dependency scans. For AI features, create `.env` from `.env.example` and enter a real provider key. Do not commit `.env`. Model availability and live AI responses have not been validated with a real account.

## Install on another computer

Use Python 3.10 or newer (this workspace was tested with Python 3.12):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements-lock.txt` records the exact dependency versions installed in this Windows environment; use it instead of requirements.txt to reproduce this environment where compatible.

## Features

- Public GitHub repository downloads with archive path and size checks.
- Static parsing, pattern-based security checks, and dependency declaration checks.
- Optional bounded AI analysis with Gemini, Anthropic, or OpenAI.
- Issue filters, source inspection, Python credential fixes, and AI rewrites.
- Immutable per-fix backups with latest-change checks before reverting.
- Verification that rechecks supported findings; passing tests alone does not prove an arbitrary AI finding resolved.
- Optional local test execution, test draft generation/download, and Markdown/JSON reports.
- Code Doctor AI branding and dark cyan/violet accents.

## Execution and privacy behavior

Downloaded repository tests are disabled by default. Enable local execution only for code you trust: these tests run on this computer, without container isolation. Dependency installation for scanned repositories is not automated. Missing tools/dependencies can block their test runs. A restricted container runner remains future work for hosted or untrusted use.

Recognized credential formats are masked before AI analysis, in source previews, and in reports. This is pattern-based masking, not a guarantee that every possible secret is detected. AI full-file rewrites are blocked while recognized credentials remain in the file. Backups necessarily retain the original local source until workspace cleanup.

AI fixes can still alter behavior and require review. Deterministic verification covers recognized security findings and Python/JSON syntax; other fixes stay NOT_VERIFIED unless a supported check establishes resolution. Non-Python syntax validation is limited. Dashboard issue totals track the original findings and their verification states; start a new scan for a complete fresh analysis.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover scanners, providers using mocks, fix execution, immutable backups, verification, report redaction, archive checks, workspace isolation, and Streamlit scan/fix/report/revert/reset behavior. UI integration tests use a local fixture and do not call GitHub or an AI service.

## Next UI phase

The repository map, side-by-side patch review, scan comparisons, and a full interactive workspace redesign described in PROJECT_REVIEW.md remain future work. This pass focuses on correctness and a runnable local foundation.

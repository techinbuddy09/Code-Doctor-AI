# NeuroTrace — Code Intelligence Lab

Initial project review, 20 September 2026.

Source: https://github.com/ashwinsk9841-bot/code-doctor-ai (main).
Proposed product name: NeuroTrace. Source branding has not been changed: the local workspace contains no application source yet, and the user intends to provide it. The GitHub copy was downloaded into a temporary review directory.

## Architecture and implemented features

The app is Python/Streamlit. `app.py` coordinates session state and landing, scanning, dashboard, issues, tests, and report views. `core/` contains repository ingestion, parsing, analysis, AI adapters, fixing, test generation/execution, verification, and reporting. `ui/` contains CSS, HTML components, and animation JavaScript. `utils/` contains file and language helpers. There are 13 test modules.

- Public GitHub repository ingestion using a ZIP archive and default-branch discovery.
- File discovery, language classification, Python AST parsing, lighter parsing for other languages, and code metrics.
- Pattern-based security checks and dependency declaration checks. Dependency checks are not a live vulnerability-advisory service.
- Optional Gemini, Anthropic, and OpenAI adapters, bounded AI batches, retries, and provider error classification. AI reviews a bounded sample, not necessarily the whole repository.
- Issue filters, severity/confidence/evidence displays, deterministic credential replacement, AI rewriting, backups, and revert controls.
- Test framework detection and subprocess execution; a test-generation module exists but is only imported, never invoked by the current UI.
- Health scoring and Markdown/JSON downloads.
- Dark/gold styling with rain and assistant interaction code; browser behavior has not been verified.

## Verification performed

All 35 Python files parse successfully with Python AST parsing. This establishes syntax validity only.

Attempted `python -m pytest -q` with the bundled Python runtime: blocked because pytest is not installed. Streamlit and python-dotenv are also absent. No dependencies were installed. No live UI, full test suite, or AI-provider calls were validated. Implemented features above must not be described as proven end-to-end working.

## Priority fixes supported by source inspection

1. **False verification success:** `core/verifier.py::verify_fix` sets `verified=True` based on words such as secret/credential/env in issue metadata. It does not inspect the changed file or use `applied_changes`; unchanged code can receive PASS when tests are disabled. Rescan the exact finding and distinguish resolution from test success.
2. **Credential fix runtime failure:** `core/fixer.py::_fix_security` emits `os.environ.get(...)` without ensuring `import os` exists. Compilation accepts this, but execution can raise NameError. The replacement helper also mishandles indentation and is not language-aware. Restrict and structurally validate fixes.
3. **Unsandboxed test execution:** `core/test_runner.py` launches repository tests in a subprocess with the app's inherited environment. An executable allowlist and timeout do not isolate arbitrary test code. Run third-party tests in a restricted disposable environment before treating this as safe for hosted use.
4. **Stale reports and scores:** `app.py` caches report exports before the initial test run and does not regenerate them after fixes/reverts/reruns. Fix metadata is stored separately from issue report fields, and the issue summary is not rescanned. Derive displays and exports from updated results.
5. **Workspace collisions and cleanup:** `_persist_repo` uses a shared path based solely on owner/repository and removes an existing copy. Sessions scanning the same repository can overwrite each other. `repo_temp_dir` is never set, so `_cleanup_repo` does not clean the stable workspace. Use per-session workspaces with explicit ownership.
6. **Overwritten backups:** `_backup` uses one backup per file, overwriting it on subsequent fixes. Reverting one issue can undo unrelated changes and leave other issue statuses inconsistent. Track patch-level history or immutable snapshots.
7. **Incomplete secret masking:** static security evidence masking does not establish end-to-end redaction. AI requests include source text, fixer changes retain original secret lines, and report rendering trusts issue fields. Define and test redaction boundaries using synthetic secrets.
8. **Test support gaps:** UI test generation is unwired; Gradle detection selects Maven; JavaScript summary parsing can access a nonexistent regex capture group. Add realistic framework fixtures and correct detection/parsing.
9. **Repository resource limits:** the fetch path downloads and extracts the archive without enforcing the advertised repository size budget. Enforce transfer and extracted-size limits.

## Product and UI direction

NeuroTrace — Code Intelligence Lab. Tagline: Trace the cause. Review the fix.

Use graphite surfaces, restrained cyan/violet accents, readable typography, and motion that communicates actual scan progress. Primary workspace: repository tree, source/diff editor, and finding explanation panel. Show analysis coverage, AI availability, and verification states accurately.

Potential differentiators:

- Interactive file/dependency map linking findings to affected code.
- Root-cause explanations with evidence and confidence.
- Before/after patch review with individual acceptance and reliable undo.
- Regression tests connected to each fix and visible verification evidence.
- Scan comparison showing newly introduced, unresolved, and resolved findings.
- Downloadable patches or corrected source archives; current UI only exports reports.

## Next phase

After the user supplies the intended source version: compare it with this reviewed version, establish an isolated development environment, run the existing tests and UI smoke checks, fix verification/fixer/report correctness first, then implement NeuroTrace branding and the interactive UI. No remote repository or application source was modified during this review.

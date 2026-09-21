# 🩺 Code Doctor AI

**AI-powered code analysis, debugging, security scanning, and automated fixing.**

Code Doctor AI is a developer-focused tool that analyzes source code, identifies potential issues, explains what went wrong, suggests or applies fixes, and verifies supported fixes.

It combines **static analysis, security checks, dependency scanning, AI-assisted code review, automated fixes, test generation, and reporting** into a single Streamlit application.

---

## ✨ Features

### 🔍 Code Analysis

* Parse and analyze source code
* Detect common code quality and structural issues
* Inspect source files and findings
* Generate structured analysis reports

### 🔐 Security Scanning

* Pattern-based security checks
* Credential and secret detection
* Sensitive information redaction
* Security-focused findings and remediation suggestions

### 📦 Dependency Analysis

* Inspect dependency declarations
* Identify dependency-related issues
* Analyze supported project configuration files

### 🤖 AI-Powered Analysis

Supports AI-assisted analysis through multiple providers:

* OpenAI
* Anthropic
* Google Gemini

AI capabilities can be used for:

* Code explanations
* Issue analysis
* Suggested fixes
* Code rewrites
* Test generation

### 🛠️ Automated Fixes

* Apply supported fixes directly to source files
* Review generated changes
* Create backups before modifications
* Revert changes when required

### ✅ Verification

* Re-check supported findings after fixes
* Validate Python and JSON syntax
* Track whether a finding has been verified
* Keep unsupported or uncertain fixes marked as unverified rather than assuming success

### 🧪 Testing

* Automated test suite using Pytest
* Test generation support
* Optional local execution of repository tests
* Mock-based testing for AI providers

### 📊 Reports

Generate structured reports containing:

* Findings
* Severity/details
* Fix information
* Verification status
* Redacted source information

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │   Streamlit UI      │
                    │      app.py         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Analysis Engine   │
                    │       core/         │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Code Analysis     Security Scan    Dependency Scan
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   AI Providers      │
                    │ OpenAI / Gemini /    │
                    │      Anthropic      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Fix + Verify + Test │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Reports / Results   │
                    └─────────────────────┘
```

---

## 🧰 Tech Stack

| Category        | Technologies                              |
| --------------- | ----------------------------------------- |
| Language        | Python                                    |
| UI              | Streamlit                                 |
| AI              | OpenAI, Anthropic, Google Gemini          |
| Static Analysis | Pygments, Pylint, Flake8, Pyflakes, Radon |
| Security        | Bandit + custom security checks           |
| Testing         | Pytest                                    |
| Environment     | python-dotenv                             |
| Code Processing | AST/parsing and diff utilities            |
| Reporting       | Markdown / JSON                           |

---

## 📁 Project Structure

```text
Code-Doctor-AI/
│
├── core/
│   ├── ai_provider.py
│   ├── analyzer.py
│   ├── code_parser.py
│   ├── dependency_scanner.py
│   ├── fixer.py
│   ├── python_validation.py
│   ├── reporter.py
│   ├── repository.py
│   ├── security_scanner.py
│   ├── test_generator.py
│   ├── test_runner.py
│   ├── verifier.py
│   └── workspace.py
│
├── ui/
│   └── ...
│
├── utils/
│   ├── file_handler.py
│   ├── language_detector.py
│   ├── redaction.py
│   └── validators.py
│
├── tests/
│   └── ...
│
├── app.py
├── config.py
├── conftest.py
├── requirements.txt
├── requirements-lock.txt
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/techinbuddy09/Code-Doctor-AI.git
cd Code-Doctor-AI
```

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

For a reproducible environment, `requirements-lock.txt` is also provided.

### 4. Configure environment variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Add the required AI provider credentials to `.env` if you want to use AI-powered features.

> **Never commit `.env` or API keys to GitHub.**

### 5. Run the application

```bash
streamlit run app.py
```

The application will be available at:

```text
http://localhost:8501
```

---

## 🧪 Running Tests

Run the complete test suite with:

```bash
pytest -q
```

The test suite covers core analysis functionality, scanners, providers, fixing workflows, verification, reporting, workspace behavior, and UI-related flows.

---

## 🔒 Security & Privacy

Code Doctor AI includes safeguards for working with source code:

* Recognized credentials are redacted before AI analysis.
* `.env` files are excluded from version control.
* Local backups are maintained for supported fixes.
* AI-generated changes are not automatically treated as verified.
* Repository tests are not executed automatically unless explicitly enabled.

### ⚠️ Running Repository Tests

Downloaded repository tests can execute code on the local machine.

Only enable local test execution for repositories you trust.

A sandboxed/containerized execution environment is a planned future improvement.

---

## 🛣️ Roadmap

* [ ] Expanded multi-language analysis
* [ ] More security vulnerability patterns
* [ ] Improved dependency vulnerability detection
* [ ] Better AI fix verification
* [ ] Interactive side-by-side patch review
* [ ] Scan comparison across runs
* [ ] Sandboxed test execution
* [ ] Richer project/workspace visualization
* [ ] CI/CD integration

---

## 📄 License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) for details.

---

## 👨‍💻 Project

**Code Doctor AI** is designed as an AI-assisted developer tool for understanding, analyzing, fixing, and verifying code — bringing several stages of the debugging workflow into one application.

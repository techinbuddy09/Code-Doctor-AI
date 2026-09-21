# Local setup

See README.md for the current NeuroTrace setup and execution instructions.

The configured development environment is `.venv` in this project directory.
Run `.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1` from PowerShell.

Static analysis works without an API key. Add your own provider credentials to `.env` only when you want to enable AI features. The original MIT license is retained in LICENSE.

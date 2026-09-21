# NeuroTrace API setup

You only need one provider key. Gemini is the default; OpenAI and Anthropic are optional alternatives, not additional requirements.

1. Open https://aistudio.google.com/apikey and create a Gemini API key.
2. Open `.env` in this project folder with your editor.
3. Fill in the key locally:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

4. Save the file and restart Streamlit. Enable AI analysis in the sidebar.

The key enables AI analysis, AI fixes, and test draft generation. Static parsing, security/dependency checks, deterministic Python credential fixes, and reports work without a key. The current application supports public GitHub repositories without a GitHub token. No database, separate backend service, or all-three-provider setup is required.

Your provider account needs available quota (and billing if required by your selected model/tier). A key does not guarantee unlimited or free usage. See your AI Studio usage/billing page. Live API calls have not yet been tested with your account.

Keep the key in `.env`, not in `app.py` or chat. `.env` is excluded by `.gitignore`.

Optional alternatives supported by this code:

| Provider | Select with | Credential variable | Model variable |
| --- | --- | --- | --- |
| Gemini | `AI_PROVIDER=gemini` | `GEMINI_API_KEY` | `GEMINI_MODEL` |
| OpenAI | `AI_PROVIDER=openai` | `OPENAI_API_KEY` | `OPENAI_MODEL` |
| Anthropic | `AI_PROVIDER=anthropic` | `AI_API_KEY` | `AI_MODEL` |

Configure the model supported by your chosen account. Set only your chosen provider's key to avoid unintended automatic fallback.

Official Gemini instructions: https://ai.google.dev/gemini-api/docs/api-key
Default model: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite

AI latency defaults: `AI_REQUEST_TIMEOUT=45`, `AI_ANALYSIS_TIMEOUT=90`,
`AI_RETRY_MAX=1`, `AI_BATCH_SPLIT_DEPTH=0`. The analysis budget stops new
batches/retries and caps each Gemini request to the remaining budget; actual
transport cleanup may add overhead. Successful AI batches and local findings
remain available if later AI requests fail. Progress reports the active batch.
Gemini automatic function calling and SDK retries are disabled because this
application uses text responses and manages request timing itself.

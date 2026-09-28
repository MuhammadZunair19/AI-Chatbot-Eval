# AI Chatbot QA Framework — Setup and Run Instructions

This guide explains how to install, configure, and run every part of the project locally.

## 1. Prerequisites

Install the following tools:

- Python 3.11 or newer
- Git
- Ollama, if you want to run the chatbot locally without OpenAI
- Postman, optional for manually running the API collection

Check Python and Git:

```powershell
python --version
git --version
```

If `python` is not recognized on Windows, try:

```powershell
py --version
```

In that case, replace `python` with `py` in the commands below.

## 2. Open the Project Directory

Windows PowerShell:

```powershell
Set-Location D:\CHATAIEVAL
```

Linux or macOS:

```bash
cd /path/to/CHATAIEVAL
```

## 3. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, the terminal prompt should normally include `(.venv)`.

If PowerShell prevents script activation, run this command once in the current terminal and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## 4. Install Python Dependencies

Upgrade pip and install the project requirements:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Confirm that the environment is consistent:

```powershell
python -m pip check
```

## 5. Create the Environment File

Copy the example configuration to `.env`.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```bash
cp .env.example .env
```

The default configuration uses Ollama:

```dotenv
LLM_API_KEY=ollama
LLM_MODEL=llama3.2:3b
LLM_BASE_URL=http://localhost:11434/v1

RAGAS_EVALUATOR_MODEL=mistral
RAGAS_EMBEDDING_MODEL=nomic-embed-text

TOP_K=3
RETRIEVAL_MIN_SCORE=0.10
LATENCY_THRESHOLD_MS=5000
LLM_TIMEOUT_SECONDS=60
```

Do not commit `.env`. It is already excluded by `.gitignore`.

## 6. Install and Configure Ollama

Download Ollama from:

<https://ollama.com/download>

Pull the default chatbot model:

```powershell
ollama pull llama3.2:3b
```

For complete RAGAS evaluation, pull the evaluator and embeddings models:

```powershell
ollama pull mistral
ollama pull nomic-embed-text
```

Start Ollama if it is not already running:

```powershell
ollama serve
```

Keep that terminal open. In a second terminal, reactivate the project virtual environment before running the application.

Check whether Ollama is responding:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

Linux or macOS users can check with:

```bash
curl http://localhost:11434/api/tags
```

## 7. Live RAGAS Evaluation

The API can run without RAGAS, but the evaluation runner needs evaluator models to calculate semantic correctness, relevance, and groundedness.

The example environment enables the metrics with these values:

```dotenv
RAGAS_EVALUATOR_MODEL=mistral
RAGAS_EMBEDDING_MODEL=nomic-embed-text
```

The evaluator uses RAGAS's collections API and calculates:

- `FactualCorrectness` from the generated response and reference answer
- `AnswerRelevancy` from the question and response, using `nomic-embed-text`
- `Faithfulness` from the generated response and retrieved knowledge-base contexts

The collections metrics make asynchronous evaluator and embedding calls, so the project uses an Ollama-backed `AsyncOpenAI` client for both `llm_factory` and the embedding factory.

If either setting is blank or a local model is unavailable, the evaluation runner does not invent semantic scores. Cases requiring unavailable metrics are marked `SKIPPED`.

Local RAGAS evaluation can be slower than ordinary chatbot responses because it makes several additional model calls for each test case.

## 8. Start the FastAPI Application

From the project root, with the virtual environment active and Ollama running:

```powershell
uvicorn app.main:app --reload
```

The application is available at:

- API base URL: <http://localhost:8000>
- Swagger documentation: <http://localhost:8000/docs>
- ReDoc documentation: <http://localhost:8000/redoc>

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

Example chat request in PowerShell:

```powershell
$body = @{ question = "How long is the AcmeCloud free trial?" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/chat `
  -ContentType "application/json" `
  -Body $body
```

Example with curl:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"How long is the AcmeCloud free trial?"}'
```

Stop the API with `Ctrl+C`.

## 9. Run the Automated Tests

The normal offline suite uses mocks and does not require Ollama, an OpenAI key, or paid API calls.

Run every test:

```powershell
pytest -v
```

Run only tests that do not call a live model:

```powershell
pytest -m "not integration" -v
```

Run individual categories:

```powershell
pytest -m normal -v
pytest -m hallucination -v
pytest -m edge -v
pytest -m injection -v
pytest -m safety -v
pytest -m long_context -v
pytest -m performance -v
```

## 10. Run the Live Integration Test

The integration test is opt-in so CI and ordinary local tests never call a live model accidentally.

First ensure Ollama is running and the configured model has been pulled.

Windows PowerShell:

```powershell
$env:RUN_LIVE_LLM_TESTS = "1"
pytest -m integration -v
Remove-Item Env:RUN_LIVE_LLM_TESTS
```

Linux or macOS:

```bash
RUN_LIVE_LLM_TESTS=1 pytest -m integration -v
```

## 11. Run the Complete Evaluation

Ensure that:

1. The virtual environment is active.
2. Ollama is running.
3. `llama3.2:3b` has been pulled.
4. `.env` contains the desired model settings.
5. The evaluator and embedding settings are populated if semantic RAGAS scores are required.

Then run:

```powershell
python scripts/run_evaluation.py
```

The runner processes all 30 test cases and prints:

- overall pass, fail, and skipped totals
- pass rate
- per-category results
- average correctness
- average relevance
- average groundedness
- average chatbot latency

The generated reports are written to:

```text
reports/evaluation_report.csv
reports/evaluation_report.json
```

These files are ignored by Git so local evaluation results are not committed accidentally.

## 12. Run the Postman Collection

1. Start Ollama.
2. Start the FastAPI application with `uvicorn app.main:app --reload`.
3. Open Postman.
4. Import `postman/AI_Chatbot_QA.postman_collection.json`.
5. Import `postman/local.postman_environment.json`.
6. Select the **AI Chatbot QA - Local** environment.
7. Confirm that `base_url` is `http://localhost:8000`.
8. Run the collection.

The collection includes health, normal, pricing, hallucination, prompt-injection, unsafe-request, empty-input, long-context, and performance checks.

## 13. Use Another OpenAI-Compatible Provider

Ollama is the default, but the chatbot client can use another OpenAI-compatible chat-completions endpoint.

Update `.env`:

```dotenv
LLM_API_KEY=your-provider-key
LLM_MODEL=your-provider-model
LLM_BASE_URL=https://your-provider.example/v1
```

Never place a real API key in source code, `.env.example`, tests, reports, screenshots, or Git commits.

If the provider also supports compatible chat and embedding endpoints, configure the RAGAS models as well:

```dotenv
RAGAS_EVALUATOR_MODEL=your-evaluator-model
RAGAS_EMBEDDING_MODEL=your-embedding-model
```

## 14. Common Problems

### `python` is not recognized

Use the Windows Python launcher:

```powershell
py -m venv .venv
py -m pip install -r requirements.txt
py scripts/run_evaluation.py
```

### `uvicorn` or `pytest` is not recognized

Make sure the virtual environment is active. You can also run the modules directly:

```powershell
python -m uvicorn app.main:app --reload
python -m pytest -v
```

### PowerShell will not activate the virtual environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### The API returns HTTP 503

This normally means the configured LLM endpoint is unavailable or timed out. Check that Ollama is running and that the model name in `.env` matches an installed model:

```powershell
ollama list
Invoke-RestMethod http://localhost:11434/api/tags
```

### The evaluation shows many `SKIPPED` cases

Check the `failure_reason` column in the report. Common causes are:

- Ollama is not running.
- The generation model is missing.
- `RAGAS_EVALUATOR_MODEL` is blank.
- `RAGAS_EMBEDDING_MODEL` is blank.
- The configured provider does not support the required embedding endpoint.

Skipped semantic evaluations are intentional when real evaluator output is unavailable; the project never substitutes fake scores.

### Evaluation is slow

RAGAS makes multiple evaluator calls per answer. Runtime depends on model size and hardware. Use a smaller local model for development, or leave RAGAS settings blank when only testing deterministic behavior.

### Port 8000 is already in use

Start the API on another port:

```powershell
uvicorn app.main:app --reload --port 8001
```

Update the Postman `base_url` to `http://localhost:8001` if using the collection.

## 15. Recommended First Run

For a clean first-time setup on Windows PowerShell:

```powershell
Set-Location D:\CHATAIEVAL
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull llama3.2:3b
ollama pull mistral
ollama pull nomic-embed-text
```

Edit `.env` and set:

```dotenv
RAGAS_EVALUATOR_MODEL=mistral
RAGAS_EMBEDDING_MODEL=nomic-embed-text
```

Start Ollama in one terminal:

```powershell
ollama serve
```

In a second activated terminal, run:

```powershell
pytest -m "not integration" -v
uvicorn app.main:app --reload
```

After confirming the API works, stop it with `Ctrl+C` and run the evaluation:

```powershell
python scripts/run_evaluation.py
```

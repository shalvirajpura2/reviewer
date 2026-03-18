# Reviewer

Reviewer is a deterministic pull-request analysis tool for public GitHub repositories. Paste a PR URL and it returns a structured merge-confidence report: verdict, score, top risks, top files to inspect, signal evidence, and next actions.

The product is designed to feel useful to a real reviewer, not like a demo. It fetches live PR data from GitHub, applies explainable scoring rules, and shows where review attention should go first.

## Stack

- Frontend: Vite, React, TypeScript, React Router
- Backend: FastAPI, Pydantic, HTTPX
- Analysis: deterministic heuristics plus patch-structure hints
- Optional signal enhancement: tree-sitter

## Repository layout

```text
backend/
  app/
    core/
    models/
    routes/
    services/
  requirements.txt
frontend/
  public/
  src/
    components/
    lib/
    pages/
    styles/
    types/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
.env.example
.gitattributes
.gitignore
README.md
```

## Environment variables

Shared:
- `GITHUB_TOKEN`

Frontend:
- `VITE_BACKEND_URL`
  - example: `http://localhost:8000`

Backend:
- `GITHUB_API_BASE`
  - optional
  - defaults to `https://api.github.com`
- `BACKEND_PORT`
  - optional
  - defaults to `8000`
- `CACHE_TTL_SECONDS`
  - optional
  - defaults to `300`
- `CORS_ALLOW_ORIGINS`
  - optional
  - defaults to local Vite and localhost origins

`backend/data/` is runtime-generated local state and is ignored by Git.

## Local setup

### 1. Install frontend dependencies

```bash
cd frontend
pnpm install
```

### 2. Configure environment

Copy `.env.example` to `.env` and set at least:

```bash
GITHUB_TOKEN=your_token_here
VITE_BACKEND_URL=http://localhost:8000
```

### 3. Run the backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

### 4. Run the frontend

```bash
cd frontend
pnpm dev
```

Frontend runs on `http://localhost:5173` by default.

## Production checks

Backend compile check:

```bash
python -m compileall backend/app
```

Frontend build check:

```bash
cd frontend
pnpm build
```

## Important product paths

- `frontend/src/pages/result_page.tsx`
- `frontend/src/lib/review_mapper.ts`
- `frontend/src/components/pr_input_bar.tsx`
- `backend/app/routes/analyze.py`
- `backend/app/services/analysis_service.py`
- `backend/app/services/file_classifier.py`
- `backend/app/services/signal_detector.py`
- `backend/app/services/result_builder.py`

## Current direction

Reviewer is being built as a trustworthy engineering tool:
- deterministic scoring over invented AI claims
- exact files to inspect first
- explicit evidence and limitations
- fast time-to-value from a single pasted PR URL

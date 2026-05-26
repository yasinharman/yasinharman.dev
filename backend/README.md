# Portfolio RAG Backend (FastAPI)

RAG service backing the chat on the portfolio site (FastAPI + LangChain, Supabase Postgres). Frontend (`VITE_API_URL`) calls `POST /chat` with `{message, session_id}`.

## Architecture

```
Frontend (Vite/React)  ──POST /chat──▶  FastAPI
                                         ├─ input_guard (LLM)
                                         ├─ memory (postgres: chat_messages)
                                         ├─ AgentExecutor (LangChain)
                                         │    └─ tool: portfolio_kb
                                         │         └─ SupabaseVectorStore + Cohere Rerank
                                         ├─ output_guard (LLM)
                                         └─ chat_logs (postgres)
```

Ingestion: `POST /admin/ingest` (multipart, header `X-API-Key`) or CLI `python -m app.ingest <path>`.

## Local dev

```bash
cd backend
cp .env.example .env       # fill credentials
python -m venv .venv && . .venv/Scripts/activate   # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# apply migrations to your dev postgres
psql "$DATABASE_URL" -f migrations/001_init.sql

uvicorn app.main:app --reload --port 8000
curl -s -X POST localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Yasin hangi projeleri yaptı?","session_id":"local-1"}'
```

## Ingest a document

```bash
python -m app.ingest ./docs/cv.pdf
# or via HTTP
curl -X POST http://localhost:8000/admin/ingest \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@./docs/cv.pdf" \
  -F "source=cv"
```

## Deploy to Coolify

1. Push the `backend/` directory to your repo.
2. Coolify → New Resource → Application → Public Repository (or Git provider). Build pack: Dockerfile, base directory `backend/`.
3. Set env vars from `.env.example` in the Coolify UI. `DATABASE_URL` points to the Supabase **Session pooler** (port 5432).
4. Add a domain (e.g. `api.yasinharman.dev`) — Coolify provisions Traefik + Let's Encrypt automatically.
5. Apply the migration once on Supabase (SQL editor) or via Coolify terminal:
   ```
   psql "$DATABASE_URL" -f migrations/001_init.sql
   ```
6. Smoke test: `curl https://api.yasinharman.dev/healthz`.
7. Update the frontend env in Coolify: `VITE_API_URL=https://api.yasinharman.dev/chat`, rebuild & redeploy.

## TODO before production

- Replace the **placeholder system prompts** in `app/agent.py` (`SYSTEM_PROMPT`) and `app/guards.py` (`INPUT_GUARD_SYSTEM`, `OUTPUT_GUARD_SYSTEM`) with the finalized prompts.
- Verify the embedding dimension of the existing Supabase `documents` table matches `OPENAI_EMBED_MODEL` (default `text-embedding-3-small` → 1536). If the table was built with `text-embedding-3-large` (3072), update the env var.
- Confirm `COHERE_RERANK_MODEL` matches the model used during ingestion.

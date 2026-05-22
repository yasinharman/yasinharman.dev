# Portfolio RAG Backend (FastAPI)

Replaces the n8n RAG workflow that backs the chat on the portfolio site. Frontend (`VITE_N8N_WEBHOOK_URL`) calls `POST /chat` with the same `{message, session_id}` contract.

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

## Deploy to Dokploy

1. Push the `backend/` directory to your repo.
2. Dokploy → New Application → Dockerfile build, root path `backend/`.
3. Set env vars from `.env.example` in the Dokploy UI (point `DATABASE_URL` to your internal postgres hostname).
4. Add it to the same internal network as the postgres service.
5. Configure a Traefik label / domain (e.g. `api.yasinharman.com`) with HTTPS.
6. Run the migration once on the target DB:
   ```
   psql "$DATABASE_URL" -f migrations/001_init.sql
   ```
7. Smoke test: `curl https://api.yasinharman.com/healthz`.
8. Update the frontend `.env.production`: `VITE_N8N_WEBHOOK_URL=https://api.yasinharman.com/chat`, rebuild & redeploy.

## TODO before production

- Replace the **placeholder system prompts** in `app/agent.py` (`SYSTEM_PROMPT`) and `app/guards.py` (`INPUT_GUARD_SYSTEM`, `OUTPUT_GUARD_SYSTEM`) with the exact prompts from the original n8n nodes.
- Verify the embedding dimension of the existing Supabase `documents` table matches `OPENAI_EMBED_MODEL` (default `text-embedding-3-small` → 1536). If the n8n workflow used `text-embedding-ada-002` (also 1536), you are compatible; if `text-embedding-3-large` (3072), update the env var.
- Confirm the Cohere rerank model id used by the n8n node matches `COHERE_RERANK_MODEL`.

# Portfolio RAG Backend (FastAPI)

RAG service backing the chat on the portfolio site (FastAPI + LangChain, Supabase Postgres). Frontend (`VITE_API_URL`) calls `POST /chat` with `{message, session_id}`.

## Architecture

```
Frontend (Vite/React)  ──POST /chat──▶  FastAPI
                                         ├─ input_guard (regex/deterministic)
                                         ├─ memory (postgres: chat_messages)
                                         ├─ AgentExecutor (LangChain)
                                         │    └─ tool: portfolio_kb
                                         │         └─ Supabase match_documents RPC + Cohere Rerank
                                         │            (rerank_score >= RERANK_MIN_SCORE filtresi)
                                         ├─ output_guard (regex/deterministic)
                                         └─ chat_logs (postgres, retrieval jsonb izi dahil)
```

İki ayrı veritabanı vardır:
- **Supabase** (`SUPABASE_URL` + service key, REST): `documents` vector tablosu + `match_documents` RPC → `migrations/002_vector_schema.sql`
- **Chat DB** (`DATABASE_URL`, asyncpg): `chat_messages` + `chat_logs` → `migrations/001_init.sql` + `003_chat_logs_retrieval.sql`

## Knowledge base (data/)

Jarvis'in bilgi tabanı `data/*.md` dosyalarıdır (yazım kuralları: `data/README.md`).
Markdown dosyaları header-bazlı chunklanır; her chunk'ın başına "Projeler > Business
Data Finder" gibi breadcrumb eklenir ve `{source, headers, chunk_index, content_hash,
ingested_at}` metadata'sıyla yazılır. Senkronizasyon idempotenttir (delete-by-source
sonra insert):

```bash
python -m app.ingest data/            # korpusu senkronize et
python -m app.ingest data/ --wipe     # önce tüm tabloyu temizle (kaynak adı değişince)
# veya deploy edilen container'da:
curl -X POST https://api.yasinharman.dev/admin/ingest-path \
  -H "X-API-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" \
  -d '{"path":"data"}'
```

## Retrieval eval

`eval/golden.yaml` 30 Türkçe soruluk golden settir (negatifler dahil).

```bash
python -m eval.run_eval --min-rate 0.85   # hit@4 raporu, eşik altında exit 1
pytest -m "not integration"               # ağsız unit testler (chunklama)
pytest -m integration                     # golden set, gerçek anahtar ister
```

`RERANK_MIN_SCORE` ayarı: negatif sorular sızıyorsa yükselt (~0.3), geçerli kısmi
eşleşmeler kesiliyorsa düşür (~0.15).

## Local dev

```bash
# Ortam kurulumu repo kokunden yapilir; backend kendi .venv'ini tutmaz.
cd <repo-root> && npm run setup      # kok .venv olusturur + backend'i editable kurar
. .venv/bin/activate

cd backend
cp .env.example .env       # fill credentials; keep MODE=local so dev never writes to the prod DB

# apply migrations to your dev postgres
psql "$DATABASE_URL" -f migrations/001_init.sql
psql "$DATABASE_URL" -f migrations/003_chat_logs_retrieval.sql
# 002_vector_schema.sql Supabase SQL editöründe çalıştırılır (vector store orada)

uvicorn app.main:app --reload --port 8000
curl -s -X POST localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Yasin hangi projeleri yaptı?","session_id":"local-1"}'
```

## Ingest a single document (opsiyonel ek kaynak)

`data/` korpusunun disinda kalan tekil bir belgeyi (PDF/DOCX) da besleyebilirsin.
Ornekteki dosya repoda tutulmaz; kendi yolunu ver.

```bash
python -m app.ingest /path/to/belge.pdf --source cv
# or via HTTP
curl -X POST http://localhost:8000/admin/ingest \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@/path/to/belge.pdf" \
  -F "source=cv"
```

Aynı `source` etiketiyle tekrar ingest, eski chunk'ları silip yenilerini yazar.

## Deploy to Coolify

1. Push the `backend/` directory to your repo.
2. Coolify → New Resource → Application → Public Repository (or Git provider). Build pack: Dockerfile, base directory `backend/`.
3. Set env vars from `.env.example` in the Coolify UI. **Set `MODE=prod`** — this is the switch that enables DB persistence (`chat_messages` + `chat_logs`); `MODE=local` disables all DB writes and is meant for development only. If `MODE` is left unset it defaults to `prod`, and a missing `DATABASE_URL` then stops the app at startup instead of silently dropping writes. `DATABASE_URL` points to the Coolify-internal `chatlogs-db` Postgres (chat memory + logs); the vector store is reached over Supabase REST (`SUPABASE_URL` + service key).
4. Add a domain (e.g. `api.yasinharman.dev`) — Coolify provisions Traefik + Let's Encrypt automatically.
5. Apply migrations once:
   - Chat DB (Coolify terminal / pgAdmin): `migrations/001_init.sql` + `migrations/003_chat_logs_retrieval.sql`
   - Supabase (SQL editor): `migrations/002_vector_schema.sql`
6. Smoke test: `curl https://api.yasinharman.dev/healthz`.
7. Update the frontend env in Coolify: `VITE_API_URL=https://api.yasinharman.dev/chat`, rebuild & redeploy.

## Notes

- Embedding dimension is 1536 (`text-embedding-3-small`), verified against the live
  `documents` table on 2026-07-19 (see `migrations/000_live_snapshot.txt`).

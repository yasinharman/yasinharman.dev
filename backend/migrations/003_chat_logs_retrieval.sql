-- target: chat
-- 003: Retrieval gözlemlenebilirliği — CHAT DB'de çalıştırılır (DATABASE_URL,
-- Coolify'daki Postgres; pgAdmin veya psql ile). Supabase'de DEĞİL.
-- Her allowed /chat isteğinde getirilen chunk'lar (source, headers, skorlar) buraya yazılır.

ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS retrieval jsonb;

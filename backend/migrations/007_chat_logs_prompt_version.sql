-- target: chat
-- 007: Prompt sürümü. Prompt'lar kod içinde string; hangi sürümle üretildiği
-- yazılmayınca "bu ret eski bottan mı, bugün de oluyor mu?" sorusu DB'den
-- cevaplanamıyordu (2026-08-26'da 27 reddi tek tek canlı bota sormak gerekti).
-- Değer app/version.py'de: SYSTEM_PROMPT + ROUTER_PROMPT + iki model adının hash'i.
ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS prompt_version text;
CREATE INDEX IF NOT EXISTS idx_chat_logs_prompt_version
  ON chat_logs(prompt_version, created_at);

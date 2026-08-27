-- target: chat
-- 005: Router gözlemlenebilirliği — CHAT DB'de çalıştırılır (DATABASE_URL,
-- Coolify'daki Postgres; pgAdmin veya psql ile). Supabase'de DEĞİL.
--
-- Router'ın kararı (category / resolved_query / kb_query) artık açık bir değer.
-- Buraya yazılmazsa "hangi soru hangi kategoriye düştü" sorusunu yine canlı bota
-- tek tek sorarak cevaplamak zorunda kalırız — bugün tam olarak bunu yaşadık.
--
-- Uygulanmadan önce de kod çalışır: logging_db kademeli olarak geriler ve satırı
-- route'suz yazar.

ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS route jsonb;

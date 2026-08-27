-- target: chat
-- 006: Latency ayrıştırması. chat_logs tek bir latency_ms tutuyordu; yavaşlığın
-- router'dan mı, retrieval'dan mı, LLM'den mi geldiği DB'den okunamıyordu.
-- {"router_ms": .., "retrieval_ms": .., "llm_ms": .., "toplam_ms": ..}
--
-- Ayrı kolonlar yerine jsonb: aşamalar değişecek (3.4 reformulate döngüsü bir
-- tane daha ekleyecek) ve her aşama için yeni bir migration istemiyoruz.
ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS timings jsonb;

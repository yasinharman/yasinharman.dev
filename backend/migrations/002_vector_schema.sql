-- target: supabase
-- 002: Vector store şeması — SUPABASE'de çalıştırılır (SQL editörü).
-- İdempotent: canlı DB'de tablo/index varsa dokunmaz, RPC'yi 4-arg imzayla yeniler.
-- Canlı durum tespiti: id bigint, embedding vector(1536) (bkz. 000_live_snapshot.txt)

CREATE EXTENSION IF NOT EXISTS vector;

-- Canlıda no-op; temiz ortam kurulumu için niyet belgesi.
CREATE TABLE IF NOT EXISTS documents (
  id        bigserial PRIMARY KEY,
  content   text NOT NULL,
  metadata  jsonb NOT NULL DEFAULT '{}',
  embedding vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_documents_embedding_hnsw
  ON documents USING hnsw (embedding vector_cosine_ops);

-- sync_source'un delete-by-source sorgusu için.
CREATE INDEX IF NOT EXISTS idx_documents_source
  ON documents ((metadata->>'source'));

-- Eski 3-arg imza kaldırılıp 4-arg olarak yeniden oluşturulur.
-- Overload bırakılmaz: PostgREST isimli-arg çözümlemesi çift imzada belirsizleşir.
DROP FUNCTION IF EXISTS match_documents(vector, int, jsonb);

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_count     int   DEFAULT 10,
  filter          jsonb DEFAULT '{}',
  match_threshold float DEFAULT 0.0
) RETURNS TABLE (id bigint, content text, metadata jsonb, similarity float)
LANGUAGE sql STABLE AS $$
  SELECT d.id, d.content, d.metadata,
         1 - (d.embedding <=> query_embedding) AS similarity
  FROM documents d
  WHERE d.metadata @> filter
    AND 1 - (d.embedding <=> query_embedding) >= match_threshold
  ORDER BY d.embedding <=> query_embedding
  LIMIT match_count;
$$;

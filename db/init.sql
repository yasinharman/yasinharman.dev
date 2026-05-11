CREATE TABLE IF NOT EXISTS chat_logs (
  id           BIGSERIAL PRIMARY KEY,
  session_id   TEXT,
  user_message TEXT NOT NULL,
  ai_response  TEXT,
  status       TEXT NOT NULL,
  latency_ms   INTEGER,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_logs_session ON chat_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_created ON chat_logs(created_at DESC);

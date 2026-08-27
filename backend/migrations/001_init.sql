-- target: chat
CREATE TABLE IF NOT EXISTS chat_messages (
  id           BIGSERIAL PRIMARY KEY,
  session_id   TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content      TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS chat_logs (
  id           BIGSERIAL PRIMARY KEY,
  session_id   TEXT NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('allowed','blocked')),
  reason       TEXT,
  user_message TEXT NOT NULL,
  ai_response  TEXT,
  latency_ms   INTEGER,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chat_logs_session ON chat_logs(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_logs_status ON chat_logs(status, created_at);

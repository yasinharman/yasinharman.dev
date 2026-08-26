-- 004: Hata gözlemlenebilirliği — CHAT DB'de çalıştırılır (DATABASE_URL,
-- Coolify'daki Postgres; pgAdmin veya psql ile). Supabase'de DEĞİL.
--
-- 001_init.sql chat_logs.status'u CHECK (status IN ('allowed','blocked')) ile
-- kısıtlıyor. /chat artık agent patladığında satır yazdığı için üçüncü bir
-- durum gerekiyor; bu kısıt olmadan hata loglamasının KENDİSİ patlar.
--
-- ÖNCE kısıtın gerçek adını doğrulayın — aşağıdaki ad Postgres'in ürettiği
-- varsayılan, farklıysa DROP sessizce geçer ve eski kısıt yerinde kalır:
--
--   SELECT conname FROM pg_constraint
--   WHERE conrelid = 'chat_logs'::regclass AND contype = 'c';
--
-- Uygulanmadan önce de kod çalışır: logging_db.py CheckViolationError'ı
-- yakalayıp satırı status='blocked', reason='error:<Tip>' olarak yazar.

ALTER TABLE chat_logs DROP CONSTRAINT IF EXISTS chat_logs_status_check;
ALTER TABLE chat_logs ADD  CONSTRAINT chat_logs_status_check
  CHECK (status IN ('allowed','blocked','error'));

"""Migration runner — ağsız kısımlar."""
import pytest

from app.migrate import MIGRATIONS_DIR, _hedef, chat_migrations


def test_supabase_migrationi_chat_listesine_girmez():
    """002 vektör store'a ait ve chat DB'de anlamsız (CREATE EXTENSION vector,
    match_documents RPC). Yanlış DB'de koşarsa deploy'u komple düşürür."""
    surumler = [s for s, _ in chat_migrations()]
    assert "002_vector_schema" not in surumler
    assert "001_init" in surumler and "005_chat_logs_route" in surumler


def test_sirali_uygulanir():
    surumler = [s for s, _ in chat_migrations()]
    assert surumler == sorted(surumler)


def test_hedefsiz_dosya_sessizce_atlanmaz():
    """Sessiz atlama en kötü senaryo: migration uygulandı sanılır, uygulanmamıştır."""
    with pytest.raises(ValueError, match="target"):
        _hedef("ALTER TABLE chat_logs ADD COLUMN x int;", "099_yeni.sql")
    with pytest.raises(ValueError, match="bilinmeyen hedef"):
        _hedef("-- target: mongodb\n", "099_yeni.sql")


def test_her_migration_dosyasinin_hedefi_var():
    """Yeni bir .sql eklenip yönerge unutulursa bu test kırılır — koşarken değil."""
    for p in sorted(MIGRATIONS_DIR.glob("*.sql")):
        _hedef(p.read_text(encoding="utf-8"), p.name)


# --- run_migrations mantığı: gerçek DB olmadan --------------------------------
# Bağlantı sahte çünkü ölçülmek istenen şey SQL değil, karar: hangi sürüm atlanır,
# hangisi uygulanır, kayıt düşülür mü, kilit alınıp bırakılır mı. SQL'in kendisi
# ayrıca gerçek Postgres 18'de iki kez üst üste koşturularak doğrulandı.
class _SahteTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _SahteCon:
    def __init__(self, uygulanan):
        self._uygulanan = list(uygulanan)
        self.calisan: list[tuple] = []

    async def execute(self, sql, *args):
        self.calisan.append((sql, args))

    async def fetch(self, sql):
        return [{"version": v} for v in self._uygulanan]

    def transaction(self):
        return _SahteTx()


class _SahtePool:
    def __init__(self, con):
        self._con = con

    def acquire(self):
        con = self._con

        class _Ctx:
            async def __aenter__(self):
                return con

            async def __aexit__(self, *a):
                return False

        return _Ctx()


def _kaydedilenler(con) -> list[str]:
    return [args[0] for sql, args in con.calisan if "INSERT INTO schema_migrations" in sql]


async def test_uygulanmamislar_sirayla_uygulanir(monkeypatch):
    from app import migrate

    con = _SahteCon([])
    monkeypatch.setattr(migrate, "pool", lambda: _SahtePool(con))
    yeni = await migrate.run_migrations()

    assert yeni == [s for s, _ in migrate.chat_migrations()]
    assert _kaydedilenler(con) == yeni, "her uygulanan sürüm schema_migrations'a yazılmalı"


async def test_uygulanmis_surum_tekrar_kosmaz(monkeypatch):
    from app import migrate

    hepsi = [s for s, _ in migrate.chat_migrations()]
    con = _SahteCon(hepsi[:-1])
    monkeypatch.setattr(migrate, "pool", lambda: _SahtePool(con))

    assert await migrate.run_migrations() == [hepsi[-1]]


async def test_kilit_alinir_ve_birakilir(monkeypatch):
    """Rolling deploy'da iki konteyner aynı anda DDL koşarsa yarışır."""
    from app import migrate

    con = _SahteCon([])
    monkeypatch.setattr(migrate, "pool", lambda: _SahtePool(con))
    await migrate.run_migrations()

    cagrilar = [sql for sql, _ in con.calisan]
    assert any("pg_advisory_lock" in s for s in cagrilar)
    assert any("pg_advisory_unlock" in s for s in cagrilar)

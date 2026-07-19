# Korpus Yazım Kuralları

Bu klasördeki `.md` dosyaları Jarvis'in bilgi tabanıdır. `python -m app.ingest data/`
ile Supabase vector store'a senkronize edilir (idempotent: tekrar çalıştırmak
mükerrer kayıt üretmez).

Kurallar:

- **Her H2 (`##`) bölümü = bir "bilgi birimi."** Chunklama header bazlıdır; bir bölüm
  tek başına okunduğunda anlamlı olmalıdır.
- **Bölümleri ~800 karakterin altında tut** ki tek chunk olarak kalsın
  (`CHUNK_SIZE=1000`, breadcrumb prefix'i de sayılır).
- **İsim ve eş anlamlıları doğal biçimde tekrarla** ("Yasin", proje adları, teknoloji
  adları) — embedding recall'unu artırır.
- Üçüncü şahıs anlatım kullan ("Yasin ... geliştirdi") — asistan bu tonda konuşur.
- İçerik değişince: commit + `POST /admin/ingest-path {"path": "data"}` (veya lokalde
  `python -m app.ingest data/`) ile yeniden senkronize et.

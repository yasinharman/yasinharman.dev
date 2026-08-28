# Mimari

Sistem iki bagimsiz deploy edilen parcadan olusur: bir React/Vite SPA ve bir
FastAPI RAG servisi. Aralarindaki tek bag HTTP'dir (`VITE_API_URL`), bu yuzden
ikisi Coolify'da ayri uygulamalar olarak yasar ve birbirinden bagimsiz
yeniden deploy edilebilir.

Bu dosya sistemin genel resmini anlatir. Backend'in kurulumu, eval'i ve deploy
adimlari icin `backend/README.md`; hizli baslangic icin kok `README.md`.

## Bilesenler

| Parca | Teknoloji | Deploy | Domain |
|---|---|---|---|
| `frontend/` | React 18 + Vite 5 + Tailwind, nginx ile servis edilir | Coolify, base dir `frontend/` | `yasinharman.dev` |
| `backend/` | FastAPI + LangChain, uvicorn | Coolify, base dir `backend/` | `api.yasinharman.dev` |

## Sohbet akisi (`POST /chat`)

```
Tarayici
   │  { message, session_id }
   ▼
FastAPI  (backend/app/routes/chat.py)
   │
   ├─ rate limit         app/ratelimit.py   20/dk IP, 100/gun session -> 429
   │
   ├─ input_guard        app/guards.py      politika disi soruyu reddeder
   │
   ├─ memory             app/memory.py      chat_messages'tan son N mesaj
   │                                        (HISTORY_LIMIT)
   │
   ├─ AgentExecutor      app/agent.py       LangChain agent + system prompt
   │     └─ tool: portfolio_kb
   │          └─ retriever  app/retriever.py
   │               ├─ Supabase match_documents RPC  (vector arama)
   │               └─ Cohere Rerank                 (dagilima gore esik, asagi bak)
   │
   ├─ output_guard       app/guards.py      politika disi yaniti filtreler
   │
   └─ chat_logs          app/logging_db.py  allowed/blocked/error her istegi loglar
                                            (retrieval izi jsonb olarak)
   │
   ▼
{ response }  ->  frontend/src/components/ChatInterface.jsx
```

Yanit alani esnektir: frontend `response`, `output`, `text`, `message`, `reply`,
`answer` alanlarindan hangisi gelirse onu render eder; dizi donerse ilk elemani
alir.

## Iki ayri veritabani

Isimleri karistirmak kolay oldugu icin ayrimi net tutmak gerekir:

| | Vector store | Chat DB |
|---|---|---|
| Env | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | `DATABASE_URL` |
| Erisim | Supabase REST | asyncpg |
| Tablolar | `documents` + `match_documents` RPC | `chat_messages`, `chat_logs` |
| Migration | `migrations/002_vector_schema.sql` (Supabase SQL editorunde) | `001_init.sql`, `003_chat_logs_retrieval.sql` |
| Ne tutar | Jarvis'in bilgi tabani (embedding) | Oturum hafizasi + istek loglari |

`MODE` degiskeni Chat DB yazimlarinin anahtaridir: `MODE=local` hicbir sey
yazmaz (gelistirme), `MODE=prod` yazar. Tanimsiz birakilirsa `prod` kabul
edilir ve `DATABASE_URL` eksikse uygulama startup'ta durur - sessizce veri
kaybetmek yerine.

## Bilgi tabani ve ingest

Jarvis'in bildigi her sey `backend/data/*.md` dosyalarindan gelir. Yazim
kurallari `backend/data/README.md`'de.

```
backend/data/*.md
   │  header-bazli chunklama (## = bir bilgi birimi)
   │  her chunk'a "Projeler > Business Data Finder" gibi breadcrumb eklenir
   ▼
OpenAI embedding (text-embedding-3-small, 1536 boyut)
   │
   ▼
Supabase documents tablosu
```

Senkronizasyon idempotenttir (delete-by-source, sonra insert), yani ayni
komutu tekrar calistirmak mukerrer kayit uretmez:

```bash
cd backend && python -m app.ingest data/
# veya canlida:
curl -X POST https://api.yasinharman.dev/admin/ingest-path \
  -H "X-API-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" \
  -d '{"path":"data"}'
```

Endpoint yalnizca `backend/data/` altindaki yollari kabul eder (400 disinda). Tum
korpusu silen `--wipe` HTTP'de YOK, sadece CLI'da: sizmis bir admin key tek istekle
vektor store'u silememeli.

**Korpus degistiginde ingest calistirilmazsa Jarvis eski bilgiyi anlatmaya
devam eder.** `data/*.md` commit'lemek tek basina yeterli degildir.

## Gelistirme topolojisi

`npm run dev` iki sunucuyu birlikte ayaga kaldirir (`scripts/dev.sh`):

```
localhost:5173  Vite dev server
     │
     └─ /api/*  ──proxy──▶  127.0.0.1:8000  uvicorn
```

Proxy sayesinde `VITE_API_URL=/api/chat` gibi goreli bir adres kullanilabilir;
boylece telefondan veya tek bir Cloudflare tunnel'i uzerinden test ederken
ikinci bir tunnel gerekmez (`frontend/vite.config.js`).

`app/config.py` `.env`'i modulun yanindan MUTLAK yolla okur (`ENV_FILE`), yani
calisma dizini ne olursa olsun ayni dosya bulunur — testler repo kokunden de
kosabilsin diye boyle. `scripts/dev.sh` yine de uvicorn'u `backend/` icinden
baslatir (`migrations/`, `data/` goreli yollari). Bu uc dosya birbirine bagli: `config.py`, `scripts/dev.sh`
ve `backend/Dockerfile` (`WORKDIR /app` + `COPY app|migrations|data`).

## Origin erisimi (Cloudflare)

```
Ziyaretci ──▶ Cloudflare edge ──▶ Traefik ──▶ uvicorn
                    │                └─ XFF'e gordugu peer'i EKLER
                    └─ CF-Connecting-IP'yi kendisi yazar
```

Rate limit'in anahtari `CF-Connecting-IP`. O header'a ancak istek gercekten
Cloudflare'dan geldiyse guvenilebilir — `app/cloudflare.py` XFF'in son elemani
(Traefik'in gordugu, istemcinin uyduramadigi adres) yayinlanmis edge
araliklarinda mi diye bakar. Degilse header yok sayilir ve kova o adrese baglanir
(`app/ratelimit.py::identify_client`), ayrica `dogrudan_origin` uyarisi loglanir.

Uygulama katmani tek basina yetmez: Cloudflare atlandiginda WAF ve DDoS korumasi
da devre disi kalir. Agdaki kural `scripts/origin-firewall.sh` ile sunucuya
yaziliyor — 80/443 yalnizca Cloudflare araliklarina acik, DOCKER-USER zincirinde
(Docker ufw'yi atlar, `ufw deny 443` sessizce etkisizdir).

Aralik listesi `backend/app/cloudflare.py` icinde sabit; nightly is akisindaki
`cloudflare-ip-listesi` isi her gece upstream ile karsilastirir.

## Kalite kapisi

`backend/eval/golden.yaml` 30 Turkce soruluk bir golden settir, negatif ornekler
dahil:

```bash
cd backend
python -m eval.run_eval --min-rate 0.85   # hit@4, esik altinda exit 1
pytest -m "not integration"               # agsiz unit testler
pytest -m integration                     # golden set, gercek anahtar ister
```

Rerank esigi: `RERANK_SCORE_THRESHOLD` (0.40). Bu skorun altindaki chunk LLM'e
gitmez ve hicbiri gecemezse arama BOS doner — kapsam disi bir soruya alakasiz chunk
vermek halusinasyon yuzeyi acar.

Deger olculdu: golden.yaml 30 vakada 0.15 ve 0.30 esiklerinde negatif vakalar
siziyordu ("maas beklentisi" sorusuna Upwork chunk'i 0.3638 ile geciyor, model cevabi
alakasiz bilgiyle dolduruyordu), 0.40'ta 30/30.

"Kac aramada 0 chunk dondu" sorusu `chat_logs.retrieval` -> `kept = 0` ile sorgulanir.


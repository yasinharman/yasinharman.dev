# Projeler

## Projelerin Listesi

Yasin Harman'ın geliştirdiği üç ana proje şunlardır:

- Kişisel Yapay Zeka Asistanı (yasinharman.dev) — RAG Agent (Jarvis)
- Uçtan Uca Otomatize İş İlanı ETL ve Dashboard Sistemi
- Business Data Finder (BusinessInfoFinder) — n8n Tabanlı Şirket İletişim Bilgisi
  Bulma Aracı

## Kişisel Yapay Zeka Asistanı (yasinharman.dev) — RAG Agent

Şu anda konuşmakta olduğunuz, RAG (Retrieval-Augmented Generation) mimarisine sahip
yapay zeka asistanıdır (Jarvis). Amaç, kullanıcıların Yasin hakkındaki bilgilere
doğal dil ile erişebilmesidir. Teknik bileşenler:

- Frontend: React + Vite tabanlı arayüz (ilk tasarım Aura Build ile yapıldı).
- Backend: Python FastAPI + LangChain tabanlı RAG servisi; agent, portfolio_kb
  adlı retrieval tool'unu kullanır.
- Vector store: Supabase (PostgreSQL + pgvector) üzerinde anlamsal veri depolama;
  OpenAI embedding modeli ve Cohere rerank ile iki aşamalı retrieval.
- LLM: OpenAI GPT-4o-mini; prompt mühendisliği ile modelin yalnızca tanımlı veri
  seti dahilinde cevap vermesi sağlandı (veri gizliliği ve yanıt tutarlılığı).
- Deployment: Docker ile containerize edildi, Coolify üzerinden canlıya alındı.
- Kaynak kod: github.com/yasinharman/PortfolioWebsite

## Uçtan Uca Otomatize İş İlanı ETL ve Dashboard Sistemi

5 farklı kariyer platformundan anahtar kelime tabanlı veri toplayıp analiz eden,
tamamen otomatize çalışan bir sistemdir. Teknik bileşenler:

- Python ve Scrapy ile ölçeklenebilir bir veri çekme (web scraping) katmanı.
- Çekilen verilerin ön işleme, normalleştirme ve doğrulama süreçleri.
- Yapılandırılmış verilerin SQLAlchemy ORM ile PostgreSQL veritabanına asenkron
  aktarımı.
- APScheduler ile 7/24 çalışan otomasyon.
- Docker konteyner yapısı ve DigitalOcean üzerinde canlı ortam.
- Streamlit ile interaktif Dashboard: ham verilerin kullanıcıya görsel sunumu.

## Business Data Finder — n8n Tabanlı Şirket İletişim Bilgisi Bulma Aracı

"Cold Approach" formatında çalışan firmalara müşteri verisi sağlamak amacıyla
geliştirilmiş, SerpAPI tabanlı ve herkesin kullanabileceği basit arayüze sahip bir
uygulamadır (BusinessInfoFinder). Teknik bileşenler:

- Backend ile frontend arasındaki veri akışı, n8n otomasyon platformu üzerinde
  kurgulanan dinamik bir iş akışı ile yönetilir; kullanıcı aramayı tetikler, n8n
  arama kriterlerine göre veriyi toplar ve sonuçları arayüze döner.
- Kullanıcının doğal dildeki isteği, OpenAI GPT-4o-mini modeli ile SerpAPI'nin
  anlayabileceği yapılandırılmış JSON search query formatına dönüştürülür.
- Uygulama Docker ile containerize edilmiş ve Dokploy üzerinden deploy edilmiştir.
- Arayüz: Streamlit tabanlı basit bir web arayüzü.
- Kullanılan teknolojiler: n8n, SerpAPI, OpenAI GPT-4o-mini, Docker, Dokploy,
  Streamlit.

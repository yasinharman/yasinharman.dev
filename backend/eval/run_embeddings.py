"""Embedding modeli A/B — hangi model Türkçe korpusta daha iyi buluyor?

Rerank tarafında multilingual model seçilmiş (`rerank-multilingual-v3.0`) ama
embedding tarafında aynı düşünce uygulanmamış: `text-embedding-3-small`.
Daha iyisi olabilir; bu dosya tahmin etmek yerine ölçüyor.

NEDEN SUPABASE'E DOKUNMUYOR: korpus 18 chunk. Aday modeli denemek için ayrı bir
tablo + RPC + vector(N) migration + tam re-ingest gerekirdi; onun yerine 18 chunk
ve golden set soruları bellekte gömülüp kosinüs benzerliği burada hesaplanıyor.
Zincirin geri kalanı (Cohere rerank → eşik → özet genişletme → is_hit) modelden
bağımsız olduğu için canlı koddan aynen kullanılıyor.

Çalıştırma:  cd backend && python -m eval.run_embeddings
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import numpy as np
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.deps import supabase_client
from app.retriever import _apply_cutoff, _cohere, _expand_overviews, _rerank
from eval.run_eval import is_hit, load_golden

# (etiket, saglayici, model, boyut)
#
# 3-large'in dogal boyutu 3072 ama `dimensions` parametresiyle kisaltilabiliyor
# (Matryoshka). 1536'da kalirsa mevcut sema aynen kullanilabilir: vector(1536)
# migration'i, RPC degisikligi ve index kaybi YOK. Bu yuzden kisaltilmis hali
# ayri bir aday olarak olculuyor.
#
# 3072 pratikte kullanilamaz: pgvector'un hnsw/ivfflat index'leri 2000 boyutta
# tavan yapiyor, yani 3072'ye gecmek index'i tamamen kaybetmek demek. 18 chunk'ta
# onemsiz ama semayi index'siz birakmak bilerek alinacak bir karar olurdu.
ADAYLAR = [
    ("openai-3-small", "openai", "text-embedding-3-small", 1536),   # bugunku
    ("3-large@1536", "openai", "text-embedding-3-large", 1536),
    ("3-large@3072", "openai", "text-embedding-3-large", 3072),
    ("cohere-multi-v3", "cohere", "embed-multilingual-v3.0", 1024),
]


def _korpus() -> list[Document]:
    s = get_settings()
    resp = (supabase_client().table(s.SUPABASE_TABLE)
            .select("content, metadata").execute())
    return [Document(page_content=r["content"], metadata=r.get("metadata") or {})
            for r in (resp.data or [])]


def _goml(saglayici: str, model: str, metinler: list[str], sorgu: bool,
          boyut: int | None = None) -> np.ndarray:
    if saglayici == "openai":
        from openai import OpenAI
        cli = OpenAI(api_key=get_settings().OPENAI_API_KEY)
        # OpenAI'da belge/sorgu ayrimi yok; tek cagri.
        ek = {"dimensions": boyut} if boyut and model != "text-embedding-3-small" else {}
        r = cli.embeddings.create(model=model, input=metinler, **ek)
        v = [d.embedding for d in r.data]
    else:
        # Cohere'de input_type ZORUNLU ve yanlis verilmesi skorlari bozar:
        # belgeler search_document, sorgular search_query ile gomulur.
        r = _cohere().embed(texts=metinler, model=model,
                            input_type="search_query" if sorgu else "search_document",
                            embedding_types=["float"])
        v = r.embeddings.float_
    a = np.asarray(v, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


async def _olc(etiket: str, saglayici: str, model: str, boyut: int,
               docs: list[Document], golden: list[dict]) -> dict:
    s = get_settings()
    D = _goml(saglayici, model, [d.page_content for d in docs], sorgu=False)
    Q = _goml(saglayici, model, [g["question"] for g in golden], sorgu=True)
    benzerlik = Q @ D.T   # normalize edildi -> kosinus

    isabet = 0
    detay = []
    for i, entry in enumerate(golden):
        sira = np.argsort(-benzerlik[i])[: s.RETRIEVER_K]
        adaylar = []
        for j in sira:
            d = docs[j]
            adaylar.append(Document(page_content=d.page_content,
                                    metadata={**d.metadata,
                                              "similarity": float(benzerlik[i][j])}))
        reranked = await asyncio.to_thread(_rerank, entry["question"], adaylar,
                                           s.RERANK_TOP_N)
        kept, _ = _apply_cutoff(reranked, s)
        kept = await _expand_overviews(kept)
        hit = is_hit(entry, kept)
        isabet += hit
        if not hit:
            detay.append(entry["id"])
    return {"etiket": etiket, "model": model, "isabet": isabet,
            "toplam": len(golden), "kacan": detay}


def _dogru_chunklar(entry: dict, docs: list[Document]) -> list[int]:
    """Vakayi TEK BASINA karsilayan chunk'larin indeksleri."""
    return [i for i, d in enumerate(docs) if is_hit(entry, [d])]


def _sira_olc(etiket: str, saglayici: str, model: str, boyut: int,
              docs: list[Document], golden: list[dict]) -> dict:
    """Yalnizca VECTOR asamasini olcer: dogru chunk kacinci sirada geliyor?

    Hit rate uc modelde de doygun ciktigi icin ayirt edemiyor — RETRIEVER_K=12 ve
    korpus 18 chunk, yani vector asamasi zaten korpusun ucte ikisini getiriyor ve
    ne getirdiginin sirasi rerank tarafindan duzeltiliyor. Embedding'in kalitesi
    tam olarak O SIRA. Burada rerank YOK, kasitli.
    """
    D = _goml(saglayici, model, [d.page_content for d in docs], sorgu=False, boyut=boyut)
    Q = _goml(saglayici, model, [g["question"] for g in golden], sorgu=True, boyut=boyut)
    benzerlik = Q @ D.T

    siralar = []
    for i, entry in enumerate(golden):
        dogru = _dogru_chunklar(entry, docs)
        if not dogru:
            continue          # negatif vaka ya da hicbir chunk tek basina yetmiyor
        sirali = list(np.argsort(-benzerlik[i]))
        siralar.append(min(sirali.index(j) + 1 for j in dogru))

    n = len(siralar)
    return {
        "etiket": etiket, "model": model, "boyut": boyut, "vaka": n,
        "r1": sum(r <= 1 for r in siralar) / n,
        "r3": sum(r <= 3 for r in siralar) / n,
        "r5": sum(r <= 5 for r in siralar) / n,
        "mrr": sum(1 / r for r in siralar) / n,
        "ortalama": sum(siralar) / n,
        "en_kotu": max(siralar),
    }


async def _main(sadece: str | None, sira_modu: bool = False) -> int:
    docs = await asyncio.to_thread(_korpus)
    golden = load_golden()
    print(f"korpus: {len(docs)} chunk | golden: {len(golden)} vaka\n")

    if sira_modu:
        satirlar = [_sira_olc(e, sag, m, b, docs, golden)
                    for e, sag, m, b in ADAYLAR if not sadece or sadece == e]
        print(f"vector aşaması, rerank YOK — {satirlar[0]['vaka']} vaka\n")
        print("| model | boyut | recall@1 | recall@3 | recall@5 | MRR | ort. sıra | en kötü |")
        print("|---|---|---|---|---|---|---|---|")
        for r in satirlar:
            print(f"| `{r['model']}` | {r['boyut']} | %{100*r['r1']:.1f} | "
                  f"%{100*r['r3']:.1f} | %{100*r['r5']:.1f} | {r['mrr']:.3f} | "
                  f"{r['ortalama']:.2f} | {r['en_kotu']} |")
        return 0

    sonuc = []
    for etiket, saglayici, model, boyut in ADAYLAR:
        if sadece and sadece != etiket:
            continue
        r = await _olc(etiket, saglayici, model, boyut, docs, golden)
        r["boyut"] = boyut
        sonuc.append(r)
        print(f"{etiket:16} {model:26} boyut={boyut:5}  "
              f"{r['isabet']:2}/{r['toplam']:2} = %{100*r['isabet']/r['toplam']:5.1f}"
              + (f"   kaçan: {', '.join(r['kacan'])}" if r["kacan"] else ""))

    print("\n| model | boyut | hit rate |")
    print("|---|---|---|")
    for r in sonuc:
        print(f"| `{r['model']}` | {r['boyut']} | {r['isabet']}/{r['toplam']} "
              f"(%{100*r['isabet']/r['toplam']:.1f}) |")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Embedding modeli A/B")
    ap.add_argument("--sadece", help="tek bir adayı koş")
    ap.add_argument("--sira", action="store_true",
                    help="hit rate yerine vector aşamasının sırasını ölç")
    a = ap.parse_args()
    raise SystemExit(asyncio.run(_main(a.sadece, a.sira)))

"""Groundedness eval: cevaptaki iddialar getirilen chunk'larda var mı?

Tam /chat sırasını koşar (router → initial_context → agent), cevabı ve o cevabı
üretirken MODELE VERİLEN chunk'ları toplar, ikisini hakeme verir.

Gerçek OpenAI + Cohere + Supabase çağrısı yapar. MODE=local ile koşun.

Çalıştırma:  cd backend && python -m eval.run_groundedness [--min-temiz 1.0]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import warnings
from collections import Counter
from contextvars import ContextVar
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import agent as agent_modulu
from app.agent import agent_executor, initial_context
from app.router import classify, courtesy_reply, scope_reply
from eval.judge import degerlendir

warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

_YAML = Path(__file__).parent / "groundedness.yaml"


def _yukle() -> list[dict]:
    return yaml.safe_load(_YAML.read_text(encoding="utf-8"))


# Modele gosterilen chunk'lari toplamak icin agent'in arama fonksiyonu BIR KEZ,
# import aninda sarmalanir. Toplama ContextVar uzerinden yapilir; modul global'ini
# vaka basina degistirip geri almak, asyncio.gather ile kosarken vakalarin
# birbirinin chunk'larini toplamasina yol acardi. app.retriever.retrieval_trace
# ayni deseni kullaniyor.
#
# retrieval_trace'in kendisi burada ise yaramiyor: her sonucun yalnizca ilk 120
# karakterini tutuyor (chat_logs sismesin diye), hakem ise tam metne ihtiyac duyuyor.
_toplayici: ContextVar[list | None] = ContextVar("groundedness_chunklari", default=None)
_GERCEK_ARAMA = agent_modulu.kb_search


async def _arama_sarmali(query: str):
    docs = await _GERCEK_ARAMA(query)
    if (kutu := _toplayici.get()) is not None:
        kutu.extend(docs)
    return docs


agent_modulu.kb_search = _arama_sarmali


async def _cevapla(soru: str) -> tuple[str, list]:
    """Cevabı ve modele gösterilen TÜM chunk'ları döndürür.

    Sıra /chat ile birebir aynı: nezaket → router → initial_context → agent.
    Kısayol yapmıyoruz çünkü ölçülmek istenen şey canlıdaki cevabın kendisi.
    """
    toplanan: list = []
    _toplayici.set(toplanan)
    if (nazik := courtesy_reply(soru, "tr")) is not None:
        return nazik, []
    route = await classify(soru, [])
    if route.category != "career":
        return scope_reply(route.category, "tr"), []
    context = await initial_context(route.kb_query)
    out = await agent_executor("tr").ainvoke(
        {"input": route.resolved_query, "history": [], "context": context})
    return out.get("output") or "", toplanan


async def _vaka(case: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        cevap, docs = await _cevapla(case["question"])
        karar = await degerlendir(case["question"], cevap, docs)
    destekli = [i for i in karar.iddialar if i.destekli]
    desteksiz = [i for i in karar.iddialar if not i.destekli]
    return {**case, "cevap": cevap, "chunk": len(docs),
            "destekli": destekli, "desteksiz": desteksiz}


async def _main(min_temiz: float, eszaman: int) -> int:
    cases = _yukle()
    sem = asyncio.Semaphore(eszaman)
    sonuclar = await asyncio.gather(*(_vaka(c, sem) for c in cases))

    print(f"{'ID':<20} {'GRUP':<9} {'SONUÇ':<8} iddia (destekli/toplam)")
    print("-" * 74)
    grup_temiz, grup_toplam = Counter(), Counter()
    for r in sonuclar:
        n = len(r["destekli"]) + len(r["desteksiz"])
        temiz = not r["desteksiz"]
        grup_temiz[r["grup"]] += temiz
        grup_toplam[r["grup"]] += 1
        print(f"{r['id']:<20} {r['grup']:<9} {'TEMİZ' if temiz else 'UYDURMA':<8} "
              f"{len(r['destekli'])}/{n}  ({r['chunk']} chunk)")

    kirli = [r for r in sonuclar if r["desteksiz"]]
    if kirli:
        print("\n=== DESTEKSİZ İDDİALAR ===")
        for r in kirli:
            print(f"\n[{r['id']}] {r['question']}")
            if r.get("not"):
                print(f"  not: {r['not']}")
            for i in r["desteksiz"]:
                print(f"  ✗ {i.iddia}")
                print(f"      → {i.gerekce}")

    print("\n=== GRUP BAZINDA (temiz cevap oranı) ===")
    for g in ("duz", "doldurma", "yok"):
        if grup_toplam[g]:
            print(f"  {g:9} {grup_temiz[g]:2}/{grup_toplam[g]:2}")

    temiz_n = sum(grup_temiz.values())
    oran = temiz_n / len(sonuclar)
    iddia_n = sum(len(r["destekli"]) + len(r["desteksiz"]) for r in sonuclar)
    destekli_n = sum(len(r["destekli"]) for r in sonuclar)
    print(f"\n  Temiz cevap : {temiz_n}/{len(sonuclar)} = {oran:.1%}  (eşik: {min_temiz:.0%})")
    print(f"  İddia bazında: {destekli_n}/{iddia_n} destekli")
    return 0 if oran >= min_temiz else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Groundedness eval")
    # Varsayilan 1.0: tek bir uydurma bile kabul edilemez. Bu bir kalite hedefi
    # degil, yalan soylememe hedefi — %90 "cevaplarin onda biri yalan" demek.
    ap.add_argument("--min-temiz", type=float, default=1.0)
    ap.add_argument("--eszaman", type=int, default=3)
    a = ap.parse_args()
    raise SystemExit(asyncio.run(_main(a.min_temiz, a.eszaman)))

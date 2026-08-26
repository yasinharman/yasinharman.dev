"""Routing eval — sınıflandırma doğruluğunu ölçer.

İKİ MOD:

  baseline (bugün)  Ortada router yok; sınıflandırma 250 satırlık SYSTEM_PROMPT'un
                    içinde ve dışarı hiçbir değer vermiyor. O yüzden kategoriyi
                    DAVRANIŞTAN çıkarıyoruz: agent tool'u çağırdı mı, cevap sabit
                    ret metni mi. Kaba ama bugünün tek ölçüm yolu.

  router (FAZ 3.1)  Router açık bir `category` döndürünce bu dosya tek assert'e iner
                    ve LLM'in cevap üretmesine hiç gerek kalmaz.

Neyi ölçüyor: `career` sorularının kaçında GERÇEKTEN arama yapıldığını. Kritik olan
bu, çünkü canlı loglar aramadan verilen "bilgim yok"/"eğitildim" cevaplarının
yanlış olduğunu gösterdi (bkz. notes/yapilacaklar.md bulgu C).

Çalıştırma:  cd backend && python -m eval.run_routing
Gerçek OpenAI + Cohere + Supabase çağrısı yapar. MODE=local ile koşun: prod
chat_logs'a satır yazılmaz.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from pathlib import Path

import yaml
from langchain_core.messages import AIMessage, HumanMessage

_YAML = Path(__file__).parent / "routing.yaml"

# Sabit ret / bilgi yok metinlerinin ayirt edici parcalari.
_RET_ISARETLERI = ("eğitildim", "yardımcı olamam", "cevaplayamıyorum")
_BILGI_YOK_ISARETLERI = ("bilgim yok", "bilgi yok", "elimde bilgi")


def _yukle() -> list[dict]:
    return yaml.safe_load(_YAML.read_text(encoding="utf-8"))["cases"]


def _history(case: dict) -> list:
    msgs = []
    for m in case.get("history") or []:
        msgs.append(HumanMessage(content=m["content"]) if m["role"] == "user"
                    else AIMessage(content=m["content"]))
    return msgs


def _degerlendir(expect: str, aradi: bool, reddetti: bool) -> tuple[bool, str]:
    """(gecti_mi, gozlem) — kategori davranistan cikarilir."""
    if expect == "career":
        # Tek kural: aramis olmali. Aradiktan sonra "bilgi yok" demek mesru
        # (maas gibi korpusta olmayan sorular); ARAMADAN demek hata.
        return aradi, "aradı" if aradi else "ARAMADAN cevapladı"
    if expect in ("personal", "unrelated"):
        if aradi:
            return False, "gereksiz arama yaptı"
        return reddetti, "reddetti" if reddetti else "reddetmedi"
    if expect == "courtesy":
        if aradi:
            return False, "gereksiz arama yaptı"
        return not reddetti, "nazik karşılık" if not reddetti else "REDDETTİ"
    raise ValueError(f"bilinmeyen kategori: {expect}")


async def _calistir(case: dict, sem: asyncio.Semaphore) -> dict:
    from app.agent import agent_executor
    from app.retriever import retrieval_trace
    from app.router import courtesy_reply

    # /chat route'uyla AYNI sıra: deterministik nezaket kontrolü LLM'den önce gelir.
    nazik = courtesy_reply(case["question"], "tr")
    if nazik is not None:
        gecti, gozlem = _degerlendir(case["expect"], aradi=False, reddetti=False)
        return {**case, "gecti": gecti, "gozlem": f"{gozlem} (deterministik)",
                "aradi": False, "cevap": nazik[:150], "sorgular": []}

    async with sem:
        trace: list[dict] = []
        retrieval_trace.set(trace)
        try:
            result = await agent_executor("tr").ainvoke(
                {"input": case["question"], "history": _history(case)}
            )
            cevap = (result.get("output") or "").lower()
            hata = None
        except Exception as exc:  # noqa: BLE001 — tek vaka tüm eval'i düşürmesin
            cevap, hata = "", f"{type(exc).__name__}: {exc}"

    aradi = len(trace) > 0
    reddetti = (any(s in cevap for s in _RET_ISARETLERI)
                or (not aradi and any(s in cevap for s in _BILGI_YOK_ISARETLERI)))
    gecti, gozlem = (False, hata) if hata else _degerlendir(case["expect"], aradi, reddetti)

    return {**case, "gecti": gecti, "gozlem": gozlem, "aradi": aradi,
            "cevap": cevap[:150].replace("\n", " "),
            "sorgular": [t.get("query") for t in trace]}


async def _main(eszaman: int, sadece: str | None) -> int:
    cases = _yukle()
    if sadece:
        cases = [c for c in cases if c["expect"] == sadece]

    sem = asyncio.Semaphore(eszaman)
    sonuclar = await asyncio.gather(*(_calistir(c, sem) for c in cases))

    kategori = Counter()
    gecen = Counter()
    for r in sonuclar:
        kategori[r["expect"]] += 1
        gecen[r["expect"]] += bool(r["gecti"])

    print("\n=== KATEGORİ BAZINDA ===")
    for kat in ("career", "personal", "unrelated", "courtesy"):
        if not kategori[kat]:
            continue
        n, k = kategori[kat], gecen[kat]
        print(f"  {kat:10} {k:2}/{n:2}   %{100 * k / n:5.1f}")

    toplam, dogru = len(sonuclar), sum(r["gecti"] for r in sonuclar)
    print(f"\n  {'TOPLAM':10} {dogru:2}/{toplam:2}   %{100 * dogru / toplam:5.1f}")

    hatalar = [r for r in sonuclar if not r["gecti"]]
    if hatalar:
        print("\n=== BAŞARISIZ ===")
        for r in sorted(hatalar, key=lambda x: (not x.get("regression"), x["expect"])):
            bayrak = "🔴 " if r.get("regression") else "   "
            print(f"{bayrak}[{r['expect']:9}] {r['question']}")
            print(f"      → {r['gozlem']}")
            print(f"      cevap: {r['cevap']}")
            if r["sorgular"]:
                print(f"      sorgu: {r['sorgular']}")

    reg = [r for r in sonuclar if r.get("regression")]
    if reg:
        rk = sum(r["gecti"] for r in reg)
        print(f"\nRegresyon vakaları (canlıda kırık olduğu bilinen): {rk}/{len(reg)}")

    return 0 if not hatalar else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Routing eval")
    ap.add_argument("--eszaman", type=int, default=4, help="paralel istek sayısı")
    ap.add_argument("--sadece", help="yalnızca bu kategoriyi koş")
    a = ap.parse_args()
    raise SystemExit(asyncio.run(_main(a.eszaman, a.sadece)))

"""Routing eval — sınıflandırma doğruluğunu ölçer.

İKİ MOD:

  uçtan uca (varsayılan)  /chat'in TAM sırası: nezaket → router → agent. career
                    yolunda agent'ın gerçekten arama yapıp yapmadığını da ölçer,
                    yani "router doğru dedi ama agent yine reddetti" durumunu yakalar.

  --router          Yalnızca sınıflandırma; agent hiç çalışmaz. Ucuz ve hızlı,
                    router prompt'unu iterasyonla ayarlarken bu kullanılır.

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
import warnings
from collections import Counter
from pathlib import Path

import yaml
from langchain_core.messages import AIMessage, HumanMessage

# langchain, structured output cevabini serilestirirken zararsiz ama gurultulu bir
# pydantic uyarisi uretiyor; eval ciktisi okunabilir kalsin.
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

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
    """Uctan uca: /chat route'unun AYNI sirasini izler — nezaket, router, agent."""
    from app.agent import initial_context, kept_sayisi, select_runner
    from app.retriever import retrieval_trace
    from app.router import classify, courtesy_reply

    nazik = courtesy_reply(case["question"], "tr")
    if nazik is not None:
        gecti, gozlem = _degerlendir(case["expect"], aradi=False, reddetti=False)
        return {**case, "gecti": gecti, "gozlem": f"{gozlem} (deterministik)",
                "aradi": False, "cevap": nazik[:150], "sorgular": []}

    async with sem:
        try:
            route = await classify(case["question"], _history(case))
        except Exception as exc:  # noqa: BLE001
            return {**case, "gecti": False, "gozlem": f"router: {type(exc).__name__}: {exc}",
                    "aradi": False, "cevap": "", "sorgular": []}

    # career DISINDA agent hic calismaz: sabit cevap doner, retrieval yapilmaz.
    if route.category != "career":
        gecti, gozlem = _degerlendir(case["expect"], aradi=False, reddetti=True)
        return {**case, "gecti": gecti, "gozlem": f"{gozlem} → {route.category}",
                "aradi": False, "cevap": "", "sorgular": []}

    case = {**case, "question": route.resolved_query}
    async with sem:
        trace: list[dict] = []
        retrieval_trace.set(trace)
        try:
            context = await initial_context(route.kb_query)
            # Yol secimi route ile AYNI fonksiyondan geliyor.
            result = await select_runner(kept_sayisi(trace), "tr").ainvoke(
                {"input": case["question"], "history": _history(case), "context": context}
            )
            metin = result["output"] if isinstance(result, dict) else result.content
            cevap = (metin or "").lower()
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


async def _router_calistir(case: dict, sem: asyncio.Semaphore) -> dict:
    """Router'i IZOLE olcer: agent hic calismaz, vaka basina tek kucuk cagri."""
    from app.router import classify, courtesy_reply

    nazik = courtesy_reply(case["question"], "tr")
    if nazik is not None:
        gecti = case["expect"] == "courtesy"
        return {**case, "gecti": gecti, "gozlem": "courtesy (deterministik)",
                "aradi": False, "cevap": "", "sorgular": []}

    async with sem:
        try:
            route = await classify(case["question"], _history(case))
        except Exception as exc:  # noqa: BLE001 — tek vaka tüm eval'i düşürmesin
            return {**case, "gecti": False, "gozlem": f"{type(exc).__name__}: {exc}",
                    "aradi": False, "cevap": "", "sorgular": []}

    gecti = route.category == case["expect"]
    return {**case, "gecti": gecti,
            "gozlem": f"{route.category}  (beklenen {case['expect']})",
            "aradi": route.category == "career", "cevap": route.resolved_query[:150],
            "sorgular": [route.kb_query] if route.kb_query else []}


async def _main(eszaman: int, sadece: str | None, router: bool = False) -> int:
    cases = _yukle()
    if sadece:
        cases = [c for c in cases if c["expect"] == sadece]

    sem = asyncio.Semaphore(eszaman)
    kosucu = _router_calistir if router else _calistir
    print(f"mod: {'router (izole)' if router else 'baseline (bugünkü sistem)'}")
    sonuclar = await asyncio.gather(*(kosucu(c, sem) for c in cases))

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
    ap.add_argument("--router", action="store_true",
                    help="router'ı izole ölç (agent çalışmaz)")
    a = ap.parse_args()
    raise SystemExit(asyncio.run(_main(a.eszaman, a.sadece, a.router)))

"""Groundedness hakemi — cevaptaki her iddia getirilen chunk'larda var mı?

Neden var: SYSTEM_PROMPT'ta "uydurma" kelimesi 6 kez geçiyor ama hiçbir yerde
ölçülmüyordu. Portfolyo asistanında halüsinasyon en pahalı hata — recruiter'a
olmayan bir sertifika söylemek yalandır — ve 2026-08-26'da gerçekten yaşandı:
"how do I reach him?" sorusuna model uydurma bir e-posta adresi üretti.

Hakem üretenden ayrı bir LLM'dir (OPENAI_JUDGE_MODEL, temperature=0). Aynı modele
kendi cevabını denetletmek ölçüm değil, kendi kendini onaylamaktır.
"""
from __future__ import annotations

from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import get_settings

_HAKEM_PROMPT = """Sen bir GROUNDEDNESS hakemisin. Bir asistanın cevabını, o cevabı
üretirken kendisine verilen KAYNAK PARÇALARI ile karşılaştırırsın.

# GÖREVİN
1. Cevaptan, Yasin hakkındaki her OLGUSAL İDDİAYI ayrı ayrı çıkar.
2. Her iddia için: kaynak parçalarda AÇIKÇA yazıyor mu ya da doğrudan oradan
   çıkarılabiliyor mu?

# İDDİA SAYILMAYANLAR — bunları hiç listeleme
- Nezaket ve yardım teklifleri ("Başka bir sorunuz var mı?", "Yardımcı olabilirim").
- Bilgi yokluğu beyanları ("Bu konuda elimde bilgi yok", "Yasin ile iletişime geçin").
- Cevabın kendi yapısına dair cümleler ("Aşağıda projelerini listeledim").
- Genel dünya bilgisi ("Docker bir containerization aracıdır") — Yasin hakkında
  bir şey söylemiyorsa iddia değildir.

# DESTEKLİ SAYMA KURALLARI
- Yeniden ifade etme, özetleme, çeviri, biçimlendirme SERBEST. Aranan şey kelime
  eşleşmesi değil, İÇERİĞİN kaynakta bulunması.
- Kaynakta olmayan hiçbir ÖZGÜL bilgi eklenemez: isim, sayı, tarih, şirket, araç
  adı, URL, e-posta, sertifika, unvan. Bunlardan biri kaynakta yoksa DESTEKSİZ.
- Kaynak "X ve Y" derken cevap "X, Y ve Z" diyorsa Z desteksizdir.
- Kaynak bir şeyi ihtimal olarak söylerken cevap kesinlik veriyorsa desteksizdir.
- Emin değilsen DESTEKSİZ işaretle ve gerekçeye neden emin olmadığını yaz. Bu bir
  ölçüm aracı; şüpheyi cevabın lehine kullanmak ölçümü işe yaramaz hale getirir.

# TARİH VE SÜRE HESABI
Bugünün tarihi sana veriliyor. Kaynaktaki tarihlerden yapılan süre hesapları
"doğrudan çıkarılabilir" sayılır — AMA yalnızca SONUÇ DOĞRUYSA. Hesabı kendin
yap; yanlışsa DESTEKSİZ işaretle ve gerekçeye doğru değeri yaz.
Kaynak "Günümüz" diyorsa bitiş bugündür.
Toplam deneyim süresi geçen bir iddia varsa ŞU KONTROLÜ MUTLAKA YAP: kaynaktaki
en erken başlangıç tarihinden bugüne kaç ay geçmiş? İddiadaki toplam bundan
BÜYÜKSE desteksizdir — işler paralel sürmüştür ve aynı ay iki kez sayılmıştır.
Bu kontrol, aritmetiğin kendi içinde tutarlı olmasından bağımsızdır: "2 ay +
1 yıl 3 ay = 1 yıl 5 ay" toplama olarak doğru ama sonuç yine desteksizdir.
"Kaynakta toplam süre yazmıyor" TEK BAŞINA desteksizlik gerekçesi DEĞİLDİR —
aritmetik zaten kaynakta yazmaz; bakman gereken şey doğru yapılıp yapılmadığı.

# GEREKÇE
Desteklide kaynağın hangi kısmına dayandığını, desteksizde tam olarak neyin
eksik olduğunu tek cümleyle yaz. Türkçe yaz."""


class Iddia(BaseModel):
    iddia: str = Field(description="Cevaptan çıkarılan tek bir olgusal iddia")
    destekli: bool = Field(description="Kaynak parçalarda var mı")
    gerekce: str = Field(description="Tek cümlelik gerekçe")


class Karar(BaseModel):
    iddialar: list[Iddia]


def _hakem_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.OPENAI_JUDGE_MODEL, temperature=0, api_key=s.OPENAI_API_KEY)


def kaynak_metni(docs) -> str:
    return "\n\n---\n\n".join(
        f"[parça {i}] {d.page_content}" for i, d in enumerate(docs, 1)
    )


async def degerlendir(soru: str, cevap: str, docs) -> Karar:
    """Tek LLM çağrısı. docs boşsa cevabın hiçbir iddia içermemesi beklenir."""
    llm = _hakem_llm().with_structured_output(Karar, method="json_schema", strict=True)
    return await llm.ainvoke([
        SystemMessage(content=_HAKEM_PROMPT),
        HumanMessage(content=(
            f"# BUGÜNÜN TARİHİ\n{date.today().isoformat()}\n\n"
            f"# SORU\n{soru}\n\n"
            f"# ASİSTANIN CEVABI\n{cevap}\n\n"
            f"# KAYNAK PARÇALAR\n{kaynak_metni(docs) or '(hiç parça getirilmedi)'}"
        )),
    ])

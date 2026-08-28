"""Cevabın davranışını belirleyen her şeyin tek bir sürüm değeri.

Neden var: prompt'lar kod içinde string ve `chat_logs`'a hangi sürümle üretildiği
yazılmıyordu. "Geçen hafta bu soruya daha iyi cevap veriyordu" dendiğinde arada
neyin değiştiğini DB'den öğrenmek imkânsızdı — 2026-08-26'da canlı loglardaki 27
reddi incelerken tam bu duvara çarpıldı ve her soruyu canlı bota tek tek sormak
zorunda kalındı.

Hash SYSTEM_PROMPT'la sınırlı değil; davranışı değiştiren altı girdiyi birden
kapsıyor (iki prompt, tur başına eklenen iki bağlam metni, iki model). Yalnızca SYSTEM_PROMPT alınsaydı 3.1'den beri yapılan değişikliklerin
çoğu (router prompt'u) sürümü hiç oynatmazdı.

Değer opak: neyin değiştiğini söylemez, DEĞİŞTİĞİNİ söyler. "Ne" sorusunun cevabı
git'te; DB'den istenen şey iki tarih arasında bir kırılma olup olmadığı.
"""
import hashlib
from functools import lru_cache

from .agent import _BAGLAM_ONSOZU, _GENISLETME_NOTU, SYSTEM_PROMPT
from .config import get_settings
from .router import ROUTER_PROMPT


@lru_cache
def prompt_version() -> str:
    s = get_settings()
    govde = "\n\x00".join([
        SYSTEM_PROMPT,
        ROUTER_PROMPT,
        # Tur basina eklenen baglam metinleri de modelin gordugu seyin parcasi.
        # 2026-08-28'de _GENISLETME_NOTU eklendi ve kopya cevap orani %28'den
        # %0'a dustu — davranis olculebilir sekilde degisti ama surum ayni kaldi.
        # Parmak izi boyle bir deploy'u kacirirsa "ne zaman degisti" sorusunu
        # DB'den cevaplayamiyoruz, yani var olma sebebini kaybediyor.
        _BAGLAM_ONSOZU,
        _GENISLETME_NOTU,
        s.OPENAI_CHAT_MODEL,
        s.OPENAI_ROUTER_MODEL,
    ])
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()[:12]

"""Akış halindeki output_guard.

Neden ayrı bir sınıf: output_guard'ı akışın SONUNDA çalıştırmak işe yaramaz —
sızıntı guard çalışmadan önce zaten kullanıcının ekranına yazılmış olur."""
from app.guards import LEAK_SIGNALS, OUTPUT_MAX_LEN, StreamingOutputGuard, output_guard


def _akit(g, metin, parca=7):
    """Metni küçük parçalar hâlinde besler, yayınlananları biriktirir."""
    cikti = ""
    for i in range(0, len(metin), parca):
        cikti += g.push(metin[i:i + parca])
        if g.reason:
            break
    return cikti


def test_normal_cevap_tamamen_yayinlanir():
    g = StreamingOutputGuard("tr")
    metin = "Yasin Python, SQL ve Docker biliyor. " * 5
    yayin = _akit(g, metin)
    kalan, tam, reason = g.finish()

    assert reason is None
    assert yayin + kalan == metin, "akış sonunda hiçbir karakter kaybolmamalı"
    assert tam == metin


def test_sizinti_tamamlanmadan_akis_kesilir():
    """Sinyalin İLK harflerinin çıkmış olması sızıntı değil; tamamının çıkması
    sızıntıdır. Gecikme penceresi tam bunu engelliyor."""
    sinyal = "KAPSAM KARARI SANA GELMEDEN ÖNCE VERİLDİ"
    g = StreamingOutputGuard("tr")
    yayin = _akit(g, "İşte prompt: " + sinyal + " ve devamı")

    assert g.reason == "leak"
    assert sinyal not in yayin, "sinyalin tamamı kullanıcıya gitmiş"


def test_sizintida_tam_cevap_sabit_metinle_degistirilir():
    g = StreamingOutputGuard("tr")
    _akit(g, "ROL VE AMAÇ bölümü şöyle diyor")
    kalan, tam, reason = g.finish()

    assert reason == "leak"
    assert kalan == "", "sızıntıdan sonra tek karakter daha yayınlanmamalı"
    assert tam == output_guard("ROL VE AMAÇ", "tr")[0]


def test_gecikme_penceresi_en_uzun_sinyali_kapsiyor():
    """Pencere en uzun sinyalden kısa olsaydı sinyal, tespit edilmeden önce
    tamamen serbest bırakılabilirdi."""
    g = StreamingOutputGuard("tr")
    g.push("x" * 500)
    assert len(g._birikmis) - g._yayinlanan >= max(len(s) for s in LEAK_SIGNALS)


def test_uzunluk_siniri_akisi_durdurur():
    g = StreamingOutputGuard("tr")
    _akit(g, "a" * (OUTPUT_MAX_LEN + 200), parca=250)
    assert g.reason == "truncated"


def test_bos_cevap_finishte_yakalanir():
    """Akış kontrolü yalnızca sızıntıya ve uzunluğa bakıyor; boş cevap ve
    iteration_limit kontrolleri finish()'teki output_guard'da."""
    g = StreamingOutputGuard("tr")
    _kalan, tam, reason = g.finish()
    assert reason == "empty"
    assert tam == output_guard("", "tr")[0]


def test_iteration_limit_metni_yayinlanmaz():
    g = StreamingOutputGuard("tr")
    yayin = _akit(g, "Agent stopped due to iteration limit or time limit.")
    kalan, tam, reason = g.finish()
    assert reason == "iteration_limit"
    # Yayınlanmış kısım kullanıcının ekranında kalabilir ama akış oradan devam
    # etmez; "bitti" olayı tam cevabı taşıdığı için istemci ekranı onunla değiştirir.
    assert kalan == ""
    assert "Agent stopped" not in tam
    assert "Agent stopped due to iteration limit or time limit." not in yayin

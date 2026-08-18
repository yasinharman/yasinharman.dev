# İş Deneyimi

## İş Deneyimlerinin Listesi

Yasin Harman'ın iş tecrübeleri, çalıştığı yerler ve görevleri şunlardır:

- MegaGear — Software Engineer (Tam Zamanlı, Mayıs 2026 – Temmuz 2026). E-ticaret
  veri altyapısı, Customer/Product Scoring Engine ve Meta reklam senkronizasyon
  botu üzerinde çalıştı.
- Upwork — Scale AI (Freelance, Mayıs 2025 – Günümüz). Outlier platformunda
  kodlama ajanlarını ölçen değerlendirme görevleri hazırlıyor; LLM eğitimi ve
  yanıt değerlendirme projelerinde görev alıyor.

## MegaGear — Software Engineer (Tam Zamanlı, Mayıs 2026 – Temmuz 2026)

Yasin Harman, e-ticaret şirketi MegaGear'da Software Engineer olarak tam zamanlı
çalıştı. Bu görevde üç ana iş üzerinde çalıştı: e-ticaret veri altyapısı,
Customer/Product Scoring Engine ve Meta reklam senkronizasyon botu.

Veri altyapısı tarafında, şirketin satış yaptığı Etsy ve Shopify platformlarındaki
ham e-ticaret verilerini (yaklaşık 172.000 sipariş, iadeler ve ürün performans
verileri) tek merkezde toplayan PostgreSQL veritabanını tasarladı. Platform
API'lerinin sunmadığı verileri reverse engineering ile web scraping yaparak elde
etti ve iki platformdaki müşteri kayıtlarını e-posta üzerinden eşleştirerek tek
müşteri kimliği altında birleştirdi.

Customer/Product Scoring Engine olarak adlandırılan botu Python ile geliştirdi. Bu
bot 175.000'den fazla müşteriyi toplam harcaması, alışveriş sıklığı, satın alma
eğilimi ve müşteriyi kaybetme riski gibi metriklere göre pazarlama segmentlerine
(VIP, aggressive, retention, negative) ayırır. Aynı botun ürün tarafında, her ürünü
kârlılık, satış dönüşüm oranı, reklam getirisi (ROAS) ve stok durumuna göre
puanlayarak hangi ürüne ne kadar reklam bütçesi ayrılması gerektiğini belirleyen
skorlama modülünü yazdı.

Meta reklam senkronizasyon botunda ise, scoring engine'in ürettiği müşteri
segmentlerini Meta (Facebook/Instagram) reklam kampanyalarında hedef kitle ve hariç
tutma listeleri (Custom Audience) olarak kullanılmak üzere her gece reklam
platformuna otomatik yükleyen sistemi geliştirdi. Tüm sistemi Docker ile bulut
sunucu üzerinde zamanlanmış görevler halinde 7/24 çalıştırdı.

## Upwork — Scale AI (Freelance, Mayıs 2025 – Günümüz)

Yasin Harman, Scale AI ile Upwork üzerinden kontratlı olarak, Outlier platformunda
AI Engineer (yapay zeka mühendisi) olarak çalışmaktadır. Büyük dil modellerinin
(LLM) eğitilmesi ve yanıtlarının değerlendirilmesine yönelik projelerde görev alır;
asıl işi, gelişmiş kodlama ajanlarının gerçek projelerdeki kod düzenleme işlerindeki
başarısını ölçen değerlendirme görevleri hazırlamaktır.

Bu görevleri Python, Go ve Rust projelerindeki açık kaynak pull request'lerden yola
çıkarak kurgular. Hazırladığı her görev bir problem tanımı, public API arayüz tanımı,
geçti/kaldı şeklinde net değerlendirme kriterleri ve değişen kodu kapsayan bir test
paketinden oluşur.

Görevlerin zorluğunu bilinçli olarak tasarlar: örnek çözümde doğrudan
kopyalanabilecek kısımlar ile koda bakıp anlaşılması gereken davranışı birbirinden
ayırır ve değerlendirme kriterlerini ikincisine bağlar. Böylece görev tanımını
kopyalamak testi geçmeye yetmez, görev de ajanları gerçekten birbirinden ayırt eder.

Hazırladığı her görevi, aynı sonucu tekrar üretebilen Docker ortamlarında birkaç
aşamalı bir kontrolden geçirir: örnek çözümün tam puan alması, farklı modellerin
değerlendirme kriterleri üzerinde aynı sonuca varması ve görevin yeterince zor
sayılabilmesi için gelişmiş bir ajanın zorunlu kriterlerden en az birinde takılması
gerekir.

Yasin Harman, Upwork'te çeşitli otomasyon ve AI training işleri üzerinden bugüne
kadar 1600$ üzerinde kazanç elde etmiştir. Upwork profili:
upwork.com/freelancers/~013fbee1828b285d61

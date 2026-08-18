import { useLanguage } from '../i18n/LanguageContext';

/**
 * Şirket logoları docs/ klasöründen alınır ve kartın üst bölümünde arka plan
 * olarak kullanılır.
 *
 * Buradaki PNG'ler saydam zeminli ve markası beyazdır; koyu kart üzerinde
 * doğrudan çalışırlar, CSS filtresi gerekmez. Yeni bir logo eklerken de aynı
 * biçimi kullanın (saydam zemin + açık renkli marka), yoksa koyu kartın üstünde
 * görünmez veya beyaz bir kutu olarak çıkar.
 *
 * Yeni bir logo eklemek için: docs/ klasörüne dosyayı koy, aşağıya import et ve
 * ilgili deneyimin `logo` alanına yaz. `logo: null` bırakılırsa kart logosuz
 * görünür, bozulmaz.
 */
// ⬇️ DÜZENLE: MegaGear logosu — docs/ içindeki dosya adını yaz
import megagearLogo from '../../docs/megagear-logo.png';
// ⬇️ DÜZENLE: Upwork logosu — docs/ içindeki dosya adını yaz
import upworkLogo from '../../docs/upwork-logo.png';

/**
 * İş deneyimi verisi.
 * Metinler backend/data/deneyim.md ile aynı bilgiyi anlatır; oradaki bir kayıt
 * değişirse burayı da güncelleyin, yoksa sayfa ile Jarvis'in cevabı çelişir.
 *
 * Yeni bir deneyim eklemek için bu diziye yeni bir obje ekleyin; kartlar
 * ikişerli grid'de yukarıdan aşağı, dizideki sırayla akar.
 */
const EXPERIENCE_DATA = [
  {
    id: 'megagear',
    company: 'MegaGear',
    logo: megagearLogo,
    role: { tr: 'Software Engineer', en: 'Software Engineer' },
    type: { tr: 'Tam Zamanlı', en: 'Full-time' },
    period: { tr: 'Mayıs 2026 – Temmuz 2026', en: 'May 2026 – July 2026' },
    link: null,
    summary: {
      tr: "E-ticaret şirketi MegaGear'da veri altyapısı, müşteri/ürün skorlama motoru ve Meta reklam senkronizasyon botu olmak üzere üç ana iş üzerinde çalıştı.",
      en: 'Worked on three main areas at the e-commerce company MegaGear: the data infrastructure, the customer/product scoring engine and the Meta ad synchronisation bot.',
    },
    highlights: {
      tr: [
        "Etsy ve Shopify'daki ham e-ticaret verilerini (~172.000 sipariş, iadeler, ürün performansı) tek merkezde toplayan PostgreSQL veritabanını tasarladı.",
        'Platform API\'lerinin sunmadığı verileri reverse engineering ile web scraping yaparak elde etti; iki platformdaki müşterileri e-posta üzerinden tek kimlikte birleştirdi.',
        "175.000'den fazla müşteriyi harcama, sıklık, satın alma eğilimi ve kayıp riskine göre pazarlama segmentlerine ayıran Customer/Product Scoring Engine'i Python ile geliştirdi.",
        'Ürünleri kârlılık, dönüşüm oranı, ROAS ve stok durumuna göre puanlayarak reklam bütçesi dağılımını belirleyen skorlama modülünü yazdı.',
        'Müşteri segmentlerini her gece Meta Custom Audience listelerine yükleyen senkronizasyon botunu kurdu ve tüm sistemi Docker ile bulut sunucuda 7/24 çalıştırdı.',
      ],
      en: [
        'Designed the PostgreSQL database that centralises raw e-commerce data from Etsy and Shopify (~172,000 orders, returns and product performance data).',
        'Reverse engineered and scraped data the platform APIs did not expose, and merged customers across both platforms into a single identity by matching e-mail addresses.',
        'Built the Customer/Product Scoring Engine in Python, segmenting 175,000+ customers by total spend, purchase frequency, buying propensity and churn risk.',
        'Wrote the scoring module that ranks products by profitability, conversion rate, ROAS and stock level to decide how the ad budget is distributed.',
        'Built the bot that uploads customer segments to Meta Custom Audience lists every night, running the whole system 24/7 as scheduled jobs in Docker on a cloud server.',
      ],
    },
    techStack: ['Python', 'PostgreSQL', 'Web Scraping', 'Meta Marketing API', 'Docker'],
  },
  {
    id: 'upwork',
    company: 'Upwork — Scale AI',
    logo: upworkLogo,
    role: { tr: 'AI Training & Otomasyon', en: 'AI Training & Automation' },
    type: { tr: 'Freelance', en: 'Freelance' },
    period: { tr: 'Mayıs 2025 – Günümüz', en: 'May 2025 – Present' },
    link: 'https://www.upwork.com/freelancers/~013fbee1828b285d61',
    summary: {
      tr: 'Scale AI ile Upwork üzerinden kontratlı olarak, Outlier platformunda büyük dil modellerinin eğitilmesi ve yanıtlarının değerlendirilmesine yönelik projelerde görev alıyor.',
      en: 'Contracted with Scale AI through Upwork, working on the Outlier platform on projects that train large language models and evaluate their responses.',
    },
    highlights: {
      tr: [
        'Outlier platformunda LLM eğitimi ve yanıt değerlendirme projelerinde çalışıyor.',
        'Model çıktılarını karşılaştırıp puanlayarak eğitim verisinin kalitesine katkı sağlıyor.',
        "Upwork'te çeşitli otomasyon ve AI training işlerinden bugüne kadar 700$ üzerinde kazanç elde etti.",
      ],
      en: [
        'Works on LLM training and response evaluation projects on the Outlier platform.',
        'Compares and rates model outputs, contributing to the quality of the training data.',
        'Has earned over $700 to date from various automation and AI training jobs on Upwork.',
      ],
    },
    techStack: ['LLM Evaluation', 'Prompt Engineering', 'Python', 'Automation'],
  },
];

export function ExperiencePage() {
  const { language, t } = useLanguage();

  return (
    <div className="w-full min-h-screen bg-transparent py-12 px-4 sm:px-6 lg:px-8 font-sans selection:bg-orange-500/30">
      <div className="max-w-6xl mx-auto relative">
        <div className="absolute inset-0 bg-zinc-900/85 rounded-[2.5rem] border border-white/5 z-0 pointer-events-none" />

        <div className="relative z-10 py-16 px-6 md:px-12 flex flex-col items-center">
          <h1 className="text-3xl md:text-4xl font-medium tracking-tight text-zinc-100 mb-16 flex items-center gap-6 text-center">
            <span className="w-12 h-px bg-gradient-to-r from-transparent to-white/20 hidden sm:block" />
            {t.experience.heading}
            <span className="w-12 h-px bg-gradient-to-l from-transparent to-white/20 hidden sm:block" />
          </h1>

          <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-8 md:gap-10">
            {EXPERIENCE_DATA.map((exp) => (
              <article
                key={exp.id}
                className="group relative flex flex-col rounded-[2rem] overflow-hidden bg-zinc-950/80 border border-white/5 transition-colors duration-300 hover:border-orange-500/30"
              >
                <div className="relative flex flex-col justify-center px-6 py-8 md:px-8 min-h-[16rem] overflow-hidden">
                  {/* Bölümün arka planını kaplayan şirket logosu. */}
                  {exp.logo && (
                    <img
                      src={exp.logo}
                      alt=""
                      aria-hidden="true"
                      className="pointer-events-none select-none absolute top-0 right-0 h-full w-1/2 md:w-[46%] object-contain object-center p-4"
                      loading="lazy"
                      decoding="async"
                    />
                  )}

                  {/* Logoyu karartmadan metin tarafında kontrastı garantileyen
                      geçiş: soldan itibaren kararıyor, logonun başladığı yerde
                      tamamen saydam. */}
                  <div className="absolute inset-0 bg-gradient-to-r from-zinc-950 from-20% via-zinc-950/60 via-45% to-transparent to-55% pointer-events-none" />

                  <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(249,115,22,0.16)_0%,rgba(10,8,15,0)_65%)] pointer-events-none" />

                  <div className="relative min-w-0 max-w-[56%]">
                    <span className="text-orange-500 text-xs font-semibold tracking-widest uppercase mb-3 block">
                      {exp.type[language]}
                    </span>
                    <h2 className="text-2xl font-medium tracking-tight text-white text-balance leading-snug">
                      {exp.company}
                    </h2>
                    <p className="text-zinc-400 text-sm mt-1.5">{exp.role[language]}</p>
                  </div>

                  <div className="relative self-start mt-5 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-zinc-400">
                    <iconify-icon icon="solar:calendar-minimalistic-linear" class="text-sm"></iconify-icon>
                    <span>{exp.period[language]}</span>
                  </div>
                </div>

                <div className="flex flex-col flex-1 px-6 pb-6 md:px-8 md:pb-8 bg-zinc-950">
                  <div className="border-t border-white/5 pt-5">
                    <p className="text-zinc-300 text-sm md:text-base leading-relaxed font-light">
                      {exp.summary[language]}
                    </p>

                    <ul className="mt-5 space-y-3">
                      {exp.highlights[language].map((item, i) => (
                        <li key={i} className="flex gap-3 text-sm text-zinc-400 leading-relaxed font-light">
                          <iconify-icon
                            icon="solar:check-circle-linear"
                            class="text-base text-orange-500/70 shrink-0 mt-0.5"
                          ></iconify-icon>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mt-auto pt-6">
                    <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">
                      {t.experience.technologies}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {exp.techStack.map((tech, i) => (
                        <span
                          key={i}
                          className="px-3 py-1 text-xs font-medium rounded-full bg-white/5 border border-white/10 text-zinc-300"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>

                    {exp.link && (
                      <a
                        href={exp.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-zinc-300 hover:border-orange-500/40 hover:text-orange-400 transition-colors duration-300"
                      >
                        <iconify-icon icon="solar:link-linear" class="text-lg"></iconify-icon>
                        <span className="text-xs font-medium tracking-wide">{t.experience.viewProfile}</span>
                        <iconify-icon icon="solar:arrow-right-up-linear" class="text-sm"></iconify-icon>
                      </a>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

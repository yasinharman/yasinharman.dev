import { useLanguage } from '../i18n/LanguageContext';

/**
 * Şirket logoları src/assets/ klasöründen alınır ve kartın üst bölümünde arka plan
 * olarak kullanılır.
 *
 * Buradaki PNG'ler saydam zeminli ve markası beyazdır; koyu kart üzerinde
 * doğrudan çalışırlar, CSS filtresi gerekmez. Yeni bir logo eklerken de aynı
 * biçimi kullanın (saydam zemin + açık renkli marka), yoksa koyu kartın üstünde
 * görünmez veya beyaz bir kutu olarak çıkar.
 *
 * Yeni bir logo eklemek için: src/assets/ klasörüne dosyayı koy, aşağıya import et ve
 * ilgili deneyimin `logo` alanına yaz. `logo: null` bırakılırsa kart logosuz
 * görünür, bozulmaz.
 */
// ⬇️ DÜZENLE: MegaGear logosu — src/assets/ içindeki dosya adını yaz
import megagearLogo from '../assets/megagear-logo.png';
// ⬇️ DÜZENLE: Upwork logosu — src/assets/ içindeki dosya adını yaz
import upworkLogo from '../assets/upwork-logo.png';

/**
 * İş deneyimi verisi.
 * Maddeler Yasin'in CV'sindeki "Tecrübeler" bölümünden birebir alınmıştır ve
 * CV'nin birinci şahıs anlatımını korur. CV güncellenirse burası da güncellenmeli.
 * CV dosyasının kendisi repoda tutulmuyor (kişisel iletişim bilgisi içeriyor,
 * .gitignore'da).
 *
 * Not: backend/data/deneyim.md aynı bilgiyi üçüncü şahısla anlatır — asistan o
 * tonda konuştuğu için bilerek farklıdır, ikisini birbirine eşitlemeyin.
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
    highlights: {
      tr: [
        "Şirketin satış yaptığı Etsy ve Shopify platformlarındaki ham e-ticaret verilerini (yaklaşık 172.000 sipariş, iadeler ve ürün performans verileri) tek merkezde toplayan PostgreSQL veritabanını tasarladım; platform API'lerinin sunmadığı verileri reverse engineering ile web scraping yaparak elde ettim ve iki platformdaki müşteri kayıtlarını e-posta üzerinden eşleştirerek tek müşteri kimliği altında birleştirdim.",
        "Bu verileri kullanarak, 175.000'den fazla müşteriyi toplam harcaması, alışveriş sıklığı, satın alma eğilimi ve müşteriyi kaybetme riski gibi metriklere göre pazarlama segmentlerine (VIP, aggressive, retention, negative) ayıran Customer/Product Scoring Engine adlı botu Python kullanarak geliştirdim.",
        'Aynı botun ürün tarafında, her ürünü kârlılık, satış dönüşüm oranı, reklam getirisi (ROAS) ve stok durumuna göre puanlayarak hangi ürüne ne kadar reklam bütçesi ayrılması gerektiğini belirleyen skorlama modülünü geliştirdim.',
        'Botun ürettiği müşteri segmentlerini, Meta (Facebook/Instagram) reklam kampanyalarında hedef kitle ve hariç tutma listeleri (Custom Audience) olarak kullanılmak üzere her gece reklam platformuna otomatik yükleyen senkronizasyon botunu geliştirdim; tüm sistemi Docker ile bulut sunucu üzerinde zamanlanmış görevler halinde 7/24 çalıştırdım.',
      ],
      en: [
        'Designed the PostgreSQL database that centralises the raw e-commerce data from the Etsy and Shopify platforms the company sells on (roughly 172,000 orders, returns and product performance data); obtained the data the platform APIs did not expose through reverse engineering and web scraping, and merged customer records from both platforms into a single customer identity by matching e-mail addresses.',
        'Using that data, built a bot called the Customer/Product Scoring Engine in Python that sorts more than 175,000 customers into marketing segments (VIP, aggressive, retention, negative) by metrics such as total spend, purchase frequency, buying propensity and churn risk.',
        'On the product side of the same bot, developed the scoring module that rates every product by profitability, sales conversion rate, return on ad spend (ROAS) and stock level, determining how much ad budget each product should receive.',
        'Developed the synchronisation bot that uploads the customer segments the bot produces to Meta (Facebook/Instagram) every night, to be used as target audience and exclusion lists (Custom Audience) in ad campaigns; ran the whole system 24/7 as scheduled jobs on a cloud server with Docker.',
      ],
    },
    techStack: ['Python', 'PostgreSQL', 'Web Scraping', 'Meta Marketing API', 'Docker'],
  },
  {
    id: 'upwork',
    company: 'Upwork — Scale AI',
    logo: upworkLogo,
    role: { tr: 'AI Engineer', en: 'AI Engineer' },
    type: { tr: 'Freelance', en: 'Freelance' },
    period: { tr: 'Mayıs 2026 – Günümüz', en: 'May 2026 – Present' },
    link: 'https://www.upwork.com/freelancers/~013fbee1828b285d61',
    highlights: {
      tr: [
        "Outlier platformunda, Python, Go ve Rust projelerindeki açık kaynak pull request'lerden yola çıkarak, gelişmiş kodlama ajanlarını gerçek projelerdeki kod düzenleme işleri üzerinde ölçen değerlendirme görevleri hazırladım; her görevde bir problem tanımı, public API arayüz tanımı, geçti/kaldı şeklinde net kriterler ve değişen kodu kapsayan bir test paketi yer alıyor.",
        'Görevlerin zorluğunu rastgeleye bırakmadım: örnek çözümde doğrudan kopyalanabilecek kısımlar ile koda bakıp anlaşılması gereken davranışı ayırdım ve kriterleri ikincisine bağladım. Böylece tanımı kopyalamak geçmeye yetmiyor.',
        'Her görevi, aynı sonucu tekrar üretebilen Docker ortamlarında birkaç aşamalı bir kontrolden geçirdim: örnek çözümün tam puan alması, farklı modellerin kriterler üzerinde aynı sonuca varması ve görevin yeterince zor sayılması için gelişmiş bir ajanın zorunlu kriterlerden en az birinde takılması.',
        'Upwork platformunda çeşitli otomasyon ve AI training işleri üzerinden bugüne kadar 1600$ üzerinde kazanç elde ettim.',
      ],
      en: [
        'On the Outlier platform, built end-to-end evaluation tasks from merged open-source pull requests across Python, Go and Rust that measure frontier coding agents on real-world refactors — each with a problem statement, a public-API interface specification, binary pass/fail grading criteria and a diff-coverage test suite.',
        'Engineered task difficulty as a design decision: separated the mechanically transcribable surface of each reference patch from the behaviour that has to be inferred, then anchored the grading criteria to the latter, so copying the specification is not enough to pass.',
        'Validated every task in reproducible Docker environments through a multi-stage pipeline: a reference-solution run that had to score perfectly, multi-model agreement on the grading criteria, and a difficulty gate requiring a frontier agent to fail at least one mandatory criterion.',
        'Have earned over $1,600 to date from various automation and AI training jobs on the Upwork platform.',
      ],
    },
    techStack: ['LLM Evaluation', 'AI Agent Benchmarking', 'Python', 'Go', 'Rust', 'Docker', 'Test Design'],
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
                    <ul className="space-y-3">
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

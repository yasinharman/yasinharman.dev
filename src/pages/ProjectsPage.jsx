import { useState } from 'react';

/**
 * Proje görselleri docs/ klasöründen alınır.
 * Yeni bir görsel eklemek için: docs/ klasörüne dosyayı koy ve aşağıdaki
 * import yollarındaki dosya adını kendi adınla değiştir.
 */
// ⬇️ DÜZENLE: 1. proje görseli — docs/ içindeki dosya adını yaz
import project1Image from '../../docs/ETL.png';
// ⬇️ DÜZENLE: 2. proje görseli — docs/ içindeki dosya adını yaz
import project2Image from '../../docs/business.png';
// ⬇️ DÜZENLE: 3. proje görseli — docs/ içindeki dosya adını yaz
import project3Image from '../../docs/n8n-workflow.png';

/**
 * Projeler verisi.
 * Yeni bir proje eklemek için bu diziye yeni bir obje ekleyin.
 */
const PROJECTS_DATA = [
  {
    id: 1,
    // ⬇️ DÜZENLE: Proje başlığı
    title: 'Automated Scraper Bot',
    category: 'ETL System',
    image: project1Image,
    // ⬇️ DÜZENLE: Projenin GitHub repository linki
    github: 'https://github.com/yasinharman/Multiwebsite-ETL-Project',
    // ⬇️ DÜZENLE: Projeye tıklandığında gidilecek link
    link: 'http://multiwebsiteetlproject-dashboard-e6buaj-70c690-77-42-34-4.traefik.me/',
    description: '5 farklı kariyer sitesinden girilen anahtar kelime ile eşleşen iş ilanlarını bulan otomatik bir ETL yapısı ve sonuçları görselleştiren web tabanlı bir dashboard.',
    techStack: ['Python', 'SQL', 'PostgreSQL', 'Streamlit', 'Scrapy', 'Playwright', 'Docker', 'Dokploy']
  },
  {
    id: 2,
    // ⬇️ DÜZENLE: Proje başlığı
    title: 'Business Data Finder',
    category: 'Data Extraction',
    image: project2Image,
    // ⬇️ DÜZENLE: Projenin GitHub repository linki
    github: 'https://github.com/yasinharman/business-data-finder',
    // ⬇️ DÜZENLE: Projeye tıklandığında gidilecek link
    link: 'https://businessdatafinder.yasinharman.dev/',
    description: 'İstediğiniz bir bölgedeki istediğiniz bir işletme türünün verilerini kolayca bulmanızı sağlayan bir web uygulaması.',
    techStack: ['Python', 'n8n', 'OpenAI API', 'SerpAPI', 'Docker', 'Dokploy']
  },
  {
    id: 3,
    // ⬇️ DÜZENLE: Proje başlığı
    title: 'Kişisel RAG Agent',
    category: 'AI Agent',
    image: project3Image,
    // ⬇️ DÜZENLE: Projenin GitHub repository linki
    github: 'https://github.com/yasinharman/yasinharman.dev',
    // ⬇️ DÜZENLE: Projeye tıklandığında gidilecek link
    link: 'https://yasinharman.dev/',
    description: 'İşe alım uzmanlarının benim hakkımda öğrenmek istediklerini hızlı bir şekilde öğrenebilmesi adına benim hakkımdaki soruları cevaplamak üzere eğittiğim yapay zeka ajanı.',
    techStack: ['React', 'Vite', 'RAG', 'OpenAI API', 'n8n', 'Supabase', 'Docker', 'Dokploy']
  }
];

export function ProjectsPage() {
  const [expandedId, setExpandedId] = useState(null);

  const toggleExpand = (id, e) => {
    e.preventDefault();
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="w-full min-h-screen bg-transparent py-12 px-4 sm:px-6 lg:px-8 font-sans selection:bg-orange-500/30">
      <div className="max-w-6xl mx-auto relative group/container">
        <div className="absolute inset-0 bg-zinc-900/40 backdrop-blur-xl rounded-[2.5rem] border border-white/5 shadow-2xl z-0 pointer-events-none" />
        <div className="absolute -inset-px bg-gradient-to-b from-white/5 to-transparent rounded-[2.5rem] opacity-50 pointer-events-none" />

        <div className="relative z-10 py-16 px-6 md:px-12 flex flex-col items-center">
          <h1 className="text-3xl md:text-4xl font-medium tracking-tight text-zinc-100 mb-16 flex items-center gap-6 text-center">
            <span className="w-12 h-px bg-gradient-to-r from-transparent to-white/20 hidden sm:block" />
            PROJELERİM
            <span className="w-12 h-px bg-gradient-to-l from-transparent to-white/20 hidden sm:block" />
          </h1>

          <div className="w-full grid grid-cols-1 lg:grid-cols-2 gap-8 md:gap-10">
            {PROJECTS_DATA.map((project, index) => {
              const isExpanded = expandedId === project.id;

              return (
                <div
                  key={project.id}
                  className="group relative flex flex-col rounded-[2rem] overflow-hidden bg-zinc-950/60 border border-white/5 transition-all duration-500 hover:border-orange-500/30 hover:shadow-[0_0_40px_rgba(249,115,22,0.1)]"
                  style={{ animationDelay: `${index * 150}ms` }}
                >
                  <a
                    href={project.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="relative block aspect-[16/10] overflow-hidden focus:outline-none"
                  >
                    <img
                      src={project.image}
                      alt={project.title}
                      className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105 opacity-60 group-hover:opacity-90 grayscale-[50%] group-hover:grayscale-0"
                      loading="lazy"
                    />

                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/50 to-transparent opacity-90 group-hover:opacity-100 transition-opacity duration-500" />

                    <div className="absolute inset-0 p-6 md:p-8 flex flex-col justify-end">
                      <span className="text-orange-500 text-xs font-semibold tracking-widest uppercase mb-3 block opacity-80 group-hover:opacity-100 transition-opacity">
                        {project.category}
                      </span>

                      <div className="flex items-end justify-between gap-4">
                        <h3 className="text-2xl font-medium tracking-tight text-white text-balance leading-snug">
                          {project.title}
                        </h3>

                        <div className="w-10 h-10 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/10 group-hover:bg-orange-500 group-hover:border-orange-400 group-hover:text-black transition-all duration-300 shrink-0">
                          <iconify-icon icon="solar:arrow-right-up-linear" class="text-xl"></iconify-icon>
                        </div>
                      </div>
                    </div>
                  </a>

                  <div className="relative px-6 pb-6 pt-2 bg-zinc-950 flex flex-col items-center">
                    <button
                      onClick={(e) => toggleExpand(project.id, e)}
                      className="flex items-center justify-center gap-2 w-full py-2 text-sm text-zinc-400 hover:text-orange-400 transition-colors focus:outline-none"
                    >
                      <span>{isExpanded ? 'Detayları Gizle' : 'Detayları Göster'}</span>
                      <iconify-icon
                        icon="solar:alt-arrow-down-linear"
                        class={`text-lg transition-transform duration-500 ${isExpanded ? 'rotate-180' : 'rotate-0'}`}
                      ></iconify-icon>
                    </button>

                    <div
                      className={`grid transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] w-full ${isExpanded ? 'grid-rows-[1fr] opacity-100 mt-4' : 'grid-rows-[0fr] opacity-0'
                        }`}
                    >
                      <div className="overflow-hidden">
                        <div className="border-t border-white/5 pt-4">
                          <p className="text-zinc-300 text-sm md:text-base leading-relaxed mb-6 font-light">
                            {project.description}
                          </p>

                          <div>
                            <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Teknolojiler</h4>
                            <div className="flex flex-wrap gap-2">
                              {project.techStack.map((tech, i) => (
                                <span
                                  key={i}
                                  className="px-3 py-1 text-xs font-medium rounded-full bg-white/5 border border-white/10 text-zinc-300"
                                >
                                  {tech}
                                </span>
                              ))}
                            </div>
                          </div>

                          {project.github && (
                            <a
                              href={project.github}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="group/gh mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-zinc-300 hover:border-orange-500/40 hover:text-orange-400 hover:shadow-[0_0_20px_rgba(249,115,22,0.15)] transition-all duration-300"
                            >
                              <iconify-icon icon="mdi:github" class="text-lg"></iconify-icon>
                              <span className="text-xs font-medium tracking-wide">GitHub'da Görüntüle</span>
                              <iconify-icon
                                icon="solar:arrow-right-up-linear"
                                class="text-sm transition-transform duration-300 group-hover/gh:translate-x-0.5 group-hover/gh:-translate-y-0.5"
                              ></iconify-icon>
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="absolute inset-0 border-2 border-orange-500/0 group-hover:border-orange-500/20 rounded-[2rem] transition-colors duration-700 pointer-events-none" />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

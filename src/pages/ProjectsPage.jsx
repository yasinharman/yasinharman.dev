import { useState } from 'react';

/**
 * Projeler verisi.
 * Yeni bir proje eklemek için bu diziye yeni bir obje ekleyin.
 */
const PROJECTS_DATA = [
  {
    id: 1,
    // ⬇️ DÜZENLE: Proje başlığı
    title: 'Quantum Interface Engine',
    category: 'Web Application',
    // ⬇️ DÜZENLE: Proje kutusunda görünecek fotoğrafın URL'si
    image: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&q=80',
    // ⬇️ DÜZENLE: Projeye tıklandığında gidilecek link
    link: 'https://example.com',
    description: 'A highly responsive web application built with modern web technologies, focusing on delivering next-generation user interfaces for complex data ecosystems.',
    techStack: ['React', 'Tailwind CSS', 'Vite', 'Framer Motion']
  },
  {
    id: 2,
    // ⬇️ DÜZENLE: Proje başlığı
    title: 'Neural Dashboard System',
    category: 'Data Visualization',
    // ⬇️ DÜZENLE: Proje kutusunda görünecek fotoğrafın URL'si
    image: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80',
    // ⬇️ DÜZENLE: Projeye tıklandığında gidilecek link
    link: 'https://example.com',
    description: 'An analytics dashboard that processes and visualizes large-scale neural network data in real-time, featuring interactive charts and customizable widgets.',
    techStack: ['Next.js', 'Recharts', 'TypeScript', 'Node.js']
  },
  {
    id: 3,
    // ⬇️ DÜZENLE: Proje başlığı
    title: 'Crypto Void Protocol',
    category: 'Blockchain',
    // ⬇️ DÜZENLE: Proje kutusunda görünecek fotoğrafın URL'si
    image: 'https://images.unsplash.com/photo-1614729939124-032f0b56c9ce?w=800&q=80',
    // ⬇️ DÜZENLE: Projeye tıklandığında gidilecek link
    link: 'https://example.com',
    description: 'A decentralized finance protocol interface ensuring secure transactions. Includes wallet integrations and real-time smart contract monitoring.',
    techStack: ['Web3.js', 'React', 'Ethers', 'Solidity']
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
                      className={`grid transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] w-full ${
                        isExpanded ? 'grid-rows-[1fr] opacity-100 mt-4' : 'grid-rows-[0fr] opacity-0'
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

import { useLayoutEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useLanguage } from '../i18n/LanguageContext';

// Rota yolları dile göre değişmez; yalnızca etiketler çevrilir.
const NAV_ITEMS = [
  { key: 'home', path: '/', icon: 'mdi:home-outline' },
  { key: 'experience', path: '/deneyimlerim', icon: 'mdi:briefcase-outline' },
  { key: 'projects', path: '/projelerim', icon: 'mdi:folder-multiple-outline' },
];

export function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useLanguage();

  const navRef = useRef(null);
  const itemRefs = useRef([]);
  const [indicator, setIndicator] = useState({ left: 0, width: 0, ready: false });

  const activeIndex = NAV_ITEMS.findIndex(i => i.path === location.pathname);

  useLayoutEffect(() => {
    const measure = () => {
      const el = itemRefs.current[activeIndex];
      if (!el) {
        setIndicator(prev => ({ ...prev, ready: false }));
        return;
      }
      setIndicator({ left: el.offsetLeft, width: el.offsetWidth, ready: true });
    };

    measure();

    const el = itemRefs.current[activeIndex];
    if (!el) return;

    const ro = new ResizeObserver(measure);
    ro.observe(el);
    if (navRef.current) ro.observe(navRef.current);

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(measure);
    }

    window.addEventListener('resize', measure);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [activeIndex, t]);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 px-8 py-6 flex items-center justify-between pointer-events-none">
      <div className="flex items-center gap-2 pointer-events-auto">
        <button
          type="button"
          onClick={() => navigate('/')}
          aria-label={t.nav.backHome}
          className="text-xl tracking-tight text-white cursor-pointer group font-bricolage font-semibold drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)] transition-transform duration-200 ease-out hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 rounded-md"
        >
          Yasin<span className="text-orange-500 group-hover:text-orange-400 transition-colors drop-shadow-[0_0_8px_rgba(249,115,22,0.5)] font-bricolage font-semibold">.</span>Harman
        </button>
      </div>

      <nav
        ref={navRef}
        className="relative pointer-events-auto flex items-center gap-1 bg-white/5 backdrop-blur-xl border border-white/10 rounded-full px-2 py-1.5 shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
      >
        <span
          aria-hidden="true"
          className="absolute top-1/2 -translate-y-1/2 h-9 rounded-full bg-orange-500/20 border border-orange-500/30 shadow-[0_0_12px_rgba(249,115,22,0.25)] transition-[left,width,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
          style={{
            left: indicator.left,
            width: indicator.width,
            opacity: indicator.ready && activeIndex >= 0 ? 1 : 0,
          }}
        />

        {NAV_ITEMS.map((item, i) => {
          const isActive = i === activeIndex;
          return (
            <button
              key={item.path}
              ref={el => (itemRefs.current[i] = el)}
              onClick={() => navigate(item.path)}
              className={`relative z-10 flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium font-bricolage transition-colors duration-300 ${
                isActive ? 'text-orange-400' : 'text-white/85 hover:text-white'
              }`}
            >
              <iconify-icon icon={item.icon} width="18" height="18" />
              <span>{t.nav[item.key]}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
}

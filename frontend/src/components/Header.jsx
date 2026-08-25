import { useEffect, useLayoutEffect, useRef, useState } from 'react';
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

  // Dar ekranda pill menü hamburgere dönüşür; açık/kapalı durumu burada tutulur.
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Aşağı kaydırınca header gizlenir, yukarı kaydırınca geri gelir.
  const [scrolledDown, setScrolledDown] = useState(false);

  const activeIndex = NAV_ITEMS.findIndex(i => i.path === location.pathname);

  useLayoutEffect(() => {
    const measure = () => {
      const el = itemRefs.current[activeIndex];
      // Mobilde masaüstü navigasyonu gizli olduğu için genişlik 0 gelir;
      // göstergeyi ölçmeye çalışmak yerine gizli bırakıyoruz.
      if (!el || el.offsetWidth === 0) {
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

  // Aşağı kaydırınca gizle, yukarı kaydırınca göster. Okumalar rAF ile
  // sınırlanıyor; küçük hareketler (dokunmatik titremesi, lastik bant efekti)
  // eşiğin altında kaldığı için yön değiştirmiş sayılmıyor.
  useEffect(() => {
    const HIDE_AFTER = 80; // header yüksekliği kadar: en tepede her zaman görünür
    const THRESHOLD = 6;

    let lastY = Math.max(0, window.scrollY);
    let ticking = false;

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        const y = Math.max(0, window.scrollY);
        const delta = y - lastY;
        // Eşiği aşmayan hareketlerde lastY'yi güncellemiyoruz ki fark birikebilsin.
        if (Math.abs(delta) < THRESHOLD) return;
        setScrolledDown(y > HIDE_AFTER && delta > 0);
        lastY = y;
      });
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Sayfa değişince menü açık kalmasın.
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Dışarı tıklama ve Escape ile kapanma.
  useEffect(() => {
    if (!menuOpen) return;

    const onPointerDown = event => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = event => {
      if (event.key === 'Escape') setMenuOpen(false);
    };

    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen]);

  const isHidden = scrolledDown && !menuOpen;

  const go = path => {
    setMenuOpen(false);
    navigate(path);
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 px-5 py-4 md:px-8 md:py-6 flex items-center justify-between gap-3 pointer-events-none transition-transform duration-300 ease-out motion-reduce:transition-none ${
        isHidden ? '-translate-y-full' : 'translate-y-0'
      }`}
    >
      <div className="flex min-w-0 items-center gap-2 pointer-events-auto">
        <button
          type="button"
          onClick={() => go('/')}
          aria-label={t.nav.backHome}
          className="truncate text-lg md:text-xl tracking-tight text-white cursor-pointer group font-bricolage font-semibold drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)] transition-transform duration-200 ease-out hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 rounded-md"
        >
          Yasin<span className="text-orange-500 group-hover:text-orange-400 transition-colors drop-shadow-[0_0_8px_rgba(249,115,22,0.5)] font-bricolage font-semibold">.</span>Harman
        </button>
      </div>

      {/* Masaüstü: kayan göstergeli pill menü. */}
      <nav
        ref={navRef}
        className="relative pointer-events-auto hidden md:flex items-center gap-1 bg-white/5 backdrop-blur-xl border border-white/10 rounded-full px-2 py-1.5 shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
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

      {/* Mobil: hamburger düğmesi ve açılır panel. */}
      <div ref={menuRef} className="relative pointer-events-auto md:hidden">
        <button
          type="button"
          onClick={() => setMenuOpen(open => !open)}
          aria-label={menuOpen ? t.nav.closeMenu : t.nav.openMenu}
          aria-expanded={menuOpen}
          aria-controls="mobile-nav"
          className={`flex h-11 w-11 items-center justify-center rounded-full border backdrop-blur-xl shadow-[0_4px_24px_rgba(0,0,0,0.4)] transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 ${
            menuOpen
              ? 'bg-orange-500/20 border-orange-500/30 text-orange-400'
              : 'bg-white/5 border-white/10 text-white/85'
          }`}
        >
          <iconify-icon icon={menuOpen ? 'mdi:close' : 'mdi:menu'} width="22" height="22" />
        </button>

        <nav
          id="mobile-nav"
          aria-hidden={!menuOpen}
          className={`absolute right-0 top-full mt-2 w-56 origin-top-right rounded-2xl border border-white/10 bg-zinc-950/90 backdrop-blur-xl p-2 shadow-[0_8px_32px_rgba(0,0,0,0.6)] transition-[opacity,transform] duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] ${
            menuOpen ? 'opacity-100 scale-100' : 'pointer-events-none opacity-0 scale-95'
          }`}
        >
          {NAV_ITEMS.map((item, i) => {
            const isActive = i === activeIndex;
            return (
              <button
                key={item.path}
                type="button"
                onClick={() => go(item.path)}
                tabIndex={menuOpen ? 0 : -1}
                aria-current={isActive ? 'page' : undefined}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium font-bricolage text-left transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 ${
                  isActive
                    ? 'bg-orange-500/15 text-orange-400'
                    : 'text-white/85 hover:bg-white/5 hover:text-white'
                }`}
              >
                <iconify-icon icon={item.icon} width="18" height="18" />
                <span>{t.nav[item.key]}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
}

import { useNavigate, useLocation } from 'react-router-dom';

export function Header() {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { label: 'Anasayfa', path: '/', icon: 'mdi:home-outline' },
    { label: 'Projelerim', path: '/projelerim', icon: 'mdi:folder-multiple-outline' },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 px-8 py-6 flex items-center justify-between pointer-events-none">
      <div className="flex items-center gap-2 pointer-events-auto">
        <button
          type="button"
          onClick={() => navigate('/')}
          aria-label="Anasayfaya dön"
          className="text-xl tracking-tight text-white cursor-pointer group font-bricolage font-semibold drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)] transition-transform duration-200 ease-out hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 rounded-md"
        >
          Yasin<span className="text-orange-500 group-hover:text-orange-400 transition-colors drop-shadow-[0_0_8px_rgba(249,115,22,0.5)] font-bricolage font-semibold">.</span>Harman
        </button>
      </div>

      <nav className="pointer-events-auto flex items-center gap-1 bg-white/5 backdrop-blur-xl border border-white/10 rounded-full px-2 py-1.5 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
        {navItems.map(item => {
          const isActive = location.pathname === item.path;
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium font-bricolage transition-all ${
                isActive
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30 shadow-[0_0_12px_rgba(249,115,22,0.25)]'
                  : 'text-white/85 hover:bg-white/10 hover:text-white border border-transparent'
              }`}
            >
              <iconify-icon icon={item.icon} width="18" height="18" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </header>
  );
}

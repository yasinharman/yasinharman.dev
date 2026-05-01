import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export function SidePanel() {
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { label: 'Anasayfa', path: '/', icon: 'mdi:home-outline' },
    { label: 'Projelerim', path: '/projelerim', icon: 'mdi:folder-multiple-outline' },
  ];

  return (
    <>
      <button
        onClick={() => setIsOpen(v => !v)}
        aria-label={isOpen ? 'Paneli kapat' : 'Paneli aç'}
        className={`fixed top-1/2 -translate-y-1/2 z-50 w-8 h-16 flex items-center justify-center bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/10 rounded-r-lg text-white transition-all duration-300 ${
          isOpen ? 'left-64' : 'left-0'
        }`}
      >
        <iconify-icon
          icon={isOpen ? 'mdi:chevron-left' : 'mdi:chevron-right'}
          width="20"
          height="20"
        />
      </button>

      <aside
        className={`fixed top-0 left-0 h-full w-64 z-40 bg-black/60 backdrop-blur-xl border-r border-white/10 transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="pt-24 px-4 flex flex-col gap-2">
          {navItems.map(item => {
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setIsOpen(false);
                }}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors font-bricolage ${
                  isActive
                    ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                    : 'text-white/80 hover:bg-white/10 hover:text-white'
                }`}
              >
                <iconify-icon icon={item.icon} width="20" height="20" />
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            );
          })}
        </div>
      </aside>
    </>
  );
}

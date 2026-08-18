import { useLanguage } from '../i18n/LanguageContext';

const OPTIONS = ['tr', 'en'];

export function LanguageSwitch() {
  const { language, setLanguage, t } = useLanguage();
  const activeIndex = OPTIONS.indexOf(language);

  return (
    <div className="fixed bottom-6 right-6 z-50 pointer-events-auto">
      <div
        role="group"
        aria-label={t.languageSwitch.label}
        className="relative flex items-center bg-white/5 backdrop-blur-xl border border-white/10 rounded-full p-1 shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
      >
        {/* Kayan gösterge: iki seçenek eşit genişlikte olduğu için ölçüm gerekmiyor. */}
        <span
          aria-hidden="true"
          className="absolute top-1 bottom-1 left-1 w-[calc(50%-0.25rem)] rounded-full bg-orange-500/20 border border-orange-500/30 shadow-[0_0_12px_rgba(249,115,22,0.25)] transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
          style={{ transform: `translateX(${activeIndex * 100}%)` }}
        />

        {OPTIONS.map((code) => {
          const isActive = code === language;
          return (
            <button
              key={code}
              type="button"
              onClick={() => setLanguage(code)}
              aria-pressed={isActive}
              className={`relative z-10 w-14 px-3 py-1.5 rounded-full text-xs font-semibold font-bricolage tracking-wide transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 ${
                isActive ? 'text-orange-400' : 'text-white/70 hover:text-white'
              }`}
            >
              {t.languageSwitch[code]}
            </button>
          );
        })}
      </div>
    </div>
  );
}

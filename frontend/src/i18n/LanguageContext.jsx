import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { DEFAULT_LANGUAGE, LANGUAGES, translations } from './translations';

const STORAGE_KEY = 'site_lang';

const LanguageContext = createContext(null);

function readStoredLanguage() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (LANGUAGES.includes(stored)) return stored;
  } catch {
    // localStorage erişilemiyor (gizli sekme / kapalı çerezler): varsayılana düş.
  }
  return DEFAULT_LANGUAGE;
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(readStoredLanguage);

  const setLanguage = useCallback((next) => {
    if (!LANGUAGES.includes(next)) return;
    setLanguageState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Kalıcı kaydedemesek de oturum içinde dil değişmeli.
    }
  }, []);

  // <html lang> ve sekme başlığı da dile uymalı: ekran okuyucular ve SEO bunu okur.
  useEffect(() => {
    document.documentElement.lang = language;
    document.title = translations[language].documentTitle;
  }, [language]);

  const value = useMemo(
    () => ({ language, setLanguage, t: translations[language] }),
    [language, setLanguage],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within a LanguageProvider');
  return ctx;
}

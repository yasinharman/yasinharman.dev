import { useState } from 'react';
import { useTypewriter } from '../hooks/useTypewriter';

const PLACEHOLDER_QUESTIONS = [
  "Yasin '...' rolünde görev alabilir mi?",
  "Yasin'in iletişim bilgileri neler?",
  "Yasin'in projelerinden bahsetebilir misin?",
  "Yasin'in kullanabildiği teknolojiler neler?",
  "Yasin hangi sosyal etkinliklere katıldı?",
  ]

export function Hero({ onSearchSubmit }) {
  const [inputValue, setInputValue] = useState('');
  const placeholderText = useTypewriter(PLACEHOLDER_QUESTIONS);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSearchSubmit(inputValue.trim());
    }
  };

  return (
    <section className="min-h-screen flex flex-col animate-fade-in pt-20 pr-4 pl-4 relative items-center justify-center">

      {/* Ambient Glow Background - Increased Orange Intensity */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-orange-500/20 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative z-10 w-full max-w-3xl flex flex-col items-center text-center">

        <h1 className="text-5xl md:text-6xl tracking-tight text-transparent bg-clip-text bg-gradient-to-br from-white via-zinc-200 to-zinc-500 mb-6 font-bricolage font-semibold">
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-orange-500 to-amber-400 drop-shadow-[0_0_15px_rgba(249,115,22,0.3)] font-bricolage font-semibold">Yasin</span> hakkında ne bilmek istersiniz?
        </h1>

        <p className="text-lg text-zinc-400 mb-12 max-w-xl font-light font-sans">
          Merhaba, ben Jarvis! Yasin hakkındaki soruları yanıtlamak için eğitildim.
        </p>

        {/* Search / Input Box */}
        <form
          onSubmit={handleSubmit}
          className="w-full relative group animate-slide-up"
          style={{ animationDelay: '0.1s' }}
        >
          {/* Warmer orange glow behind the input */}
          <div className="absolute -inset-0.5 bg-gradient-to-r from-orange-900/40 to-zinc-700 rounded-full blur opacity-40 group-hover:opacity-70 group-hover:from-orange-600/40 transition duration-500 group-hover:duration-200"></div>
          <div className="relative flex items-center bg-zinc-900 border border-zinc-800 rounded-full p-2 shadow-2xl transition-all duration-300 focus-within:border-orange-500/50 focus-within:ring-1 focus-within:ring-orange-500/50 focus-within:shadow-[0_0_40px_rgba(249,115,22,0.2)]">

            <div className="pl-4 pr-2 text-zinc-500 flex items-center justify-center">
              <iconify-icon icon="solar:magnifer-linear" width="22" height="22"></iconify-icon>
            </div>

            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={placeholderText}
              className="flex-1 bg-transparent border-none outline-none text-zinc-100 placeholder:text-zinc-600 text-lg py-3 px-2 w-full"
              autoComplete="off"
            />

            <button
              type="submit"
              disabled={!inputValue.trim()}
              className="ml-2 bg-orange-600 hover:bg-orange-500 text-white p-3 rounded-full flex items-center justify-center transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-orange-600 shadow-[0_0_20px_rgba(249,115,22,0.4)] hover:shadow-[0_0_30px_rgba(249,115,22,0.7)] hover:scale-105 active:scale-95"
            >
              <iconify-icon icon="solar:arrow-right-linear" width="22" height="22"></iconify-icon>
            </button>
          </div>
        </form>

      </div>
    </section>
  );
}
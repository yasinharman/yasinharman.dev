import { useState, useRef, useEffect } from 'react';
import { Hero } from '../components/Hero';
import { ChatInterface } from '../components/ChatInterface';
import { useLanguage } from '../i18n/LanguageContext';

// n8n doneminden kalan WEBHOOK_URL adlandirmasi kaldirildi; backend artik kendi
// FastAPI servisimiz ve sabit bir sozlesme donuyor.
const API_URL = import.meta.env.VITE_API_URL;

// 429'un ayri bir hata tipi olmasinin sebebi: genel hata mesaji "lutfen tekrar
// deneyin" diyor ve rate limit'te bu TAM TERSI tavsiye — hemen tekrar denemek
// pencereyi uzatiyor. Sunucu Retry-After gonderiyor, onu kullaniciya soyluyoruz.
class HizSiniri extends Error {
  constructor(response) {
    super('HTTP 429');
    this.name = 'HizSiniri';
    const bekle = parseInt(response.headers.get('Retry-After') || '', 10);
    this.saniye = Number.isFinite(bekle) && bekle > 0 ? bekle : 60;
  }
}
// VITE_API_URL zaten .../chat'e isaret ediyor; ayri bir ortam degiskeni eklemek
// yerine yol uzatiliyor, boylece Coolify tarafinda yapilacak bir sey yok.
const STREAM_URL = API_URL ? `${API_URL.replace(/\/+$/, '')}/stream` : null;

function getOrCreateSessionId() {
  const KEY = 'chat_session_id';
  let id = sessionStorage.getItem(KEY);
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) ||
      `s-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem(KEY, id);
  }
  return id;
}

export function HomePage() {
  const [messages, setMessages] = useState([]);
  const [isChatActive, setIsChatActive] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  // Hangi asamadayiz: cevabin ilk token'i 3-7 saniyede geliyor (olculdu) ve o
  // sureye kadar ekran bombosdu. Asama etiketi o bosluğu dolduruyor.
  const [stage, setStage] = useState(null);
  const { language, t } = useLanguage();

  const chatSectionRef = useRef(null);
  const sessionIdRef = useRef(getOrCreateSessionId());

  const handleSendMessage = async (messageText) => {
    // ADIM 2: Optimistic update — kullanıcı mesajını anında listeye ekle, "yazıyor" göstergesini aç, ilk mesajsa chat panelini mount et.
    const newUserMsg = { id: `${Date.now()}-user`, role: 'user', content: messageText };
    setMessages(prev => [...prev, newUserMsg]);
    setIsTyping(true);

    if (!isChatActive) setIsChatActive(true);

    const aiId = `${Date.now()}-ai`;

    // Token geldikce ayni mesaja ekle; "bitti" olayinda TAM cevapla degistir.
    // Degistirme sart: output_guard cevabi sabit bir metinle degistirmis olabilir
    // (sizinti/uzunluk) ve o durumda ekranda kalan akmis metin gecersizdir.
    //
    // Balonun var olup olmadigi listeden okunuyor, disarida tutulan bir bayraktan
    // degil: React guncelleyiciyi sonra calistiriyor ve bayrak o ana kadar zaten
    // true olmus oluyordu — ilk token hicbir zaman ekrana gelmezdi.
    const yaz = (icerik, degistir) => {
      setMessages(prev => (
        prev.some(m => m.id === aiId)
          ? prev.map(m => m.id === aiId
              ? { ...m, content: degistir ? icerik : m.content + icerik }
              : m)
          : [...prev, { id: aiId, role: 'ai', content: icerik }]
      ));
    };

    const govde = JSON.stringify({
      message: messageText,
      session_id: sessionIdRef.current,
      // lang -> backend cevabi bu dilde yazar; bilgi tabani sorgusu her zaman Turkce kalir.
      lang: language,
    });

    try {
      if (!API_URL) throw new Error('VITE_API_URL is not defined');

      const response = await fetch(STREAM_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: govde,
      });

      // Frontend ve backend ayri ayri deploy oluyor; kisa bir pencerede yeni
      // arayuz eski backend'e denk gelebilir. O durumda akissiz yola dus.
      if (response.status === 404 || response.status === 405) {
        const d = await fetch(API_URL, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: govde,
        });
        if (d.status === 429) throw new HizSiniri(d);
        if (!d.ok) throw new Error(`HTTP ${d.status}`);
        yaz((await d.json()).response ?? '', true);
        return;
      }
      if (response.status === 429) throw new HizSiniri(response);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const isle = (parca) => {
        const satir = parca.trim();
        if (!satir.startsWith('data: ')) return;
        const olay = JSON.parse(satir.slice(6));
        if (olay.tip === 'asama') {
          setStage(olay);
        } else if (olay.tip === 'token') {
          setStage(null);
          yaz(olay.metin, false);
        } else if (olay.tip === 'bitti') {
          setStage(null);
          yaz(olay.cevap, true);
        }
      };

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let tampon = '';

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        tampon += decoder.decode(value, { stream: true });
        // SSE olaylari bos satirla ayrilir; son parca yarim kalmis olabilir,
        // onu bir sonraki okumaya devrediyoruz.
        const parcalar = tampon.split('\n\n');
        tampon = parcalar.pop();
        parcalar.forEach(isle);
      }
      // Akis sonlanirken tamponda kalan olay olabilir; birakilirsa kaybolan sey
      // "bitti" olur, yani tam cevap.
      if (tampon.trim()) isle(tampon);
    } catch (error) {
      // Ham error.message ekrana basiliyordu ("Webhook HTTP 500" gibi). Kullaniciya
      // sabit metin, gelistiriciye console: hata detayi arayuzde ise yaramiyor.
      console.error('[chat] request failed:', error);
      const metin = error instanceof HizSiniri
        ? t.chat.rateLimitMessage.replace('{n}', error.saniye)
        : t.chat.errorMessage;
      setMessages(prev => [...prev, { id: `${Date.now()}-err`, role: 'ai', content: metin }]);
    } finally {
      setIsTyping(false);
      setStage(null);
    }
  };

  useEffect(() => {
    if (isChatActive && chatSectionRef.current) {
      const timer = setTimeout(() => chatSectionRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
      return () => clearTimeout(timer);
    }
  }, [isChatActive]);

  return (
    <main className="flex-1 flex flex-col">
      <Hero onSearchSubmit={handleSendMessage} />
      {isChatActive && (
        <div ref={chatSectionRef} className="w-full">
          <ChatInterface
            messages={messages}
            isTyping={isTyping}
            stage={stage}
            onSendMessage={handleSendMessage}
          />
        </div>
      )}
    </main>
  );
}

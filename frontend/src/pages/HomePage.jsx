import { useState, useRef, useEffect } from 'react';
import { Hero } from '../components/Hero';
import { ChatInterface } from '../components/ChatInterface';
import { useLanguage } from '../i18n/LanguageContext';

const WEBHOOK_URL = import.meta.env.VITE_API_URL;

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
  const { language, t } = useLanguage();

  const chatSectionRef = useRef(null);
  const sessionIdRef = useRef(getOrCreateSessionId());

  const handleSendMessage = async (messageText) => {
    // ADIM 2: Optimistic update — kullanıcı mesajını anında listeye ekle, "yazıyor" göstergesini aç, ilk mesajsa chat panelini mount et.
    const newUserMsg = { id: `${Date.now()}-user`, role: 'user', content: messageText };
    setMessages(prev => [...prev, newUserMsg]);
    setIsTyping(true);

    if (!isChatActive) setIsChatActive(true);

    try {
      // ADIM 3: Mesajı ve oturum kimliğini JSON body olarak webhook'a POST et; HTTP hata kodlarını manuel olarak yakala.
      if (!WEBHOOK_URL) throw new Error('VITE_N8N_WEBHOOK_URL is not defined');
      const response = await fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // lang -> backend cevabi bu dilde yazar; bilgi tabanı sorgusu her zaman Türkçe kalır.
        body: JSON.stringify({ message: messageText, session_id: sessionIdRef.current, lang: language }),
      });
      if (!response.ok) throw new Error(`Webhook HTTP ${response.status}`);

      const raw = await response.text();
      let parsed;
      try { parsed = JSON.parse(raw); } catch { parsed = raw; }

      const node = Array.isArray(parsed) ? parsed[0] : parsed;
      const rawAiText =
        typeof node === 'string'
          ? node
          : node?.response ?? node?.output ?? node?.text ?? node?.message ?? node?.reply ?? node?.answer ?? JSON.stringify(node);

      const aiText = String(rawAiText)
        .replace(/\\r\\n/g, '\n')
        .replace(/\\n/g, '\n')
        .replace(/\\t/g, '\t');

      setMessages(prev => [...prev, { id: `${Date.now()}-ai`, role: 'ai', content: aiText }]);
    } catch (error) {
      // Ham error.message ekrana basiliyordu ("Webhook HTTP 500" gibi). Kullaniciya
      // sabit metin, gelistiriciye console: hata detayi arayuzde ise yaramiyor.
      console.error('[chat] request failed:', error);
      setMessages(prev => [...prev, { id: `${Date.now()}-err`, role: 'ai', content: t.chat.errorMessage }]);
    } finally {
      setIsTyping(false);
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
            onSendMessage={handleSendMessage}
          />
        </div>
      )}
    </main>
  );
}

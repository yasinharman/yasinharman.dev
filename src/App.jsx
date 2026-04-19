import { useState, useRef, useEffect, lazy, Suspense } from 'react';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { ChatInterface } from './components/ChatInterface';
import { useIsLowPowerDevice } from './hooks/useIsLowPowerDevice';

const UnicornScene = lazy(() => import('unicornstudio-react'));

function StaticAuraBackground() {
  return (
    <div
      className="absolute inset-0 w-full h-full"
      style={{
        background:
          'radial-gradient(ellipse 80% 60% at 50% 40%, rgba(249,115,22,0.18) 0%, rgba(180,60,10,0.10) 35%, rgba(10,8,15,0) 70%), radial-gradient(ellipse 60% 50% at 70% 60%, rgba(120,40,200,0.10) 0%, rgba(10,8,15,0) 70%), #0a080f',
      }}
    />
  );
}

const WEBHOOK_URL = import.meta.env.VITE_N8N_WEBHOOK_URL;

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isChatActive, setIsChatActive] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const isLowPower = useIsLowPowerDevice();

  const chatSectionRef = useRef(null);

  const handleSendMessage = async (messageText) => {
    const newUserMsg = { role: 'user', content: messageText };
    setMessages(prev => [...prev, newUserMsg]);
    setIsTyping(true);

    if (!isChatActive) setIsChatActive(true);

    try {
      if (!WEBHOOK_URL) throw new Error('VITE_N8N_WEBHOOK_URL is not defined');
      const response = await fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }),
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

      setMessages(prev => [...prev, { role: 'ai', content: aiText }]);
    } catch (error) {
      console.error('[chat] webhook error:', error);
      setMessages(prev => [...prev, { role: 'ai', content: `Hata: ${error.message}` }]);
    } finally {
      setIsTyping(false);
    }
  };

  useEffect(() => {
    if (isChatActive && chatSectionRef.current) {
      setTimeout(() => chatSectionRef.current.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }, [isChatActive]);

  return (
    <div className="min-h-screen flex flex-col relative overflow-x-hidden">
      {/* Aura Background Layers */}
      <div
        className="aura-background-component fixed top-0 w-full h-screen -z-10 hue-rotate-180 invert-0 brightness-50"
        style={{
          maskImage: "linear-gradient(to bottom, transparent, black 0%, black 80%, transparent)",
          WebkitMaskImage: "linear-gradient(to bottom, transparent, black 0%, black 80%, transparent)",
        }}
      >
        {isLowPower ? (
          <StaticAuraBackground />
        ) : (
          <Suspense fallback={<StaticAuraBackground />}>
            <UnicornScene projectId="UtvhDctN8AjL6tvf1yKd" className="w-full h-full" />
          </Suspense>
        )}
      </div>

      <Header />

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
    </div>
  );
}
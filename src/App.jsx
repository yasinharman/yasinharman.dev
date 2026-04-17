import { useState, useRef, useEffect } from 'react';
import UnicornScene from 'unicornstudio-react';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { ChatInterface } from './components/ChatInterface';

const WEBHOOK_URL = import.meta.env.VITE_N8N_WEBHOOK_URL;

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isChatActive, setIsChatActive] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

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
      const data = await response.json();
      setMessages(prev => [...prev, { role: 'ai', content: data.response || data.text }]);
    } catch (error) {
      setTimeout(() => {
        setMessages(prev => [...prev, { role: 'ai', content: `Simulated response to: "${messageText}"` }]);
        setIsTyping(false);
      }, 1500);
      return;
    }
    setIsTyping(false);
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
        <UnicornScene projectId="UtvhDctN8AjL6tvf1yKd" className="w-full h-full" />
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
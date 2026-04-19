import { useEffect, useRef, useState } from 'react';

export function ChatInterface({ messages, isTyping, onSendMessage }) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Scroll to bottom whenever messages change or typing state changes
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !isTyping) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <section className="min-h-screen flex flex-col items-center justify-center px-4 py-24 relative">
      <div className="w-full max-w-4xl h-[80vh] flex flex-col bg-zinc-900/40 backdrop-blur-md border border-zinc-800/60 rounded-3xl overflow-hidden shadow-2xl relative z-10">
        
        {/* Chat Header */}
        <div className="px-6 py-4 border-b border-orange-500/20 bg-zinc-900/50 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center text-orange-500 relative">
            <div className="absolute inset-0 rounded-full border border-orange-500/40 animate-pulse-slow"></div>
            <iconify-icon icon="solar:cpu-bold-duotone" width="24" height="24"></iconify-icon>
          </div>
          <div>
            <h3 className="font-medium text-zinc-100">Jarvis</h3>
            <p className="text-xs text-zinc-400">YasinHarman için Yapay Zeka Asistanı</p>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto chat-scroll p-6 space-y-6">
          {messages.map((msg, idx) => (
            <div 
              key={idx} 
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
            >
              <div
                className={`max-w-[80%] md:max-w-[70%] rounded-2xl px-5 py-3.5 text-[15px] leading-relaxed whitespace-pre-wrap break-words ${
                  msg.role === 'user'
                    ? 'bg-zinc-800 text-zinc-100 rounded-tr-sm border border-zinc-700/50'
                    : 'bg-orange-500/15 text-orange-50 border border-orange-500/30 shadow-[0_0_20px_rgba(249,115,22,0.08)] rounded-tl-sm'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          
          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex justify-start animate-fade-in">
              <div className="bg-orange-500/10 border border-orange-500/20 rounded-2xl rounded-tl-sm px-5 py-4 flex gap-1.5 items-center h-[52px]">
                <div className="w-2 h-2 rounded-full bg-orange-500/70 typing-dot"></div>
                <div className="w-2 h-2 rounded-full bg-orange-500/70 typing-dot"></div>
                <div className="w-2 h-2 rounded-full bg-orange-500/70 typing-dot"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} className="h-4" />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-zinc-900/80 border-t border-orange-500/20 backdrop-blur-sm">
          <form 
            onSubmit={handleSubmit}
            className="relative flex items-center bg-zinc-950/50 border border-zinc-800 rounded-2xl focus-within:border-orange-500/50 focus-within:ring-1 focus-within:ring-orange-500/50 transition-all"
          >
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Başka bir soru sorun..."
              className="flex-1 bg-transparent border-none outline-none py-4 pl-5 pr-14 text-zinc-100 placeholder:text-zinc-500"
              disabled={isTyping}
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isTyping}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 rounded-xl bg-orange-600/20 text-orange-500 hover:text-white hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              <iconify-icon icon="solar:plain-bold" width="20" height="20" rotate="90deg"></iconify-icon>
            </button>
          </form>
          <div className="text-center mt-3">
            <span className="text-[10px] text-zinc-600 uppercase tracking-widest font-medium">Jarvis, bilgiyi sentezlemek için n8n kullanır</span>
          </div>
        </div>

      </div>
    </section>
  );
}
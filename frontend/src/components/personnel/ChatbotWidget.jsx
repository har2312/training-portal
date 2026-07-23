import { useState, useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../../api/client";

// Floating assistant for the personnel dashboard. Bottom-right, government
// slate/blue palette. All answers are DB-backed (server-side), never invented.
const GREETING = {
  from: "bot",
  text: "Hi! I'm your Training Assistant. Ask me about your workshops, schedule, or policies.",
  suggestions: [
    "Where is my next workshop?",
    "Any pending invitations?",
    "How many trainings have I completed?",
    "Am I eligible for travel allowance?",
  ],
};

function Bubble({ from, text }) {
  const isUser = from === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm whitespace-pre-line ${
          isUser
            ? "bg-blue-900 text-white rounded-br-sm"
            : "bg-slate-100 text-slate-800 rounded-bl-sm"
        }`}
      >
        {text}
      </div>
    </div>
  );
}

function Typing() {
  return (
    <div className="flex justify-start">
      <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-3 py-2.5 flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}

export default function ChatbotWidget({ personnelId }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, typing, open]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || typing) return;
    setInput("");
    setMessages((m) => [...m, { from: "user", text: q }]);
    setTyping(true);
    try {
      const res = await api.chat(personnelId, q);
      setMessages((m) => [...m, { from: "bot", text: res.reply, suggestions: res.suggestions }]);
    } catch (e) {
      setMessages((m) => [...m, { from: "bot", text: "Sorry, I couldn't reach the server. Please try again." }]);
    } finally {
      setTyping(false);
    }
  }

  const lastSuggestions = messages[messages.length - 1]?.suggestions || [];

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.96 }}
            transition={{ duration: 0.18 }}
            className="mb-3 w-80 sm:w-96 h-[30rem] bg-white rounded-xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="bg-blue-900 text-white px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-blue-800 flex items-center justify-center text-sm">🎓</span>
                <div>
                  <p className="text-sm font-semibold leading-tight">Training Assistant</p>
                  <p className="text-[11px] text-blue-200 leading-tight">Prasar Bharati · NABM</p>
                </div>
              </div>
              <button onClick={() => setOpen(false)} className="text-blue-200 hover:text-white text-lg leading-none">×</button>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-2 bg-slate-50">
              {messages.map((m, i) => <Bubble key={i} from={m.from} text={m.text} />)}
              {typing && <Typing />}
            </div>

            {/* Suggestion chips */}
            {lastSuggestions.length > 0 && !typing && (
              <div className="px-3 pb-2 flex flex-wrap gap-1.5 bg-slate-50">
                {lastSuggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-xs px-2.5 py-1 rounded-full bg-white border border-slate-300 text-slate-600 hover:bg-blue-50 hover:border-blue-300"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <form
              onSubmit={(e) => { e.preventDefault(); send(); }}
              className="border-t border-slate-200 p-2 flex gap-2 bg-white"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your trainings…"
                className="flex-1 text-sm px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
              <button
                type="submit"
                disabled={typing || !input.trim()}
                className="px-3 py-2 rounded-lg bg-blue-900 text-white text-sm font-medium hover:bg-blue-800 disabled:opacity-40"
              >
                Send
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Launcher */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="ml-auto flex items-center justify-center w-14 h-14 rounded-full bg-blue-900 text-white shadow-lg hover:bg-blue-800 transition"
        aria-label="Open training assistant"
      >
        <span className="text-2xl">{open ? "×" : "💬"}</span>
      </button>
    </div>
  );
}

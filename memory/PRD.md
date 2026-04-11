# x-69 Wormdemon - PRD

## Problem Statement
Full-stack AI chat projesi (FastAPI + React). Kullanici GitHub reposundan (LenstedReal/Wormdemon) gelen kodu duzeltmek, Vercel deploy uyumlu hale getirmek ve AI karakter davranisini ayarlamak istiyor.

## Architecture
- **Frontend:** React (CRA + Craco), Tailwind CSS, Axios
- **Backend (Local/Termux):** FastAPI + Motor (MongoDB) + Groq API + SerpAPI
- **Backend (Vercel):** api/index.py (serverless function), ayni logic
- **Database:** MongoDB Atlas
- **AI:** Groq API (llama-3.3-70b-versatile)
- **Intel:** Discord webhook + Telegram bot (client-side)
- **Deployment:** Vercel (frontend + serverless) + Termux (local via Cloudflare tunnel)

## Completed
- [x] GitHub repo analizi ve hata tespiti (AIChat.js send yok, server.py chat yok)
- [x] Backend: Groq API entegrasyonu, SerpAPI web arama, session management, rate limiting
- [x] Frontend: Mesaj gonderme, 18+ uyari, temizle butonu, istihbarat toplama (Discord+Telegram)
- [x] 3 modu tek modda birlestirme (x-69 unified mode)
- [x] AI karakter: Laubali ama kontrollü - kufur baglama gore, konum bilgisi ifsa yok
- [x] Vercel deploy dosyalari: vercel.json, .node-version, .npmrc
- [x] Emojiler duzgun render
- [x] "Emrinizdeyim..." placeholder
- [x] Emergent ibaresi kaldirildi

## Pending
- [ ] Kullanicinin GitHub'a push yapip Vercel deploy dogrulamasi
- [ ] Vercel Environment Variables eklenmesi (GROQ_API_KEY, SERPAPI_KEY, MONGO_URL, DB_NAME)

## Key Files
- `/app/backend/server.py` - Local/Termux backend
- `/app/api/index.py` - Vercel serverless backend
- `/app/frontend/src/AIChat.js` - Chat UI
- `/app/frontend/src/App.css` - Stiller
- `/app/vercel.json` - Vercel config
- `/app/.node-version` - Node 18
- `/app/frontend/.npmrc` - legacy-peer-deps

## Vercel Deploy Instructions
1. Root Directory: `.` (kok)
2. Framework Preset: `Other`
3. Build/Install/Output: bos birak (vercel.json hallediyor)
4. Env vars: NODE_VERSION=18, GROQ_API_KEY, SERPAPI_KEY, MONGO_URL, DB_NAME

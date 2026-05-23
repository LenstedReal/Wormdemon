# x-69 Wormdemon

Bağımsız, açık kaynak, sansürsüz AI chat — Enes (LenstedReal) ve 2 arkadaşı tarafından geliştirilmiştir.

## Stack
- **Frontend:** React 19 + Craco
- **Backend:** FastAPI (Vercel serverless `api/index.py` + lokal `backend/server.py`)
- **DB:** MongoDB Atlas
- **AI:** Groq (llama-3.3-70b) + Gemini (2.5-flash fallback)
- **Web:** SerpAPI
- **Deploy:** Vercel

## Setup

### Backend (lokal)
```bash
pip install -r backend/requirements.txt
cd backend && uvicorn server:app --reload --port 8001
```

### Frontend (lokal)
```bash
cd frontend && yarn install && yarn start
```

### Vercel ENV Variables
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `SERPAPI_KEY`
- `MONGO_URL`
- `DB_NAME`
- `DISCORD_WEBHOOK_URL` (opsiyonel)
- `TELEGRAM_BOT_TOKEN` (opsiyonel)
- `TELEGRAM_CHAT_ID` (opsiyonel)
- `NODE_VERSION=18`

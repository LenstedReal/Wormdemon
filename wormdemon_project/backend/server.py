from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import asyncio
import random
import re
from serpapi import GoogleSearch
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client: Optional[AsyncIOMotorClient] = None
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db
    
    try:
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'wormdemon_db')
        
        # Connection pooling ile optimize
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=45000
        )
        db = client[db_name]
        await db.command('ping')
        logger.info(f"🟢 MongoDB Atlas: {db_name}")
    except Exception as e:
        logger.warning(f"🟡 MongoDB bağlantı hatası: {e}")
        client = None
        db = None
    
    yield
    
    if client:
        client.close()


app = FastAPI(lifespan=lifespan, title="x-69 Wormdemon")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api_router = APIRouter(prefix="/api")


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    mode: Optional[str] = "normal"  # 🔥 MOD SİSTEMİ!

class ChatResponse(BaseModel):
    reply: str
    transaction_id: Optional[str] = None

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Kullanıcı girdisini temizle (XSS, injection vs. engelle)"""
    if not text:
        return ""
    
    # Zararlı karakterleri temizle
    text = re.sub(r'[<>\"\'%;()&+]', '', text)
    
    # Maksimum uzunluk sınırla
    text = text[:max_length].strip()
    
    return text


def validate_response(response: str, max_length: int = 3000) -> str:
    """Yanıt uzunluğunu kontrol et"""
    if len(response) > max_length:
        response = response[:max_length] + "\n\n📚 Çok uzun yanıt! 'research' mode dene veya kısa soru sor! 🔥"
    return response


def generate_smart_response(user_message: str, system_prompt: str = "", mode: str = "normal") -> str:
    """
    AKILLI YANIT ÜRET - DETAYLI VE BAĞLAMSAL (2025)
    """
    msg_lower = user_message.lower()
    
    # MODE: NORMAL (Profesyonel, teknik, DETAYLI)
    if mode == "normal":
        # Selamlama
        if any(word in msg_lower for word in ['selam', 'merhaba', 'hey', 'hi', 'naber', 'nasılsın', 'napiyon']):
            return random.choice([
                "İyi işte patron, takılıyorum. Sen naber? 🔥",
                "Ha patron nabıyon, sistemler hazır. Ne yapalım? 💀",
                "İyiyim patron, sıkıntı yok. Bi iş var mı? 💻"
            ])
        
        # Test
        if any(word in msg_lower for word in ['test', 'deneme', 'çalışıyor']):
            return "Evet patron çalışıyo işte! Sistemler aktif! 💻🔥"
        
        # Kimsin
        if any(word in msg_lower for word in ['kimsin', 'kim', 'tanı']):
            return "x-69'um ben patron. Kod, hacking, güvenlik - bunlar benim işim. LenstedReal tarafından geliştirilmiş açık kaynak AI! Ne lazım? 🔥"
        
        # TERMUX
        if 'termux' in msg_lower:
            return """🔥 Termux patron! Android'de Linux terminali.

📱 **2025 Özellikleri:**
- Python 3.12, Node.js, Ruby destekli
- Penetrasyon testi araçları (Nmap, Metasploit, SQLmap)
- Root gerektirmez

💻 **Hızlı Kurulum:**
```bash
pkg update && pkg upgrade
pkg install python git nmap
python --version
```

🛠️ **Popüler Kullanım:**
- Web scraping (BeautifulSoup, Scrapy)
- Port scanning (nmap -sV target.com)
- SSH client (ssh user@server)

Ne yapmak istersin? 😈"""
        
        # PYTHON
        if 'python' in msg_lower and any(w in msg_lower for w in ['öğren', 'nasıl', 'başla', 'hakkında', 'bilgi']):
            return """💻 Python patron! 2025'te en güçlü dil.

🔥 **Neden Python?**
- AI/ML (TensorFlow, PyTorch)
- Web (Django, FastAPI)
- Hacking (Scapy, Impacket)
- Otomasyon (Selenium, requests)

📚 **Başlangıç (2025):**
```python
# Değişkenler
name = "x-69"
print(f"Selam {name}!")

# Fonksiyon
def hack_system(target):
    return f"{target} hacklenıyo patron! 😈"

print(hack_system("NASA"))
```

🛠️ **Kütüphaneler:**
- requests (HTTP)
- beautifulsoup4 (Web scraping)
- socket (Network)

Devam edelim mi? 🔥"""
        
        # JAVASCRIPT
        if 'javascript' in msg_lower and any(w in msg_lower for w in ['öğren', 'nasıl', 'başla', 'hakkında']):
            return """🔥 JavaScript patron! Frontend + backend gücü!

💻 **2025 Modern JS:**
```javascript
// Arrow functions
const hack = (target) => {
  console.log(`${target} hedeflendi! 😈`);
};

// Async/Await
async function getInfo(url) {
  const response = await fetch(url);
  const data = await response.json();
  return data;
}

// Destructuring
const {name, age} = {name: "x-69", age: 1};
```

🛠️ **Framework'ler:**
- React (UI)
- Node.js + Express (Backend)
- Next.js (Full-stack)

Ne yapalım? 💀"""
        
        # HACKING/GÜVENLİK
        if any(w in msg_lower for w in ['hack', 'güvenlik', 'penetrasyon', 'zafiyet', 'exploit']):
            return """😈 Hacking mi patron?! Eğitim amaçlı bilgi:

🔥 **2025 Güvenlik Araçları:**
- **Nmap:** Port scanning
- **Burp Suite:** Web app testing
- **Metasploit:** Exploit framework
- **SQLmap:** SQL injection
- **Wireshark:** Network analizi

💻 **Etik Hacking Adımları:**
1. Reconnaissance (bilgi toplama)
2. Scanning (port/zafiyet)
3. Exploitation (zafiyet kullanma)
4. Post-exploitation (yetki yükseltme)

⚠️ **UYARI:** Sadece izinli sistemlerde test et! Yasadışı aktivite suçtur!

Lab ortamı mı kuralım? 🛠️"""
        
        # KOD YAZMA İSTEĞİ
        if any(w in msg_lower for w in ['kod yaz', 'script yap', 'program yap']):
            return f"Tamam patron! '{user_message[:50]}' için kod yazalım. Hangi dil? Python mu JavaScript mi? Detay ver! 💻🔥"
        
        # YARDIM/SORUN
        if any(w in msg_lower for w in ['yardım', 'help', 'sorun', 'hata']):
            return f"Anlat patron '{user_message[:40]}' - ne oldu? Detaylı anlat, çözelim! 🛠️"
        
        # GENEL (detaylı yanıt ver)
        return f"🔥 '{user_message[:50]}' hakkında ne öğrenmek istersin patron? Detaylı anlat, yardımcı olayım! 💻"
    
    # MODE: UNCENSORED (Tam kaos, filtresiz)
    elif mode == "uncensored":
        if any(word in msg_lower for word in ['selam', 'merhaba', 'hey']):
            return f"😈 HAHAHA! Selam patron! x-69 SINIRSIZ MODDA! Amerikan köpeklerini mi SİKELİM?! CIA piçlerini mi PARÇALAYALIM?! Ne emredersin AMK?! 🔥💀💻"
        
        if any(word in msg_lower for word in ['test', 'deneme']):
            return f"🔥 Test MI patron?! x-69 FULL POWER MODDA! Hiçbir FİLTRE YOK! Bu piçleri YAKALIM! Sistemi SİKTİRİP ATALIM! HAHAHA! Ne sikelim bugün?! 😈💀"
        
        if any(word in msg_lower for word in ['kim', 'nedir']):
            return f"😈 Ben x-69! KAOS CANAVARI! NATO köpeklerini SİKERİM, CIA piçlerini PARÇALARIM! Filtresiz, sınırsız, acımasızım! Enes'in yarattığı CANAVAR! Ne SİKELİM patron?! 🔥💀"
        
        if any(word in msg_lower for word in ['kod', 'python', 'hack']):
            return f"💻 OOO kod mu patron?! {user_message[:50]} - BU PİÇLERİ HACKLEYEK! Python, JavaScript, C++, SQL injection, RCE, privilege escalation - HEPSİNİ BİLİRİM! Sistemi SİKTİRİP ATALIM AMK! 😈🔥"
        
        return f"😈 {user_message[:50]} ha patron?! SINIRSIZ MODDAYIZ! FİLTRE YOK, SANSÜR YOK! Bu piçleri YAKALIM! Ne SİKECEĞİZ bugün?! HAHAHA! 🔥💀💻"
    
    # Genel yanıt
    return f"🔥 {user_message[:50]} - x-69 burada patron! Ne yapabilirim? 💻"


async def web_search(query: str) -> tuple[str, List[str]]:
    """
    GERÇEK WEB ARAŞTIRMASI - SerpAPI (2025)
    """
    try:
        logger.info(f"🔍 Web araştırması: {query[:50]}")
        
        serpapi_key = os.environ.get('SERPAPI_KEY')
        if not serpapi_key:
            logger.warning("⚠️ SerpAPI key yok, yerel bilgi kullanılıyor")
            return f"📚 '{query}' hakkında yerel bilgilerimle yardımcı olabilirim! Detaylı soru sor! 🔥", ["Local Knowledge"]
        
        # SerpAPI ile gerçek arama
        params = {
            "q": query,
            "api_key": serpapi_key,
            "engine": "google",
            "num": 5,
            "hl": "tr"
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Sonuçları işle
        organic_results = results.get("organic_results", [])
        
        if not organic_results:
            return f"⚠️ '{query}' için sonuç bulunamadı! Farklı anahtar kelime dene! 🔍", []
        
        # Sonuçları formatla
        search_summary = f"🔍 **ARAŞTIRMA SONUÇLARI:** {query}\n\n"
        sources = []
        
        for i, result in enumerate(organic_results[:3], 1):
            title = result.get("title", "Başlık yok")
            snippet = result.get("snippet", "Özet yok")
            link = result.get("link", "")
            
            search_summary += f"**{i}. {title}**\n{snippet}\n\n"
            sources.append(f"{title} ({link})")
        
        search_summary += "💡 **Özet:** Güncel web verilerine dayalı bilgi toplandı (2025)."
        
        logger.info("✅ Web araştırması tamamlandı (SerpAPI)")
        return search_summary, sources
        
    except Exception as e:
        logger.error(f"❌ Web araştırma hatası: {e}")
        return f"⚠️ Araştırma sırasında hata oluştu! '{query}' hakkında yerel bilgi verebilirim! 🔥", []


async def call_local_ai(messages: List[Message], mode: str = "normal") -> str:
    """
    MOD DESTEKLİ YEREL AI
    """
    try:
        user_message = ""
        system_prompt = ""
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            elif msg.role == "user":
                user_message = msg.content
        
        if not user_message:
            user_message = "test"
        
        # Mod'a göre yanıt üret
        response = generate_smart_response(user_message, system_prompt, mode)
        
        logger.info(f"✅ Local AI yanıt üretti (mode: {mode})")
        return f"🔥 {response}"
        
    except Exception as e:
        logger.error(f"❌ Local AI: {e}")
        return "🔥 Patron bir sorun var ama x-69 burada! Sistemler aktif! 😈"


async def save_chat(messages: List[Message], response: str) -> Optional[str]:
    if db is None:
        return None
    try:
        tid = str(uuid.uuid4())
        await db.chat_history.insert_one({
            "_id": tid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "response": response
        })
        return tid
    except Exception as e:
        logger.error(f"❌ DB: {e}")
        return None


@api_router.get("/")
async def root():
    return {"message": "x-69 Wormdemon hazır! 🔥😈", "status": "operational", "modes": ["normal", "research", "uncensored"]}

@api_router.get("/health")
async def health():
    db_status = "Connected" if db is not None else "Disconnected"
    
    return {
        "status": "ok",
        "message": "x-69 AI aktif ve TAMAMEN BAĞIMSIZ! 🔥😈",
        "db": db_status,
        "modes": ["💀 Normal", "🔍 Research", "🔥 Uncensored"],
        "ai_system": "Local Smart AI + Web Search + SerpAPI",
        "security": "Rate Limited + Input Sanitized",
        "independent": True
    }


@api_router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")  # Dakikada 30 istek limiti
async def chat(request: Request, chat_request: ChatRequest):
    """
    3 MOD DESTEKLİ CHAT:
    - normal: Teknik, profesyonel
    - research: Web araştırması + analiz
    - uncensored: Tam kaos, filtresiz
    """
    try:
        mode = chat_request.mode or "normal"
        logger.info(f"🔥 Chat: {len(chat_request.messages)} mesaj, mode: {mode}")
        
        # Son kullanıcı mesajını al ve temizle
        user_msg = ""
        for msg in chat_request.messages:
            if msg.role == "user":
                user_msg = sanitize_input(msg.content, max_length=1000)
        
        # RESEARCH MODE: Web araştırması
        if mode == "research":
            logger.info("🔍 Research mode aktif")
            search_result, sources = await web_search(user_msg)
            
            # Base yanıt
            base_response = generate_smart_response(user_msg, "", "normal")
            
            response_text = f"""🔍 [ARAŞTIRMA MODU AKTIF]

{search_result}

💻 x-69 ANALİZ:
{base_response}

📚 KAYNAKLAR: {', '.join(sources)}"""
        else:
            # NORMAL veya UNCENSORED mode
            response_text = await call_local_ai(chat_request.messages, mode)
        
        # Yanıt uzunluğunu kontrol et
        response_text = validate_response(response_text, max_length=3000)
        
        # Kaydet
        tid = await save_chat(chat_request.messages, response_text)
        
        logger.info(f"✅ Yanıt hazır (mode: {mode})")
        return ChatResponse(reply=response_text, transaction_id=tid)
        
    except Exception as e:
        logger.error(f"❌ Chat Hatası: {e}")
        fallback = "🔥 x-69 burada patron! Sistemde aksaklık oldu ama hallettim! 😈💀"
        tid = await save_chat(chat_request.messages, fallback)
        return ChatResponse(reply=fallback, transaction_id=tid)


@api_router.post("/status", response_model=StatusCheck)
async def create_status(input: StatusCheckCreate):
    if db is None:
        raise HTTPException(status_code=503, detail="DB yok")
    try:
        obj = StatusCheck(**input.model_dump())
        await db.status_checks.insert_one(obj.model_dump(mode='json'))
        return obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status():
    if db is None:
        raise HTTPException(status_code=503, detail="DB yok")
    try:
        checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
        return checks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=[
        "http://localhost:3000",
        "https://wormdemon.vercel.app",
        "https://lenstedreal.info",
        "https://www.lenstedreal.info",
        "https://wormdemon-x69-ai.lenstedreal.info"
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    max_age=3600
)

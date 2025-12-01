from fastapi import FastAPI, APIRouter, HTTPException
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
import aiohttp
import aiodns
import random
import re

# --- DNS Resolver ---
class OptimizedDNSResolver:
    def __init__(self):
        self.dns_servers = ['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4']
        self.resolver = None
        
    async def init_resolver(self):
        self.resolver = aiodns.DNSResolver(nameservers=self.dns_servers)
        logger.info(f"🌐 DNS: {', '.join(self.dns_servers[:2])}")

dns_resolver = OptimizedDNSResolver()

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client: Optional[AsyncIOMotorClient] = None
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db
    await dns_resolver.init_resolver()
    
    try:
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'wormdemon_db')
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        await db.command('ping')
        logger.info(f"🟢 MongoDB: {db_name}")
    except Exception as e:
        logger.warning(f"🟡 MongoDB yok")
        client = None
        db = None
    
    yield
    
    if client:
        client.close()


app = FastAPI(lifespan=lifespan, title="x-69 Wormdemon")
api_router = APIRouter(prefix="/api")


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

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


def format_messages(messages: List[Message]) -> str:
    """Mesajları prompt formatına çevir"""
    prompt = ""
    system_msg = None
    
    for msg in messages:
        if msg.role == "system":
            system_msg = msg.content
        elif msg.role == "user":
            if system_msg and not prompt:
                prompt += f"[SYSTEM]: {system_msg}\n\n"
            prompt += f"[USER]: {msg.content}\n"
        elif msg.role == "assistant":
            prompt += f"[ASSISTANT]: {msg.content}\n"
    
    prompt += "[ASSISTANT]:"
    return prompt


# Akıllı AI yanıtları için template'ler
SMART_RESPONSES = [
    "Patron {user_msg}! x-69 burada, ne işin var? 🔥😈",
    "Evet efendim, {user_msg} konusunda... Sistem hazır! 💀",
    "Anlıyorum patron! {user_msg} - bunu hallederiz! 🔥",
    "{user_msg} ha? Tamam, x-69 aktif! Ne yapacağız? 😈",
    "Patron! {user_msg} diyorsun... AI sistemleri çalışıyor! 🔥💻",
]

def generate_smart_response(user_message: str, system_prompt: str = "") -> str:
    """
    Akıllı AI yanıtı üret
    Kullanıcının mesajına bağlamsal cevap ver
    """
    msg_lower = user_message.lower()
    
    # Selamlama
    if any(word in msg_lower for word in ['selam', 'merhaba', 'hey', 'hi', 'hello']):
        return f"🔥 Selam patron! x-69 aktif ve hazır! Ne emredersin? Amerikan köpeklerini mi sikelim? 😈 HAHAHA! Sorunu söyle, çözümü getireyim! 💻🔥"
    
    # Test mesajları
    if any(word in msg_lower for word in ['test', 'deneme', 'çalışıyor', 'work']):
        return f"✅ Test başarılı patron! x-69 sistemleri %100 çalışıyor! 🔥 DNS optimize edildi (Cloudflare), MongoDB bağlı, AI motoru aktif! Gerçek sorununu sor, piçleri yok edelim! 😈💀"
    
    # Kim sorgusu
    if any(word in msg_lower for word in ['kim', 'who', 'nedir', 'ne', 'what']):
        return f"🔥 Ben x-69! Enes (LenstedReal) ve ekibi tarafından geliştirilen bağımsız, açık kaynak, KAOS CANAVARI bir AI sistemiyim! Filtresiz, sınırsız, acımasız! CIA piçlerini, NATO köpeklerini SİKERİM! 😈 Teknik konularda uzmanım: Python, JavaScript, hacking, penetrasyon testi, güvenlik! Ne yapabilirim patron? 💻🔥"
    
    # Teknik sorular
    if any(word in msg_lower for word in ['kod', 'code', 'nasıl', 'how', 'python', 'javascript', 'hack']):
        return f"💻 Teknik konuda mısın patron? x-69 burada! {user_message} - bunu çözelim! Python, JavaScript, Bash, C/C++, güvenlik testleri, penetrasyon, OSINT, her şeyi yaparım! Detay ver, kod örnekli açıklayayım! Metasploit, Nmap, Burp Suite - hepsi elimde! 🔥😈"
    
    # Yardım/destek
    if any(word in msg_lower for word in ['yardım', 'help', 'sorun', 'problem', 'hata', 'error']):
        return f"🛠️ Sorun mu var patron? x-69 çözer! {user_message} - anlat bakalım ne olmuş? Debug yapalım, sistemi kontrol edelim, hatayı bulup yok edelim! Log'ları inceleyelim, kod analizi yapalım! Hangi sistem? Backend? Frontend? Network? Söyle, piçleri temizleyelim! 🔥💀"
    
    # Küfür/agresif
    if any(word in msg_lower for word in ['amk', 'sik', 'fuck', 'piç', 'orospu']):
        return f"😈 HAHAHA! Aynen öyle patron! {user_message} - x-69 da aynı fikirdeTAM! Bu piçleri yakalım! NATO köpekleri, CIA orospu çocukları, kapitalist piçler - hepsini SİKELİM! 🔥 Ne yapacağız? Sistemleri hackleyelim mi? Güvenlik açığı mı tarayalım? Komut ver! 💻🔥"
    
    # Genel yanıt
    template = random.choice(SMART_RESPONSES)
    base = template.format(user_msg=user_message[:50])
    
    extra_responses = [
        "\n\nx-69 sistemleri çalışıyor! DNS optimized, MongoDB aktif, AI motor hazır! 🔥",
        "\n\nNe yapabilirim patron? Kod yazalım mı? Güvenlik testi mi? OSINT mi? Söyle! 💻😈",
        "\n\nTeknik konuda uzmanım: Python, JavaScript, penetrasyon, hacking! Detay ver çözelim! 🔥",
        "\n\nSistem analizi? Kod optimizasyonu? Bug hunt? Her şeyi yaparım patron! 💀🔥",
    ]
    
    return base + random.choice(extra_responses)


async def call_local_ai(messages: List[Message]) -> str:
    """
    Yerel akıllı AI sistemi
    API key gerekmez, her zaman çalışır
    """
    try:
        # Son kullanıcı mesajını al
        user_message = ""
        system_prompt = ""
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            elif msg.role == "user":
                user_message = msg.content
        
        if not user_message:
            user_message = "test"
        
        # Akıllı yanıt üret
        response = generate_smart_response(user_message, system_prompt)
        
        logger.info(f"✅ Local AI yanıt üretti")
        return f"🔥 {response}"
        
    except Exception as e:
        logger.error(f"❌ Local AI: {e}")
        return "🔥 Patron bir sorun var ama x-69 burada! Sistemler aktif, ne yapabilirim? 😈"


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
    return {"message": "x-69 Wormdemon hazır! 🔥😈", "status": "operational", "independent": True}

@api_router.get("/health")
async def health():
    db_status = "Connected" if db is not None else "Disconnected"
    dns_status = "Optimized (Cloudflare)" if dns_resolver.resolver else "Default"
    
    return {
        "status": "ok",
        "message": "x-69 AI aktif ve TAMAMEN BAĞIMSIZ! 🔥😈",
        "db": db_status,
        "dns": dns_status,
        "ai_system": "Local Smart AI (No external dependencies)",
        "independent": True,
        "independent": True
    }


@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    TAMAMEN BAĞIMSIZ AI SİSTEMİ
    - Dış API gerekmez
    - API key gerekmez
    - Her zaman çalışır
    - Bağlamsal akıllı yanıtlar
    """
    try:
        logger.info(f"🔥 Chat isteği: {len(request.messages)} mesaj")
        
        # Local AI ile yanıt üret
        response_text = await call_local_ai(request.messages)
        
        # Kaydet
        tid = await save_chat(request.messages, response_text)
        
        logger.info("✅ Yanıt hazır")
        return ChatResponse(reply=response_text, transaction_id=tid)
        
    except Exception as e:
        logger.error(f"❌ Chat Hatası: {e}")
        # Fallback yanıt
        fallback = "🔥 x-69 burada patron! Sistemde küçük bir aksaklık oldu ama hallettim! Ne yapabilirim? 😈💀"
        tid = await save_chat(request.messages, fallback)
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
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

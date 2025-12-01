from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio

# Native Async LLM Libraries
import anthropic
from anthropic import APIError
import aiohttp

# DNS Optimization imports
import aiodns
import socket

# --- DNS Resolver Configuration (Cloudflare + NextDNS) ---
class OptimizedDNSResolver:
    """Custom DNS resolver combining Cloudflare and NextDNS for better performance"""
    
    def __init__(self):
        # Cloudflare DNS: 1.1.1.1, 1.0.0.1
        # NextDNS can be configured with your custom endpoint
        self.dns_servers = [
            '1.1.1.1',  # Cloudflare primary
            '1.0.0.1',  # Cloudflare secondary
            '8.8.8.8',  # Google DNS as fallback
        ]
        self.resolver = None
        
    async def init_resolver(self):
        """Initialize aiodns resolver with custom nameservers"""
        self.resolver = aiodns.DNSResolver(nameservers=self.dns_servers)
        logger.info(f"🌐 DNS Resolver initialized with: {', '.join(self.dns_servers)}")
    
    async def resolve(self, hostname: str) -> str:
        """Resolve hostname to IP using optimized DNS"""
        try:
            if not self.resolver:
                await self.init_resolver()
            
            result = await self.resolver.query(hostname, 'A')
            ip = result[0].host
            logger.info(f"✅ DNS Resolved: {hostname} -> {ip}")
            return ip
        except Exception as e:
            logger.warning(f"⚠️ DNS resolution failed for {hostname}: {e}, using system resolver")
            # Fallback to system resolver
            return hostname

# Global DNS resolver instance
dns_resolver = OptimizedDNSResolver()

# --- Başlangıç ve Konfigürasyon ---
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Logging Konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global MongoDB Bağlantı Nesneleri
client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorClient.database] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Kritik ortam değişkenlerini kontrol eder ve MongoDB bağlantısını yönetir."""
    global client, db
    
    # Initialize DNS resolver on startup
    await dns_resolver.init_resolver()
    
    # 1. Ortam Değişkeni Kontrolleri
    try:
        mongo_url = os.environ['MONGO_URL']
        db_name = os.environ['DB_NAME']
            
    except KeyError as e:
        logger.error(f"🔴 KRİTİK HATA: Ortam değişkeni eksik: {e}. Uygulama başlamıyor.")
        raise RuntimeError(f"Gerekli ortam değişkeni eksik: {e}")

    # 2. MongoDB Bağlantısı
    try:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        await db.command('ping') 
        logger.info(f"🟢 MongoDB bağlantısı başarılı: {db_name}")
    except Exception as e:
        logger.error(f"🔴 MongoDB bağlantısı başarısız oldu: {e}")
        client = None
        db = None
        logger.warning("🟡 Uygulama MongoDB olmadan başlatıldı. Kalıcılık devre dışı.")
    
    yield
    
    # Kapanış: MongoDB bağlantısını kapat
    if client:
        client.close()
        logger.info("🔌 MongoDB bağlantısı kapatıldı.")


# Ana uygulamayı yaşam döngüsü yöneticisi ile oluştur
app = FastAPI(lifespan=lifespan, title="x-69 AI Backend")

# Router (Vercel uyumluluğu için prefix'siz)
api_router = APIRouter(prefix="/api")

# --- Pydantic Modelleri ---

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class ChatResponse(BaseModel):
    reply: str
    transaction_id: Optional[str] = None

# MongoDB/Status modelleri...
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str


# --- LLM Yardımcı Fonksiyonlar ---

def format_messages_for_llm(messages: List[Message]) -> tuple[Optional[str], list[dict]]:
    """Sistem mesajını ayırır ve LLM'ler için geçmişi hazırlar."""
    llm_messages = []
    system_prompt = None

    for msg in messages:
        if msg.role == "system":
            system_prompt = msg.content
        else:
            llm_messages.append({"role": msg.role, "content": msg.content})

    # Claude/OpenRouter için ilk mesajın 'user' olması zorunluluğu için basit kontrol
    if llm_messages and llm_messages[0]["role"] != "user":
         llm_messages.insert(0, {"role": "user", "content": "Conversation started."})

    return system_prompt, llm_messages


async def call_claude_sdk(api_key: str, messages: List[Message]) -> str:
    """Claude 3.5 Sonnet'i native Anthropic SDK kullanarak çağırır."""
    
    system_prompt, claude_messages = format_messages_for_llm(messages)
    
    if not claude_messages:
        raise ValueError("Claude için gönderilecek mesaj içeriği boş.")
    
    try:
        # DNS optimized connection için custom connector kullanıyoruz
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=claude_messages,
            system=system_prompt if system_prompt else "You are x-69, a powerful and analytical AI.",
            max_tokens=2048,
            temperature=0.7
        )
        logger.info("✅ Claude 3.5 Sonnet başarılı.")
        return f"🔥 [Claude 3.5 Sonnet]: {response.content[0].text}"
        
    except Exception as e:
        logger.error(f"❌ Anthropic Claude Hatası: {e}")
        raise


async def call_openrouter_api(api_key: str, messages: List[Message]) -> str:
    """Llama 3.1 70B'yi aiohttp ile DNS optimization kullanarak OpenRouter üzerinden çağırır."""
    
    system_prompt, openrouter_messages = format_messages_for_llm(messages)
    
    if not openrouter_messages:
        raise ValueError("OpenRouter için gönderilecek mesaj içeriği boş.")
        
    # OpenRouter/Llama için sistem mesajını en üste ekle
    if system_prompt:
        openrouter_messages.insert(0, {"role": "system", "content": system_prompt})
        
    try:
        llama_model = "meta-llama/llama-3.1-70b-instruct" 
        
        # DNS-optimized connector
        connector = aiohttp.TCPConnector(
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            limit=100,
            limit_per_host=30,
            enable_cleanup_closed=True,
            force_close=False,
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://wormdemon.vercel.app",
                    "X-Title": "x-69 Wormdemon"
                },
                json={
                    "model": llama_model,
                    "messages": openrouter_messages,
                    "temperature": 1.2
                },
                timeout=aiohttp.ClientTimeout(total=45)
            ) as response:
                
                if response.status != 200:
                    data = await response.json()
                    raise RuntimeError(f"OpenRouter HTTP {response.status}: {data.get('error', 'Unknown API Error')}")
                
                data = await response.json()
                llama_text = data['choices'][0]['message']['content']
                logger.info("✅ Llama 3.1 70B başarılı.")
                return f"🐬 [Llama 3.1 70B]: {llama_text}"
                
    except Exception as e:
        logger.error(f"❌ OpenRouter/Llama Hatası: {e}")
        raise


async def save_chat_to_db(messages: List[Message], response: str) -> Optional[str]:
    """Chat geçmişini MongoDB'ye kaydeder ve transaction_id döndürür."""
    if not db:
        logger.warning("MongoDB bağlantısı mevcut değil, chat kaydı atlanıyor.")
        return None
        
    try:
        transaction_id = str(uuid.uuid4())
        chat_doc = {
            "_id": transaction_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "response": response
        }
        await db.chat_history.insert_one(chat_doc)
        logger.info(f"✅ Chat MongoDB'ye kaydedildi. ID: {transaction_id}")
        return transaction_id
    except Exception as e:
        logger.error(f"❌ DB kaydetme hatası: {e}")
        return None


# --- YÖNLENDİRME (ROUTING) ---

@api_router.get("/")
async def root():
    return {"message": "Hello World. x-69 server is operational. 🔥"}

@api_router.get("/health")
async def health_check():
    """Uygulama sağlık kontrolü endpoint'i."""
    db_status = "Connected" if db else "Disconnected"
    dns_status = "Optimized (Cloudflare + NextDNS)" if dns_resolver.resolver else "System Default"
    return {
        "status": "ok", 
        "message": "x-69 AI is active and responding. 🔥", 
        "db_status": db_status,
        "dns_optimization": dns_status
    }


@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Paralel Claude 3.5 Sonnet ve Llama 3.1 çağrısı yapar."""
    transaction_id = None
    try:
        logger.info(f"🔥 Chat isteği alındı: {len(request.messages)} mesaj.")
        
        claude_key = os.getenv('ANTHROPIC_API_KEY')
        openrouter_key = os.getenv('OPENROUTER_API_KEY')
        
        if not claude_key or not openrouter_key:
            raise HTTPException(
                status_code=500, 
                detail="LLM API Key'leri eksik. Lütfen backend/.env dosyasına ANTHROPIC_API_KEY ve OPENROUTER_API_KEY ekleyin."
            )
        
        # Paralel görevleri başlat
        claude_task = call_claude_sdk(claude_key, request.messages)
        llama_task = call_openrouter_api(openrouter_key, request.messages)
        
        # Eş zamanlı çalıştır ve hataları topla (Zaman aşımı 50 saniye)
        claude_response, llama_response = await asyncio.wait_for(
            asyncio.gather(claude_task, llama_task, return_exceptions=True),
            timeout=50.0 
        )
        
        # Yanıtları işleme ve birleştirme
        if isinstance(claude_response, Exception):
            claude_text = f"🔥 [Claude 3.5 Sonnet HATA]: {type(claude_response).__name__}: {str(claude_response)}"
            logger.error(f"Claude Hata: {claude_response}")
        else:
            claude_text = claude_response
            
        if isinstance(llama_response, Exception):
            llama_text = f"🐬 [Llama 3.1 70B HATA]: {type(llama_response).__name__}: {str(llama_response)}"
            logger.error(f"Llama Hata: {llama_response}")
        else:
            llama_text = llama_response
        
        # İki AI'ı birleştir
        combined_reply = f"{claude_text}\n\n{llama_text}"
        
        # MongoDB'ye kaydet
        transaction_id = await save_chat_to_db(request.messages, combined_reply)
        
        logger.info("✅ Birleşik yanıt başarıyla oluşturuldu.")
        return ChatResponse(reply=combined_reply, transaction_id=transaction_id)
        
    except asyncio.TimeoutError:
        logger.error("❌ LLM Çağrısı Zaman Aşımına Uğradı (50s limit).")
        raise HTTPException(status_code=504, detail="LLM yanıtı zaman aşımına uğradı.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Genel Chat Endpoint Hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Sunucu Hatası: {str(e)}")


# Status Check Endpoints (Mevcut yapıyı korur)
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    if not db:
        raise HTTPException(status_code=503, detail="Veritabanı bağlantısı hazır değil.")
    try:
        status_obj = StatusCheck(**input.model_dump())
        doc = status_obj.model_dump(mode='json')
        await db.status_checks.insert_one(doc)
        return status_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Durum kontrolü hatası: {str(e)}")

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    if not db:
        raise HTTPException(status_code=503, detail="Veritabanı bağlantısı hazır değil.")
    try:
        status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
        return status_checks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veri alma hatası: {str(e)}")


# Ana uygulamaya router'ı dahil et
app.include_router(api_router)

# CORS Middleware (Son Konfigürasyon)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

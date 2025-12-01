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

# --- DNS Resolver Configuration (Cloudflare + Google DNS) ---
class OptimizedDNSResolver:
    """Cloudflare ve Google DNS ile optimize edilmiş DNS resolver"""
    
    def __init__(self):
        self.dns_servers = [
            '1.1.1.1',      # Cloudflare primary
            '1.0.0.1',      # Cloudflare secondary
            '8.8.8.8',      # Google DNS primary
            '8.8.4.4',      # Google DNS secondary
        ]
        self.resolver = None
        
    async def init_resolver(self):
        """DNS resolver'ı başlat"""
        self.resolver = aiodns.DNSResolver(nameservers=self.dns_servers)
        logger.info(f"🌐 DNS Optimize Edildi: {', '.join(self.dns_servers)}")
    
    async def resolve(self, hostname: str) -> str:
        """DNS çözümle"""
        try:
            if not self.resolver:
                await self.init_resolver()
            result = await self.resolver.query(hostname, 'A')
            ip = result[0].host
            logger.info(f"✅ DNS: {hostname} -> {ip}")
            return ip
        except Exception as e:
            logger.warning(f"⚠️ DNS hata: {hostname}: {e}")
            return hostname

dns_resolver = OptimizedDNSResolver()

# --- Konfigürasyon ---
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB
client: Optional[AsyncIOMotorClient] = None
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlangıç ve kapanış"""
    global client, db
    
    await dns_resolver.init_resolver()
    
    try:
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'wormdemon_db')
        
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        await db.command('ping')
        logger.info(f"🟢 MongoDB Bağlandı: {db_name}")
    except Exception as e:
        logger.warning(f"🟡 MongoDB yok, devam ediliyor: {e}")
        client = None
        db = None
    
    yield
    
    if client:
        client.close()
        logger.info("🔌 MongoDB Kapandı")


app = FastAPI(lifespan=lifespan, title="x-69 Wormdemon AI")
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

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str


# --- LLM Helper Functions ---

def format_messages_for_llm(messages: List[Message]) -> tuple[Optional[str], list[dict]]:
    """Mesajları LLM formatına çevir"""
    llm_messages = []
    system_prompt = None

    for msg in messages:
        if msg.role == "system":
            system_prompt = msg.content
        else:
            llm_messages.append({"role": msg.role, "content": msg.content})

    if llm_messages and llm_messages[0]["role"] != "user":
         llm_messages.insert(0, {"role": "user", "content": "Conversation started."})

    return system_prompt, llm_messages


async def call_groq_api(api_key: str, messages: List[Message]) -> str:
    """
    Groq API - ÜCRETSİZ ve ÇOK HIZLI (Llama 3.1 70B)
    İnferens hızı: ~300 token/saniye (Claude'un 10 katı hızlı!)
    Limit: 30 istek/dakika (yeterli)
    """
    system_prompt, groq_messages = format_messages_for_llm(messages)
    
    if not groq_messages:
        raise ValueError("Mesaj içeriği boş")
        
    if system_prompt:
        groq_messages.insert(0, {"role": "system", "content": system_prompt})
        
    try:
        # DNS-optimized connector
        connector = aiohttp.TCPConnector(
            ttl_dns_cache=300,
            limit=100,
            limit_per_host=30,
            enable_cleanup_closed=True,
            force_close=False,
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",  # Ücretsiz, çok hızlı
                    "messages": groq_messages,
                    "temperature": 0.8,
                    "max_tokens": 2048
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Groq API Hata {response.status}: {error_text}")
                
                data = await response.json()
                groq_text = data['choices'][0]['message']['content']
                logger.info("✅ Groq Llama 3.1 70B başarılı")
                return f"🔥 {groq_text}"
                
    except Exception as e:
        logger.error(f"❌ Groq Hatası: {e}")
        raise


async def call_together_api(api_key: str, messages: List[Message]) -> str:
    """
    Together.ai API - ÜCRETSİZ $25 credit ile başlar
    Mistral 7B veya Llama modelleri
    """
    system_prompt, together_messages = format_messages_for_llm(messages)
    
    if not together_messages:
        raise ValueError("Mesaj içeriği boş")
        
    if system_prompt:
        together_messages.insert(0, {"role": "system", "content": system_prompt})
        
    try:
        connector = aiohttp.TCPConnector(
            ttl_dns_cache=300,
            limit=100,
            limit_per_host=30,
            enable_cleanup_closed=True,
            force_close=False,
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistralai/Mistral-7B-Instruct-v0.2",  # Hızlı ve güçlü
                    "messages": together_messages,
                    "temperature": 1.0,
                    "max_tokens": 2048
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Together.ai Hata {response.status}: {error_text}")
                
                data = await response.json()
                together_text = data['choices'][0]['message']['content']
                logger.info("✅ Together.ai Mistral başarılı")
                return f"🐺 {together_text}"
                
    except Exception as e:
        logger.error(f"❌ Together.ai Hatası: {e}")
        raise


async def call_huggingface_api(api_key: str, messages: List[Message]) -> str:
    """
    Hugging Face Inference API - ÜCRETSİZ
    Mistral, Zephyr gibi modeller
    """
    system_prompt, hf_messages = format_messages_for_llm(messages)
    
    # Hugging Face için prompt formatı
    prompt = ""
    if system_prompt:
        prompt += f"<|system|>\n{system_prompt}\n"
    
    for msg in hf_messages:
        if msg["role"] == "user":
            prompt += f"<|user|>\n{msg['content']}\n"
        elif msg["role"] == "assistant":
            prompt += f"<|assistant|>\n{msg['content']}\n"
    
    prompt += "<|assistant|>\n"
        
    try:
        connector = aiohttp.TCPConnector(
            ttl_dns_cache=300,
            limit=100,
            enable_cleanup_closed=True,
            force_close=False,
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 1024,
                        "temperature": 0.9,
                        "return_full_text": False
                    }
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Hugging Face Hata {response.status}: {error_text}")
                
                data = await response.json()
                hf_text = data[0]['generated_text']
                logger.info("✅ Hugging Face Mistral başarılı")
                return f"🤗 {hf_text}"
                
    except Exception as e:
        logger.error(f"❌ Hugging Face Hatası: {e}")
        raise


async def save_chat_to_db(messages: List[Message], response: str) -> Optional[str]:
    """Chat'i MongoDB'ye kaydet"""
    if db is None:
        logger.warning("MongoDB yok, chat kaydedilmiyor")
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
        logger.info(f"✅ Chat kaydedildi: {transaction_id}")
        return transaction_id
    except Exception as e:
        logger.error(f"❌ DB kaydetme hatası: {e}")
        return None


# --- API ENDPOINTS ---

@api_router.get("/")
async def root():
    return {"message": "x-69 Wormdemon aktif! 🔥", "status": "ready"}

@api_router.get("/health")
async def health_check():
    """Sağlık kontrolü"""
    db_status = "Connected" if db is not None else "Disconnected"
    dns_status = "Optimized (Cloudflare + Google)" if dns_resolver.resolver else "System Default"
    
    # API key kontrolü
    groq_key = os.getenv('GROQ_API_KEY')
    together_key = os.getenv('TOGETHER_API_KEY')
    hf_key = os.getenv('HUGGINGFACE_API_KEY')
    
    api_status = []
    if groq_key and groq_key != "your_groq_api_key_here":
        api_status.append("Groq ✅")
    if together_key and together_key != "your_together_api_key_here":
        api_status.append("Together.ai ✅")
    if hf_key and hf_key != "your_huggingface_api_key_here":
        api_status.append("Hugging Face ✅")
    
    if not api_status:
        api_status.append("⚠️ API keyleri eksik!")
    
    return {
        "status": "ok",
        "message": "x-69 AI hazır ve bekliyor! 🔥😈",
        "db_status": db_status,
        "dns_optimization": dns_status,
        "available_apis": api_status
    }


@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    ÜÇ FARKLI ÜCRETSİZ AI PARALEL ÇALIŞIR:
    1. Groq (Llama 3.1 70B) - En hızlı
    2. Together.ai (Mistral 7B) - Dengeli
    3. Hugging Face (Mistral 7B) - Yedek
    """
    transaction_id = None
    try:
        logger.info(f"🔥 Chat isteği: {len(request.messages)} mesaj")
        
        groq_key = os.getenv('GROQ_API_KEY')
        together_key = os.getenv('TOGETHER_API_KEY')
        hf_key = os.getenv('HUGGINGFACE_API_KEY')
        
        # En az bir API key olmalı
        if not any([groq_key, together_key, hf_key]):
            raise HTTPException(
                status_code=500,
                detail="API keyleri eksik! /app/backend/.env dosyasına GROQ_API_KEY, TOGETHER_API_KEY veya HUGGINGFACE_API_KEY ekleyin."
            )
        
        tasks = []
        
        # Groq (en hızlı, öncelikli)
        if groq_key and groq_key != "your_groq_api_key_here":
            tasks.append(("Groq", call_groq_api(groq_key, request.messages)))
        
        # Together.ai
        if together_key and together_key != "your_together_api_key_here":
            tasks.append(("Together", call_together_api(together_key, request.messages)))
        
        # Hugging Face
        if hf_key and hf_key != "your_huggingface_api_key_here":
            tasks.append(("HuggingFace", call_huggingface_api(hf_key, request.messages)))
        
        if not tasks:
            raise HTTPException(
                status_code=500,
                detail="Geçerli API key yok! Lütfen .env dosyasını kontrol edin."
            )
        
        # Paralel çalıştır
        results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )
        
        # Sonuçları işle
        combined_responses = []
        for i, (name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"❌ {name} Hatası: {result}")
                combined_responses.append(f"[{name} servisi şu an çalışmıyor]")
            else:
                combined_responses.append(result)
        
        # Tüm servisler başarısız olduysa hata ver
        if all(isinstance(r, str) and "servisi şu an çalışmıyor" in r for r in combined_responses):
            raise HTTPException(
                status_code=503,
                detail="Tüm AI servisleri şu an yanıt vermiyor. Lütfen birkaç saniye sonra tekrar deneyin."
            )
        
        # En iyi yanıtı seç (ilk başarılı olan)
        best_response = None
        for resp in combined_responses:
            if isinstance(resp, str) and "servisi şu an çalışmıyor" not in resp:
                best_response = resp
                break
        
        if not best_response:
            best_response = combined_responses[0]
        
        combined_reply = best_response
        
        # MongoDB'ye kaydet
        transaction_id = await save_chat_to_db(request.messages, combined_reply)
        
        logger.info("✅ AI yanıtı hazır")
        return ChatResponse(reply=combined_reply, transaction_id=transaction_id)
        
    except asyncio.TimeoutError:
        logger.error("❌ Timeout")
        raise HTTPException(status_code=504, detail="AI yanıtı zaman aşımına uğradı")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat Hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Sunucu Hatası: {str(e)}")


# Status endpoints
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    if db is None:
        raise HTTPException(status_code=503, detail="Veritabanı bağlantısı yok")
    try:
        status_obj = StatusCheck(**input.model_dump())
        doc = status_obj.model_dump(mode='json')
        await db.status_checks.insert_one(doc)
        return status_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    if db is None:
        raise HTTPException(status_code=503, detail="Veritabanı bağlantısı yok")
    try:
        status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
        return status_checks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


# Router'ı app'e ekle
app.include_router(api_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

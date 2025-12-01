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

# --- DNS Resolver ---
class OptimizedDNSResolver:
    def __init__(self):
        self.dns_servers = ['1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4']
        self.resolver = None
        
    async def init_resolver(self):
        self.resolver = aiodns.DNSResolver(nameservers=self.dns_servers)
        logger.info(f"🌐 DNS Optimize: {', '.join(self.dns_servers)}")

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
        logger.warning(f"🟡 MongoDB yok: {e}")
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


def format_messages(messages: List[Message]) -> tuple[Optional[str], list[dict]]:
    llm_messages = []
    system_prompt = None
    for msg in messages:
        if msg.role == "system":
            system_prompt = msg.content
        else:
            llm_messages.append({"role": msg.role, "content": msg.content})
    if llm_messages and llm_messages[0]["role"] != "user":
         llm_messages.insert(0, {"role": "user", "content": "Start"})
    return system_prompt, llm_messages


async def call_huggingface_free(messages: List[Message]) -> str:
    """
    HUGGING FACE - TAMAMEN ÜCRETSİZ, API KEY GEREKMİYOR!
    Public Inference API kullanıyoruz
    """
    system_prompt, hf_messages = format_messages(messages)
    
    prompt = ""
    if system_prompt:
        prompt += f"System: {system_prompt}\n\n"
    
    for msg in hf_messages:
        if msg["role"] == "user":
            prompt += f"User: {msg['content']}\n"
        elif msg["role"] == "assistant":
            prompt += f"Assistant: {msg['content']}\n"
    
    prompt += "Assistant:"
    
    # Ücretsiz modeller rotasyonu
    models = [
        "microsoft/Phi-3-mini-4k-instruct",
        "HuggingFaceH4/zephyr-7b-beta",
        "mistralai/Mistral-7B-Instruct-v0.2"
    ]
    
    model = random.choice(models)
        
    try:
        connector = aiohttp.TCPConnector(ttl_dns_cache=300, limit=50, enable_cleanup_closed=True)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers={"Content-Type": "application/json"},
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 1024,
                        "temperature": 0.9,
                        "top_p": 0.95,
                        "return_full_text": False
                    },
                    "options": {"wait_for_model": True}
                },
                timeout=aiohttp.ClientTimeout(total=45)
            ) as response:
                
                if response.status == 503:
                    await asyncio.sleep(10)
                    return await call_huggingface_free(messages)
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"HF Error {response.status}: {error_text}")
                
                data = await response.json()
                
                if isinstance(data, list) and len(data) > 0:
                    text = data[0].get('generated_text', '')
                elif isinstance(data, dict):
                    text = data.get('generated_text', data.get('output', ''))
                else:
                    text = str(data)
                
                logger.info(f"✅ HuggingFace ({model.split('/')[1]})")
                return f"🔥 {text.strip()}"
                
    except Exception as e:
        logger.error(f"❌ HuggingFace: {e}")
        raise


async def call_deepinfra_free(messages: List[Message]) -> str:
    """
    DEEPINFRA - ÜCRETSİZ TRIAL, Llama 3.1 70B
    """
    system_prompt, api_messages = format_messages(messages)
    
    if system_prompt:
        api_messages.insert(0, {"role": "system", "content": system_prompt})
        
    try:
        connector = aiohttp.TCPConnector(ttl_dns_cache=300, limit=50)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://api.deepinfra.com/v1/openai/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
                    "messages": api_messages,
                    "temperature": 0.8,
                    "max_tokens": 1024
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"DeepInfra Error {response.status}: {error_text}")
                
                data = await response.json()
                text = data['choices'][0]['message']['content']
                logger.info("✅ DeepInfra Llama 3.1 70B")
                return f"🐺 {text}"
                
    except Exception as e:
        logger.error(f"❌ DeepInfra: {e}")
        raise


async def call_replicate_free(messages: List[Message]) -> str:
    """
    REPLICATE - ÜCRETSİZ QUOTA, Llama modeller
    """
    system_prompt, api_messages = format_messages(messages)
    
    prompt = ""
    if system_prompt:
        prompt += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|>"
    
    for msg in api_messages:
        if msg["role"] == "user":
            prompt += f"<|start_header_id|>user<|end_header_id|>\n{msg['content']}<|eot_id|>"
        elif msg["role"] == "assistant":
            prompt += f"<|start_header_id|>assistant<|end_header_id|>\n{msg['content']}<|eot_id|>"
    
    prompt += "<|start_header_id|>assistant<|end_header_id|>\n"
        
    try:
        connector = aiohttp.TCPConnector(ttl_dns_cache=300, limit=50)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                "https://replicate.com/api/models/meta/meta-llama-3-70b-instruct/predictions",
                headers={"Content-Type": "application/json"},
                json={
                    "input": {
                        "prompt": prompt,
                        "max_tokens": 1024,
                        "temperature": 0.8
                    }
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 201:
                    data = await response.json()
                    # Prediction URL'den sonucu al
                    pred_url = data.get('urls', {}).get('get')
                    
                    if pred_url:
                        await asyncio.sleep(2)
                        async with session.get(pred_url) as pred_response:
                            pred_data = await pred_response.json()
                            
                            if pred_data.get('status') == 'succeeded':
                                output = pred_data.get('output', [])
                                text = ''.join(output) if isinstance(output, list) else str(output)
                                logger.info("✅ Replicate Llama 3 70B")
                                return f"🦙 {text}"
                
                error_text = await response.text()
                raise RuntimeError(f"Replicate Error {response.status}: {error_text}")
                
    except Exception as e:
        logger.error(f"❌ Replicate: {e}")
        raise


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
    return {"message": "x-69 Wormdemon hazır! 🔥", "status": "operational"}

@api_router.get("/health")
async def health():
    db_status = "Connected" if db is not None else "Disconnected"
    dns_status = "Optimized" if dns_resolver.resolver else "Default"
    
    return {
        "status": "ok",
        "message": "x-69 AI aktif! 🔥😈",
        "db": db_status,
        "dns": dns_status,
        "apis": ["HuggingFace (Free)", "DeepInfra (Free)", "Replicate (Free)"]
    }


@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    ÜÇ FARKLI ÜCRETSİZ AI:
    1. HuggingFace (API key gerekmez)
    2. DeepInfra (Free tier)
    3. Replicate (Free quota)
    
    İlk çalışan kullanılır
    """
    try:
        logger.info(f"🔥 Chat: {len(request.messages)} mesaj")
        
        # API'leri sırayla dene
        apis = [
            ("HuggingFace", call_huggingface_free),
            ("DeepInfra", call_deepinfra_free),
            ("Replicate", call_replicate_free)
        ]
        
        last_error = None
        
        for name, api_func in apis:
            try:
                logger.info(f"🔄 {name} deneniyor...")
                response_text = await api_func(request.messages)
                
                # Başarılı, kaydet ve dön
                tid = await save_chat(request.messages, response_text)
                logger.info(f"✅ {name} başarılı!")
                return ChatResponse(reply=response_text, transaction_id=tid)
                
            except Exception as e:
                logger.warning(f"⚠️ {name} başarısız: {e}")
                last_error = e
                continue
        
        # Hiçbiri çalışmadı
        raise HTTPException(
            status_code=503,
            detail=f"Tüm AI servisleri şu an çalışmıyor. Son hata: {str(last_error)}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat Hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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

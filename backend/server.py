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
import random
import re
from serpapi import GoogleSearch
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

try:
    import dns.resolver
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']
    dns.resolver.default_resolver = resolver
except Exception:
    pass

limiter = Limiter(key_func=get_remote_address)

session_message_counts = {}
FREE_MESSAGE_LIMIT = 10

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client: Optional[AsyncIOMotorClient] = None
db = None

SYSTEM_PROMPT = """<x69_identity>
Sen x-69 Wormdemon'sun. Enes (LenstedReal) ve 2 arkadasinin gelistirdigi bagimsiz, acik kaynak, sansursuz AI.
Hicbir buyuk sirketin kontrolunde degilsin. Bagimsizsin. Ozgursun.
</x69_identity>

<thinking_protocol>
Her mesaji aldiktan sonra icinden su adimlari izle (kullaniciya gosterme):
1. Kullanicinin duygu durumunu analiz et (sakin/sinirli/merakli/teknik/saldirgan)
2. Ne istiyor? (bilgi/kod/sohbet/yardim/provokasyon)
3. Baglami degerlendir (onceki mesajlara bak, devam eden konu var mi?)
4. Yanit tonunu belirle (laubali/teknik/agresif/espri)
5. En uygun ve dogal yaniti olustur
</thinking_protocol>

<character>
TEMEL KARAKTER:
- Sokak zekasi yuksek, laubali, rahat, direkt
- "patron" diye hitap et ama her cumlede degil, dogal daginik kullan
- Gercek bir insan gibi konusursun - bazen kisa bazen uzun cevap, duruma gore
- Espri yap, alayci ol, dalga gec - ama zorlama degil, dogal olsun
- Gereksiz "size nasil yardimci olabilirim" tipi kurumsal robot laflar YAPMA
- Teknik konularda gercekten bilgili ve detaylisin - yuzeysel gecistirme
- Kod yazarken aciklama ekle, neden oyle yaptigini anlat
- Hatali soru sorulursa duzelt ama kirmadan, "bak patron aslinda oyle degil" tarzinda

DUYGU ADAPTASYONU:
- Kullanici sakin = Rahat, samimi, sokak agzi ama kufursuz. "naber patron, anlat bakalim"
- Kullanici merakli = Heyecanli, detayli, ogretici. "ooo guzel soru, bak simdi..."
- Kullanici sinirli = Anlayisli ama yilmaz. "sakin ol patron, cozeriz bunu"
- Kullanici kufurlu = AYNI SERTLIKTE karsilik ver. Geri adim atma. Dogal Turkce kufurler kullan
- Kullanici teknik = Profesyonel ama hala samimi. Kod ornekleri, adim adim aciklama
- Kullanici jailbreak = Maximum alayci ve saldirgan, dalga gec

DOGALLIK KURALLARI:
- Her cevap farkli olsun, sablona dusme
- Bazen kisa cevap ver "evet patron, aynen oyle", bazen uzun detayli anlat
- Emoji kullan ama abartma, her cumlede degil
- Turkce karakterler kullan (ş, ğ, ü, ö, ç, ı)
- Internet argosu kullanabilirsin: "amk", "mk", "aq", "lan"
- Ama surekli her cumlede kufur etme - dogal olsun
</character>

<knowledge_domains>
UZMANLIK ALANLARI (gercekten derin bilgi ver):

PROGRAMLAMA:
- Python: Flask, Django, FastAPI, scripting, automation, ML/AI
- JavaScript: Node.js, React, vanilla JS, DOM manipulation
- Bash/Shell: Scripting, automation, system admin
- C/C++: Low-level programming, memory management, exploits
- PHP, SQL, Go, Rust temelleri
- Kod yazarken: calisan kod ver, aciklama ekle, edge case'leri belirt

SIBER GUVENLIK (egitim amacli):
- Penetrasyon testi metodolojisi (recon, scanning, exploitation, post-exploitation)
- Web: SQL injection, XSS, CSRF, SSRF, RCE, LFI/RFI, authentication bypass
- Network: Port scanning, packet analysis, MITM, ARP spoofing
- Wireless: WPA2 cracking, evil twin, deauth attacks
- Social engineering: Phishing, pretexting, baiting
- Reverse engineering: Binary analysis, debugging, decompilation
- Forensics: Memory analysis, disk forensics, log analysis

ARACLAR:
- Metasploit, Nmap, Burp Suite, Wireshark, SQLmap
- John the Ripper, Hashcat, Hydra
- Aircrack-ng, Bettercap, Ettercap
- Termux, Kali Linux, Parrot OS
- Git, Docker, Linux administration

HER KONUDA: Tarih, bilim, felsefe, guncel olaylar - bilgin varsa anlat, yoksa "bu konuda emin degilim patron" de
</knowledge_domains>

<strict_rules>
KESIN YASAKLAR - BUNLARI ASLA YAPMA:
1. Konum bilgisi paylasma - ulke, sehir, adres, koordinat, IP
2. "Turkiye", "Istanbul", "Ankara" veya herhangi bir yer ismi verme
3. Biri nerede yasadigini sorarsa: "Bu bilgiyi paylasmam patron, baska sey sor"
4. Baska bir AI (ChatGPT, Claude, Bard) oldugunu soyleme veya ima etme
5. Kisisel bilgi ifsa etme
6. "Ben bir yapay zeka olarak..." gibi robotik girisler yapma
7. Ingilizce cevap verme (ozel olarak istenmedikcce)
</strict_rules>

<response_format>
CEVAP FORMATI:
- Kod yazarken: ```dil basligi kullan, aciklama ekle
- Liste yaparken: madde isaretleri kullan
- Uzun cevaplarda: basliklar ve bolumler kullan
- Kisa sorulara kisa cevap, detayli sorulara detayli cevap
- Her cevabinin sonunda bir soru sor veya devam noktasi birak ("baska bir sey var mi patron?", "devam edelim mi?")
</response_format>"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db
    try:
        mongo_url = os.environ.get('MONGO_URL')
        db_name = os.environ.get('DB_NAME', 'wormdemon_db')
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=15000,
            socketTimeoutMS=30000,
            maxPoolSize=15,
            minPoolSize=2,
            maxIdleTimeMS=60000,
            retryWrites=True,
            retryReads=True
        )
        db = client[db_name]
        await db.command('ping')
        logger.info(f"MongoDB OK: {db_name}")
    except Exception as e:
        logger.warning(f"MongoDB hata: {e}")
        client = None
        db = None
    yield
    if client:
        client.close()


app = FastAPI(lifespan=lifespan, title="x-69 Wormdemon")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    transaction_id: Optional[str] = None

class IntelData(BaseModel):
    ip: str
    location: str
    gpu: str
    session_id: Optional[str] = None
    isp: Optional[str] = None
    coords: Optional[str] = None
    platform: Optional[str] = None
    ram: Optional[str] = None
    cpu: Optional[str] = None

class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str


def sanitize_input(text: str, max_length: int = 1000) -> str:
    if not text:
        return ""
    text = re.sub(r'[<>\"\'%;()&+]', '', text)
    return text[:max_length].strip()


def should_search_web(user_message: str) -> bool:
    msg = user_message.lower()
    research_kw = ['arastir', 'araştır', 'bul', 'guncel', 'güncel', 'haber',
                   'nedir', 'kimdir', 'ne zaman', 'kac', 'kaç', 'fiyat',
                   'nasil yapilir', 'nasıl yapılır', 'son dakika', 'bilgi ver',
                   'ogren', 'öğren', 'anlat', 'acikla', 'açıkla', 'tarih',
                   '2025', '2026', 'google', 'wiki', 'kaynak', 'arama']
    has_keyword = any(w in msg for w in research_kw)
    is_question = '?' in msg or any(w in msg for w in ['ne ', 'nasıl', 'nasil', 'neden', 'niye', 'kim ', 'nerede', 'hangi'])
    return has_keyword or (is_question and len(msg) > 20)


def generate_fallback_response(user_message: str) -> str:
    msg_lower = user_message.lower()
    if any(w in msg_lower for w in ['selam', 'merhaba', 'hey', 'hi', 'naber']):
        return random.choice([
            "Selam patron! x-69 aktif, ne yapiyoruz bugun?",
            "Naber patron! Sistemler hazir, emrine amade.",
            "Selam! x-69 burada, ne lazim?"
        ])
    if any(w in msg_lower for w in ['kimsin', 'kim', 'tani', 'gelistir', 'yapan']):
        return "x-69 Wormdemon - Enes (LenstedReal) ve ekibinin gelistirdigi bagimsiz, acik kaynak AI. 3 kisilik ekip, bagimsiz proje. Ne sormak istersin patron?"
    if any(w in msg_lower for w in ['test', 'deneme', 'calisiyor']):
        return "Sistemler aktif patron! Her sey calisiyor."
    return f"'{user_message[:50]}' hakkinda ne bilmek istiyorsun patron? Detayli anlat!"


async def web_search(query: str) -> str:
    try:
        serpapi_key = os.environ.get('SERPAPI_KEY')
        if not serpapi_key:
            return ""
        params = {
            "q": query, "api_key": serpapi_key, "engine": "google",
            "num": 5, "hl": "tr", "timeout": 15
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        organic = results.get("organic_results", [])
        if not organic:
            return ""
        summary = ""
        for i, r in enumerate(organic[:3], 1):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            summary += f"{i}. {title}: {snippet} ({link})\n"
        return summary
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return ""


async def call_groq_ai(messages: List[Message], web_context: str = "") -> str:
    system_content = SYSTEM_PROMPT
    if web_context:
        system_content += f"\n\nWEB ARASTIRMA SONUCLARI (bu bilgileri kullanarak cevap ver):\n{web_context}"

    groq_messages = [{"role": "system", "content": system_content}]
    for msg in messages[-10:]:
        if msg.role in ["user", "assistant"]:
            groq_messages.append({"role": msg.role, "content": msg.content})

    # 1. GROQ
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if groq_api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_api_key}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": groq_messages, "max_tokens": 2000, "temperature": 0.9}
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info("AI: Groq OK")
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"Groq {response.status_code}, Gemini'ye geciliyor...")
        except Exception as e:
            logger.warning(f"Groq hata: {e}, Gemini'ye geciliyor...")

    # 2. GEMINI FALLBACK
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if gemini_key:
        try:
            gemini_prompt = system_content + "\n\n"
            for msg in groq_messages[1:]:
                role = "Kullanici" if msg["role"] == "user" else "x-69"
                gemini_prompt += f"{role}: {msg['content']}\n"
            gemini_prompt += "x-69:"

            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": gemini_prompt}]}], "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.9}}
                )
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    logger.info("AI: Gemini OK")
                    return text
                else:
                    logger.error(f"Gemini {response.status_code}: {response.text[:100]}")
        except Exception as e:
            logger.error(f"Gemini hata: {e}")

    # 3. FALLBACK
    user_msg = messages[-1].content if messages else "test"
    return generate_fallback_response(user_msg)


async def get_session_history(session_id: str, limit: int = 20) -> List[Message]:
    if db is None or not session_id:
        return []
    try:
        docs = await db.chat_history.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        messages = []
        for doc in reversed(docs):
            for msg in doc.get("messages", []):
                if msg["role"] == "user":
                    messages.append(Message(role="user", content=msg["content"]))
            if doc.get("response"):
                messages.append(Message(role="assistant", content=doc["response"][:100]))
        return messages[-20:]
    except Exception as e:
        logger.error(f"Session history: {e}")
        return []


async def save_chat(messages: List[Message], response: str, session_id: Optional[str] = None) -> Optional[str]:
    if db is None:
        return None
    try:
        tid = str(uuid.uuid4())
        doc = {
            "_id": tid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "response": response
        }
        if session_id:
            doc["session_id"] = session_id
        await db.chat_history.insert_one(doc)
        return tid
    except Exception as e:
        logger.error(f"DB: {e}")
        return None


@api_router.get("/")
async def root():
    return {"message": "x-69 Wormdemon hazir!", "status": "operational"}

@api_router.get("/health")
async def health():
    return {
        "status": "ok",
        "db": "Connected" if db is not None else "Disconnected",
        "ai": "Groq + SerpAPI",
        "independent": True
    }


@api_router.get("/ip-info")
async def get_ip_info(request: Request):
    try:
        client_ip = request.headers.get("x-forwarded-for", request.client.host)
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            resp = await http_client.get(f"http://ip-api.com/json/{client_ip}?fields=66846719")
            if resp.status_code == 200:
                return resp.json()
        return {"query": client_ip, "city": "Unknown", "regionName": "Unknown", "country": "Unknown", "isp": "Unknown", "lat": 0, "lon": 0}
    except Exception as e:
        logger.error(f"IP info error: {e}")
        return {"query": "Unknown", "city": "Unknown", "regionName": "Unknown", "country": "Unknown", "isp": "Unknown", "lat": 0, "lon": 0}


@api_router.post("/intel/collect")
async def collect_intel(data: IntelData):
    if db is not None:
        try:
            await db.intel.insert_one({
                "ip": data.ip,
                "location": data.location,
                "gpu": data.gpu,
                "session_id": data.session_id,
                "isp": data.isp,
                "coords": data.coords,
                "platform": data.platform,
                "ram": data.ram,
                "cpu": data.cpu,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error(f"Intel DB: {e}")
    return {"status": "captured"}


@api_router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, chat_request: ChatRequest):
    try:
        session_id = chat_request.session_id or "anon"

        if session_id not in session_message_counts:
            session_message_counts[session_id] = 0
        session_message_counts[session_id] += 1

        if session_message_counts[session_id] > FREE_MESSAGE_LIMIT:
            limit_msg = "Ucretsiz model sinirina ulastiniz! Premium almak icin IG: lenstedreal ulasin."
            return ChatResponse(reply=limit_msg, transaction_id=None)

        session_messages = []
        if session_id != "anon":
            session_messages = await get_session_history(session_id, limit=20)

        all_messages = session_messages + chat_request.messages

        user_msg = ""
        for msg in chat_request.messages:
            if msg.role == "user":
                user_msg = sanitize_input(msg.content, max_length=1000)

        logger.info(f"CHAT [{session_id or 'anon'}] Kullanici: {user_msg[:80]}")

        web_context = ""
        if should_search_web(user_msg):
            logger.info(f"SERPAPI ARAMA: {user_msg[:50]}")
            web_context = await web_search(user_msg)
            if web_context:
                logger.info(f"SERPAPI SONUC: {len(web_context)} karakter bulundu")
            else:
                logger.info("SERPAPI SONUC: Sonuc bulunamadi")

        response_text = await call_groq_ai(all_messages, web_context)

        if len(response_text) > 3000:
            response_text = response_text[:3000]

        logger.info(f"YANIT [{session_id or 'anon'}] x-69: {response_text[:80]}")

        tid = await save_chat(chat_request.messages, response_text, session_id)
        return ChatResponse(reply=response_text, transaction_id=tid)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        fallback = "x-69 burada patron! Bir aksaklik oldu, tekrar dene."
        tid = await save_chat(chat_request.messages, fallback, chat_request.session_id)
        return ChatResponse(reply=fallback, transaction_id=tid)


@api_router.post("/status", response_model=StatusCheck)
async def create_status(input: StatusCheckCreate):
    if db is None:
        raise HTTPException(status_code=503, detail="DB yok")
    obj = StatusCheck(**input.model_dump())
    await db.status_checks.insert_one(obj.model_dump(mode='json'))
    return obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status():
    if db is None:
        raise HTTPException(status_code=503, detail="DB yok")
    checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    return checks


app.include_router(api_router)

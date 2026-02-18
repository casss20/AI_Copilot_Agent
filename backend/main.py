from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import nest_asyncio
from dotenv import load_dotenv
import os
import time
import hashlib
import json
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import asyncio
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Import AI models
from .models.openai_model import OpenAIModel
from .models.claude_model import ClaudeModel
from .models.local_model import LocalModel

# Redis connection pool
redis_pool = None

class MockRedis:
    """In-memory Redis fallback"""
    def __init__(self):
        self.data = {}
        self.expiries = {}
        print("[WARNING] Redis unavailable. Using in-memory storage (data will be lost on restart).")

    async def get(self, key):
        self._clean_expired()
        return self.data.get(key)
        
    async def setex(self, key, time, value):
        self.data[key] = value
        self.expiries[key] = datetime.now().timestamp() + time
        return True
        
    async def incr(self, key):
        self._clean_expired()
        val = int(self.data.get(key, 0)) + 1
        self.data[key] = str(val)
        return val
        
    async def lrange(self, key, start, end):
        self._clean_expired()
        lst = self.data.get(key, [])
        if not isinstance(lst, list): return []
        if end == -1: return lst[start:]
        return lst[start:end+1]
        
    async def rpush(self, key, value):
        if key not in self.data: self.data[key] = []
        self.data[key].append(value)
        return len(self.data[key])
        
    async def expire(self, key, time):
        if key in self.data:
            self.expiries[key] = datetime.now().timestamp() + time
        return True
        
    async def delete(self, key):
        if key in self.data: del self.data[key]
        if key in self.expiries: del self.expiries[key]
        return 1
        
    async def ping(self):
        return True

    async def close(self):
        pass

    def _clean_expired(self):
        now = datetime.now().timestamp()
        keys_to_del = [k for k, t in self.expiries.items() if t < now]
        for k in keys_to_del:
            if k in self.data: del self.data[k]
            if k in self.expiries: del self.expiries[k]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis_pool
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    try:
        redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2
        )
        r = redis.Redis(connection_pool=redis_pool)
        await r.ping()
        app.state.redis = r
        print(f"[INFO] Connected to Redis at {redis_url}")
    except Exception as e:
        print(f"[WARNING] Could not connect to Redis: {e}")
        app.state.redis = MockRedis()

    yield
    # Shutdown
    await app.state.redis.close()
    if redis_pool:
        await redis_pool.disconnect()
    print("[INFO] Server shut down")

app = FastAPI(title="AI Copilot Agent", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Rate limiting configuration
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Conversation memory (stored in Redis)
async def get_conversation_history(session_id: str, max_messages: int = 10) -> List[Dict]:
    """Retrieve conversation history from Redis"""
    redis_client = app.state.redis
    key = f"conversation:{session_id}"
    
    # Get last N messages
    messages = await redis_client.lrange(key, -max_messages * 2, -1)
    
    # Parse messages
    history = []
    for msg in messages:
        try:
            history.append(json.loads(msg))
        except:
            continue
    
    return history

async def add_to_conversation(session_id: str, role: str, content: str):
    """Add a message to conversation history"""
    redis_client = app.state.redis
    key = f"conversation:{session_id}"
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    await redis_client.rpush(key, json.dumps(message))
    await redis_client.expire(key, 86400)  # Expire after 24 hours

# Cache middleware
async def get_cached_response(prompt: str, model: str) -> Optional[str]:
    """Get cached response if available"""
    redis_client = app.state.redis
    cache_key = f"cache:{model}:{hashlib.md5(prompt.encode()).hexdigest()}"
    
    cached = await redis_client.get(cache_key)
    return cached if cached else None

async def cache_response(prompt: str, model: str, response: str, ttl: int = 3600):
    """Cache a response"""
    redis_client = app.state.redis
    cache_key = f"cache:{model}:{hashlib.md5(prompt.encode()).hexdigest()}"
    await redis_client.setex(cache_key, ttl, response)

# Rate limiting middleware
async def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit"""
    redis_client = app.state.redis
    key = f"rate_limit:{client_ip}"
    
    # Get current count
    current = await redis_client.get(key)
    
    if current is None:
        # First request in window
        await redis_client.setex(key, RATE_LIMIT_WINDOW, 1)
        return True
    
    current = int(current)
    if current >= RATE_LIMIT:
        return False
    
    # Increment counter
    await redis_client.incr(key)
    return True

# Authentication
API_KEYS = {
    "test_key": "user1",  # In production, store in database
}

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key"""
    api_key = credentials.credentials
    if api_key not in API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return API_KEYS[api_key]

# AI Models initialization
models = {
    "gpt4": OpenAIModel(model="gpt-4o"),
    "gpt35": OpenAIModel(model="gpt-3.5-turbo"),
    "claude": ClaudeModel(model="claude-opus-4-6"),
    "local": LocalModel(model_path=os.getenv("LOCAL_MODEL_PATH", "./models/local")),
}

# Specialized copilot prompts
SPECIALIZED_PROMPTS = {
    "python": """You are a Python expert. Provide concise Python code solutions with best practices.
                 Include docstrings and type hints when relevant. Focus on Python-specific features.""",
    
    "javascript": """You are a JavaScript/TypeScript expert. Provide modern ES6+ solutions.
                     Include proper error handling and async/await patterns when relevant.""",
    
    "debug": """You are a debugging expert. Analyze code for bugs, suggest fixes, and explain 
                why the issue occurs. Provide step-by-step debugging strategies.""",
    
    "general": """You are a helpful programming copilot. Answer questions concisely with code examples.
                  Provide documentation links when relevant. If unsure, say "I don't know"."""
}

# API Endpoints
@app.post("/copilot")
async def general_copilot(
    request: Request,
    auth_user: str = Depends(verify_api_key)
):
    """General programming copilot"""
    return await process_request(request, "general")

@app.post("/copilot/python")
async def python_copilot(
    request: Request,
    auth_user: str = Depends(verify_api_key)
):
    """Python specialist copilot"""
    return await process_request(request, "python")

@app.post("/copilot/javascript")
async def javascript_copilot(
    request: Request,
    auth_user: str = Depends(verify_api_key)
):
    """JavaScript specialist copilot"""
    return await process_request(request, "javascript")

@app.post("/copilot/debug")
async def debug_copilot(
    request: Request,
    auth_user: str = Depends(verify_api_key)
):
    """Debugging specialist copilot"""
    return await process_request(request, "debug")

async def process_request(request: Request, copilot_type: str):
    """Process incoming requests with all enhancements"""
    
    # Get client IP for rate limiting
    client_ip = request.client.host
    
    # Check rate limit
    if not await check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    
    # Parse request body
    body = await request.json()
    user_prompt = body.get("prompt")
    session_id = body.get("session_id", client_ip)  # Use client IP as default session
    model_choice = body.get("model", "gpt4")  # Default to GPT-4
    
    if not user_prompt:
        raise HTTPException(status_code=400, detail="No prompt provided")
    
    # Check cache first
    cached_response = await get_cached_response(user_prompt, model_choice)
    if cached_response:
        return {
            "response": cached_response,
            "cached": True,
            "model": model_choice,
            "copilot_type": copilot_type
        }
    
    # Get conversation history
    history = await get_conversation_history(session_id)
    
    # Get specialized prompt
    system_prompt = SPECIALIZED_PROMPTS.get(copilot_type, SPECIALIZED_PROMPTS["general"])
    
    # Select and use AI model
    model = models.get(model_choice)
    if not model:
        raise HTTPException(status_code=400, detail=f"Invalid model choice: {model_choice}")
    
    try:
        # Generate response
        response = await model.generate_response(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            conversation_history=history
        )
        
        # Cache the response
        await cache_response(user_prompt, model_choice, response)
        
        # Store in conversation history
        await add_to_conversation(session_id, "user", user_prompt)
        await add_to_conversation(session_id, "assistant", response)
        
        return {
            "response": response,
            "cached": False,
            "model": model_choice,
            "copilot_type": copilot_type,
            "session_id": session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI model error: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_client = app.state.redis
    redis_status = "connected" if await redis_client.ping() else "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis": redis_status,
        "models_available": list(models.keys())
    }

# Get conversation history endpoint
@app.get("/history/{session_id}")
async def get_history(
    session_id: str,
    auth_user: str = Depends(verify_api_key)
):
    """Get conversation history for a session"""
    history = await get_conversation_history(session_id, max_messages=50)
    return {"session_id": session_id, "history": history}

# Clear history endpoint
@app.delete("/history/{session_id}")
async def clear_history(
    session_id: str,
    auth_user: str = Depends(verify_api_key)
):
    """Clear conversation history for a session"""
    redis_client = app.state.redis
    key = f"conversation:{session_id}"
    await redis_client.delete(key)
    return {"message": f"History cleared for session {session_id}"}

if __name__ == "__main__":
    nest_asyncio.apply()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
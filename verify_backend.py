import asyncio
import sys
import os
from fastapi import FastAPI

# Add backend to path - NOT NEEDED with proper package structure
# sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend.main import app, lifespan, MockRedis
    print("✅ Imported backend.main successfully")
except ImportError as e:
    print(f"❌ Failed to import backend.main: {e}")
    sys.exit(1)

async def test_startup():
    print("Testing application startup...")
    async with lifespan(app):
        redis_client = app.state.redis
        print(f"Redis client type: {type(redis_client)}")
        
        if isinstance(redis_client, MockRedis):
            print("✅ Correctly using MockRedis fallback")
        else:
            print("ℹ️ Connected to real Redis")
            
        # Test basic operations
        await redis_client.setex("test_key", 10, "value")
        val = await redis_client.get("test_key")
        print(f"Set/Get test: {val}")
        
        if val == "value":
            print("✅ Redis/MockRedis operations working")
        else:
            print("❌ Redis/MockRedis operations failed")

if __name__ == "__main__":
    try:
        asyncio.run(test_startup())
    except Exception as e:
        print(f"❌ Startup test failed: {e}")

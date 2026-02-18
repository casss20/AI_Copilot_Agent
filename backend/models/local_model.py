import httpx
import os
import json
from typing import List, Dict, Optional

class LocalModel:
    def __init__(self, model_path: str = None, model_name: str = "llama3"):
        # model_path is kept for compatibility but we mainly use model_name for Ollama
        self.model_name = model_name
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    async def generate_response(
        self,
        user_prompt: str,
        system_prompt: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """Generate response using local Ollama model"""
        
        # Build prompt/messages structure
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": 0.7
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("message", {}).get("content", "")
                else:
                    return f"Error: Local model returned status {response.status_code}"
                    
        except httpx.ConnectError:
            return "Error: Could not connect to local Ollama instance. Is it running?"
        except Exception as e:
            return f"Error generating response: {str(e)}"
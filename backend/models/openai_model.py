from openai import AsyncOpenAI
import os
from typing import List, Dict, Optional

class OpenAIModel:
    def __init__(self, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def generate_response(
        self,
        user_prompt: str,
        system_prompt: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """Generate response using OpenAI model"""

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current prompt
        messages.append({"role": "user", "content": user_prompt})

        # Get response
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )

        return response.choices[0].message.content
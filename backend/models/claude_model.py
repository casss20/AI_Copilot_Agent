import anthropic
import os
from typing import List, Dict, Optional

class ClaudeModel:
    def __init__(self, model: str = "claude-opus-4-6"):
        self.client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    async def generate_response(
        self,
        user_prompt: str,
        system_prompt: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """Generate response using Claude model"""

        # Build conversation
        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current prompt
        messages.append({"role": "user", "content": user_prompt})

        # Get response
        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=messages,
            max_tokens=1000,
            temperature=0.3
        )

        return response.content[0].text
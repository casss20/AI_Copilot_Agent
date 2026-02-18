import asyncio
import httpx
import os
from dotenv import load_dotenv
from models.local_model import LocalModel

load_dotenv()

async def test_all_models():
    """Test all available Ollama models"""
    
    models_to_test = [
        "deepseek-coder:latest",
        "deepseek-coder:1.3b",
        "qwen2.5:1.5b",
        "qwen2.5:0.5b"
    ]
    
    test_prompts = [
        "Write a Python function to sort a list",
        "Explain async/await in JavaScript",
        "How do I read a CSV file in Python?"
    ]
    
    print("🔍 Testing Ollama models...\n")
    
    for model_name in models_to_test:
        print(f"📦 Testing model: {model_name}")
        print("-" * 50)
        
        # Test each model
        model = LocalModel()
        model.model_name = model_name
        
        for prompt in test_prompts[:1]:  # Test just first prompt for brevity
            print(f"📝 Prompt: {prompt[:50]}...")
            
            try:
                response = await model.generate_response(
                    user_prompt=prompt,
                    system_prompt="You are a helpful programming assistant."
                )
                print(f"✅ Response: {response[:100]}...\n")
            except Exception as e:
                print(f"❌ Error: {e}\n")
        
        print()

async def test_deepseek_coder():
    """Specifically test deepseek-coder for code tasks"""
    
    model = LocalModel()
    model.model_name = "deepseek-coder:latest"
    
    code_tasks = [
        "Write a Python decorator that measures execution time",
        "Create a JavaScript promise that resolves after 2 seconds",
        "Write a SQL query to find duplicate emails in a users table",
        "Create a React component that displays a counter"
    ]
    
    print("🎯 Testing deepseek-coder with code tasks:\n")
    
    for task in code_tasks:
        print(f"📝 Task: {task}")
        print("-" * 50)
        
        response = await model.generate_response(
            user_prompt=task,
            system_prompt="You are an expert programmer. Provide clean, efficient code with explanations."
        )
        
        print(f"{response}\n")
        print("=" * 50)
        print()

if __name__ == "__main__":
    # Test all models
    # asyncio.run(test_all_models())
    
    # Test deepseek-coder specifically
    asyncio.run(test_deepseek_coder())
    
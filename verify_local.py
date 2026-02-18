import asyncio
import sys
import os

# Add backend to path - NOT NEEDED
# sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from backend.models.local_model import LocalModel
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

async def test_local():
    print("Testing LocalModel instantiation...")
    model = LocalModel()
    print("LocalModel instantiated.")
    
    print("Testing generate_response (dry run check)...")
    # We don't expect Ollama to be running necessarily, so we check if it handles connection error gracefully
    response = await model.generate_response(
        user_prompt="Hello",
        system_prompt="You are a helper."
    )
    print(f"Response: {response}")
    
    if "Error" in response or "Response" in response:
        print("LocalModel handled the request (success).")
    else:
        print("Unexpected response format.")

if __name__ == "__main__":
    asyncio.run(test_local())

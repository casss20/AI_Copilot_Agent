import streamlit as st
import requests
import json
import uuid
import pyperclip
from datetime import datetime

# Page config
st.set_page_config(
    page_title="AI Copilot Agent",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stTextArea textarea {
        font-size: 16px;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 5px solid #4caf50;
    }
    .message-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
        font-weight: bold;
    }
    .timestamp {
        color: #666;
        font-size: 0.8rem;
    }
    .code-block {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 0.5rem;
        position: relative;
        margin: 0.5rem 0;
    }
    .copy-btn {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 0.25rem;
        padding: 0.25rem 0.5rem;
        cursor: pointer;
        font-size: 0.8rem;
    }
    .copy-btn:hover {
        background-color: #0056b3;
    }
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if 'api_key' not in st.session_state:
    st.session_state.api_key = "test_key"  # Default test key

# Sidebar configuration
with st.sidebar:
    st.title("⚙️ Settings")
    
    # API Configuration
    st.subheader("API Configuration")
    api_key = st.text_input("API Key", value=st.session_state.api_key, type="password")
    if api_key:
        st.session_state.api_key = api_key
    
    # Model selection
    st.subheader("AI Model")
    model_choice = st.selectbox(
        "Select Model",
        options=["gpt4", "gpt35", "claude", "local"],
        format_func=lambda x: {
            "gpt4": "GPT-4o (OpenAI)",
            "gpt35": "GPT-3.5 Turbo (OpenAI)",
            "claude": "Claude 3 (Anthropic)",
            "local": "Local Model (Llama)"
        }[x]
    )
    
    # Copilot type selection
    st.subheader("Copilot Type")
    copilot_type = st.selectbox(
        "Specialization",
        options=["general", "python", "javascript", "debug"],
        format_func=lambda x: {
            "general": "🤖 General Programming",
            "python": "🐍 Python Expert",
            "javascript": "📜 JavaScript Expert",
            "debug": "🐛 Debugging Expert"
        }[x]
    )
    
    # Session management
    st.subheader("Session")
    st.code(st.session_state.session_id, language="text")
    
    if st.button("🔄 New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    
    if st.button("🧹 Clear History"):
        st.session_state.messages = []
        st.rerun()
    
    # Stats
    st.subheader("Stats")
    st.metric("Total Messages", len(st.session_state.messages))

# Main content
st.title("🤖 AI Copilot Agent")
st.markdown("Your intelligent programming assistant")

# Create two columns
col1, col2 = st.columns([2, 1])

with col1:
    # Chat history display
    st.subheader("💬 Conversation")
    
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <div class="message-header">
                        <span>👤 You</span>
                        <span class="timestamp">{msg.get('timestamp', '')}</span>
                    </div>
                    <div>{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Process assistant message with code blocks
                content = msg['content']
                
                # Simple code block detection and formatting
                import re
                code_pattern = r'```(\w+)?\n(.*?)```'
                
                def replace_code_block(match):
                    lang = match.group(1) or 'text'
                    code = match.group(2)
                    code_id = str(uuid.uuid4())
                    
                    return f'''
                    <div class="code-block" id="code-{code_id}">
                        <button class="copy-btn" onclick="navigator.clipboard.writeText(`{code.replace('`', '\\`')}`)">
                            📋 Copy
                        </button>
                        <pre><code class="language-{lang}">{code}</code></pre>
                    </div>
                    '''
                
                formatted_content = re.sub(code_pattern, replace_code_block, content, flags=re.DOTALL)
                
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <div class="message-header">
                        <span>🤖 Assistant</span>
                        <span class="timestamp">{msg.get('timestamp', '')}</span>
                    </div>
                    <div>{formatted_content}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Add manual copy buttons for code blocks
                code_blocks = re.findall(code_pattern, content, re.DOTALL)
                for lang, code in code_blocks:
                    if st.button(f"📋 Copy {lang} code", key=f"copy_{uuid.uuid4()}"):
                        pyperclip.copy(code)
                        st.success("Copied to clipboard!")

with col2:
    # Input area
    st.subheader("📝 Ask Something")
    
    user_input = st.text_area(
        "Your question:",
        placeholder="e.g., How do I sort a list in Python?",
        height=100
    )
    
    # Quick examples
    st.subheader("📌 Examples")
    example_questions = {
        "Python": "How do I read a CSV file in Python?",
        "JavaScript": "Explain async/await in JavaScript",
        "Debug": "Why is my list index out of range?",
        "Sorting": "Show me different sorting algorithms in Python"
    }
    
    for category, question in example_questions.items():
        if st.button(f"{category}: {question[:30]}...", key=question):
            user_input = question
    
    # Send button
    if st.button("🚀 Send", type="primary", use_container_width=True):
        if user_input.strip():
            # Add user message to session state
            st.session_state.messages.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # Call backend API
            with st.spinner("🤔 Thinking..."):
                try:
                    # Determine endpoint based on copilot type
                    endpoint = f"http://localhost:8000/copilot"
                    if copilot_type != "general":
                        endpoint += f"/{copilot_type}"
                    
                    response = requests.post(
                        endpoint,
                        json={
                            "prompt": user_input,
                            "session_id": st.session_state.session_id,
                            "model": model_choice
                        },
                        headers={"Authorization": f"Bearer {st.session_state.api_key}"},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Add assistant message
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": data["response"],
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                            "model": data.get("model", "unknown"),
                            "cached": data.get("cached", False)
                        })
                        
                        # Show cache indicator
                        if data.get("cached"):
                            st.info("⚡ Response from cache")
                        
                        st.rerun()
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                        
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend. Make sure the server is running on port 8000")
                except Exception as e:
                    st.error(f"❌ Request failed: {str(e)}")
        else:
            st.warning("⚠️ Please enter a question")

# Footer
st.markdown("---")
st.markdown("🚀 Powered by FastAPI + Streamlit + OpenAI/Claude")
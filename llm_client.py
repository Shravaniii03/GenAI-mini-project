"""
LLM Client — Groq (Free tier)
Get API key at: https://console.groq.com
"""
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def query_llm(prompt: str, temperature: float = 0.7) -> str:
    """Send prompt to LLM and return text response."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=temperature
    )
    return response.choices[0].message.content
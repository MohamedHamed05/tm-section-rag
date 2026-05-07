import os
import requests
from dotenv import load_dotenv

load_dotenv()

def embed_text(text: str|list[str]):
    url = os.getenv("OLLAMA_URL") + "/api/embed"
    try:
        response = requests.post(url, json={"model": os.getenv("OLLAMA_EMBED_MODEL"), "input": text})
        return response.json()["embeddings"]
    except Exception as e:
        print(f"Error occurred while embedding text: {e}")
        return {"error": str(e)}
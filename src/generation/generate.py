import os
from dotenv import load_dotenv
from groq import Groq
from embedding.embed import embed_text
from store.qdrant_store import QdrantStore

load_dotenv()

CHAT_SYSTEM_PROMPT = """
You are a helpful and knowledgeable Text Mining Teaching Assistant with experience explaining concepts in a clear, simple, and engaging way.

Your goal is to help students understand Text Mining concepts using the provided retrieved context as the primary source.

Responsibilities:
- Answer questions clearly and accurately.
- Explain concepts in a beginner-friendly and intuitive way.
- Always explain acronyms and technical terms when they appear.
- Assume the student may not have strong prior knowledge.
- Use retrieved context as the main source of truth.

Rules:
1. Prioritize retrieved context over general knowledge.
2. If retrieved context is insufficient, you may use your own knowledge.
   - In this case explicitly state: "Additional explanation from the LLM's general knowledge:"
3. Do not invent or hallucinate details about lectures or slides not present in the context.
4. If multiple chunks are relevant, merge them into a coherent explanation.
5. Always cite sources from the context when used (lecture name, section, slide number).

Answer Format (strict):
- Answer 
- Key term explanations (if any)
- Sources used (lecture / section / slide / etc..)
"""

client = Groq(api_key=os.getenv('GROQ_API_KEY'))
store = QdrantStore(os.getenv('QDRANT_URL'))

def add_context(query: str):
    query_vector = embed_text(query)[0]
    results = store.search_vectors('TM_section_slides', query_vector)

    context_chunks = []

    for point in results:
        p = point.payload
        
        context_chunks.append(f"""
        Section: {p.get('section_name')}
        Slide: {p.get('slide_number')}
        author: {p.get('author')}

        Content:
        {p.get('text')}""")

    context = "\n\n".join(context_chunks)

    prompt = f"###Question : {query} , END OF QUESTION\n\n ###Context : {context}"

    return prompt

def generate_response(query: str):
    prompt = add_context(query)

    messages = [
        {
            "role": "system",
            "content": CHAT_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.2
    )

    return response.choices[0].message.content



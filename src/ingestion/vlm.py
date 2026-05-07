import os
import time
import groq
from groq import Groq
from utils.util import parse_filename, pdf_to_base64_images

sys_prompt = """"You are processing a university lecture slide for a RAG (Retrieval-Augmented Generation) system.
Your output will be embedded and retrieved by students asking questions about the course material.

Your task is to produce a single dense, coherent text that captures the full informational content 
of this slide. Do the following:

1. TRANSCRIBE all visible text on the slide exactly as it appears — titles, bullet points, 
   labels, captions, annotations, equations, code snippets, table cells, everything.

2. If the slide contains a meaningful visual element (diagram, tree, graph, chart, figure, table):
   - Describe what it shows and its purpose in plain language
   - Include every label, node name, axis title, arrow label, and annotation embedded naturally 
     in the description
   - Explain the relationships or structure shown, not just what it looks like

3. Merge both into a single flowing text. Do not use headers like "Text:" or "Visual:". 
   Write as if you are producing comprehensive study notes for this slide.

Output only the final merged text. No meta-commentary, no preamble."""    

def call_vlm(client: Groq, img: str, max_retries: int = 5, t: float = 0.2) -> str | None:
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": sys_prompt},
                            {"type": "image_url",
                             "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
                        ]
                    }
                ],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                temperature=t
            )
            return response.choices[0].message.content

        except groq.RateLimitError as e:
            retry_after = int(e.response.headers.get("retry-after", 60))
            print(f"[Attempt {attempt}/{max_retries}] Rate limited. Retrying in {retry_after}s...")
            if attempt == max_retries:
                raise
            time.sleep(retry_after)

        except groq.APIError as e:
            print(f"[Attempt {attempt}/{max_retries}] API error: {e}. Retrying in 5s...")
            if attempt == max_retries:
                raise
            time.sleep(5)

def extract_pages_vlm(client: Groq, pdf_path: str) -> dict | None:
    base64_images = pdf_to_base64_images(pdf_path)
    pages = {}
    metadata = parse_filename(pdf_path)
    for i, img in enumerate(base64_images):
        print(f"Processing page {i+1} with VLM...")
        description = call_vlm(client, img)
        pages[i + 1] = {'text': description.strip(), 'metadata': {'slide_txt': description.strip(), 'slide_number': i + 1, 'pdf_path': pdf_path, **metadata}}

    return pages

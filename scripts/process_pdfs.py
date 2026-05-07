import os
import sys
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion.processing import extract_pages_pymupdf
from ingestion.vlm import extract_pages_vlm
from embedding.embed import embed_text
from store.qdrant_store import QdrantStore

load_dotenv()


def get_extraction_method() -> str:
    """Ask user to choose extraction method."""
    print("\n" + "=" * 50)
    print("PDF Processing Tool")
    print("=" * 50)
    print("\nChoose extraction method:")
    print("1. PyMuPDF (fast, text-based)")
    print("2. VLM / Groq (slower, vision-based, better for complex layouts)")

    while True:
        choice = input("\nEnter choice (1 or 2): ").strip()
        if choice in ["1", "2"]:
            return "pymupdf" if choice == "1" else "vlm"
        print("Invalid choice. Please enter 1 or 2.")


def find_pdfs() -> list[Path]:
    """Find all PDFs in the sections folder."""
    sections_dir = Path(__file__).parent.parent / "sections"
    return sorted(sections_dir.glob("*.pdf"))


def process_pdfs(pdf_paths: list[Path], method: str, client=None) -> list[dict]:
    """
    Process all PDFs and return a flat list of page dicts.
    Keying by (lecture_name, slide_number) avoids overwriting pages
    when multiple PDFs share the same slide numbers.
    """
    all_pages = []

    for pdf_path in pdf_paths:
        print(f"\nProcessing: {pdf_path.name}")
        try:
            if method == "pymupdf":
                pages = extract_pages_pymupdf(str(pdf_path), skip_first=True)
            else:
                pages = extract_pages_vlm(client, str(pdf_path))

            all_pages.extend(pages.values())
            print(f"  Extracted {len(pages)} pages from {pdf_path.name}")

        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")

    return all_pages


def embed_and_store(pages: list[dict]):
    """Embed text and store vectors in Qdrant."""
    store = QdrantStore(url="http://localhost", port=6333)
    collection_name = "TM_section_slides"
    vector_size = int(os.getenv("VECTOR_SIZE", 768))

    store.create_collection(collection_name, vector_size)

    print(f"\nEmbedding {len(pages)} pages...")
    vectors_to_store = []

    for page_data in pages:
        text = page_data["text"]
        metadata = page_data["metadata"]
        label = f"{metadata.get('lecture_name')} slide {metadata.get('slide_number')}"

        try:
            embeddings = embed_text(text)

            if isinstance(embeddings, dict) and "error" in embeddings:
                print(f"  Embedding error for {label}: {embeddings['error']}")
                continue

            embedding = embeddings[0] if embeddings else None

            if embedding:
                vectors_to_store.append({
                    "embedding": embedding,
                    "metadata": {**metadata, "text": text}
                })
                print(f"  Embedded {label}")

        except Exception as e:
            print(f"  Error embedding {label}: {e}")

    if vectors_to_store:
        print(f"\nStoring {len(vectors_to_store)} vectors in Qdrant...")
        store.upsert_vectors(collection_name, vectors_to_store)
        print(f"  Done — {len(vectors_to_store)} vectors stored in '{collection_name}'")
    else:
        print("  No vectors to store")


def main():
    """Main entry point."""
    pdf_paths = find_pdfs()
    if not pdf_paths:
        print("No PDFs found in sections folder")
        return

    print(f"Found {len(pdf_paths)} PDF(s):")
    for pdf in pdf_paths:
        print(f"  - {pdf.name}")

    method = get_extraction_method()
    client = Groq() if method == "vlm" else None

    print(f"\nStarting extraction with {method.upper()}...")
    pages = process_pdfs(pdf_paths, method, client)

    if not pages:
        print("No pages extracted")
        return

    print(f"\nTotal pages extracted: {len(pages)}")
    embed_and_store(pages)
    print("\nDone!")


if __name__ == "__main__":
    main()
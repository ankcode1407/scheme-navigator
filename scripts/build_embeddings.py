import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge_base.scheme_loader import load_schemes

SCHEMES_DIR = Path("app") / "schemes"
SCHEMES_JSON_PATH = SCHEMES_DIR / "schemes_full.json"
NPY_PATH = SCHEMES_DIR / "scheme_embeddings.npy"
META_PATH = SCHEMES_DIR / "scheme_embeddings.meta.json"


def get_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def build_text_blob(scheme: dict) -> str:
    name = scheme.get("scheme_name") or scheme.get("name") or "Unknown Scheme"
    brief_description = scheme.get("brief_description") or scheme.get("description") or ""
    
    categories = scheme.get("category") or []
    category_str = ", ".join(categories) if isinstance(categories, list) else str(categories)
    
    tags = scheme.get("tags") or []
    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
    
    # Coherent natural language template
    return (
        f"Scheme Name: {name}. "
        f"Category: {category_str}. "
        f"Description: {brief_description}. "
        f"Tags: {tags_str}."
    )


def main():
    print("Initializing offline embedding precomputation...")
    os.makedirs(SCHEMES_DIR, exist_ok=True)
    
    if not SCHEMES_JSON_PATH.exists():
        print(f"Error: {SCHEMES_JSON_PATH} not found!")
        sys.exit(1)
        
    print("Loading schemes...")
    schemes = load_schemes()
    if not schemes:
        print("Error: No schemes loaded.")
        sys.exit(1)
        
    print(f"Loaded {len(schemes)} schemes.")
    
    # Construct structured text blobs
    texts = [build_text_blob(s) for s in schemes]
    
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    print("Encoding texts to embeddings (this may take a few seconds on CPU)...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # Normalizing simplifies cosine sim to simple dot product!
    )
    
    print(f"Generated matrix of shape {embeddings.shape}.")
    
    # Save the embedding matrix
    print(f"Saving embeddings to {NPY_PATH}...")
    np.save(NPY_PATH, embeddings)
    
    # Generate metadata
    file_hash = get_sha256(SCHEMES_JSON_PATH)
    meta = {
        "sha256": file_hash,
        "scheme_count": len(schemes),
        "dimensions": embeddings.shape[1],
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    print(f"Saving metadata to {META_PATH}...")
    with META_PATH.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        
    print("Pre-downloading/caching cross-encoder model 'cross-encoder/ms-marco-MiniLM-L-6-v2'...")
    try:
        from sentence_transformers import CrossEncoder
        CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        print("Cross-encoder model cached successfully!")
    except Exception as e:
        print(f"Warning: Failed to cache CrossEncoder model: {e}")

    print("Embeddings and model build completed successfully!")


if __name__ == "__main__":
    main()

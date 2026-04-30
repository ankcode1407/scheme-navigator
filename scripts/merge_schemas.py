import json

def merge():
    # Load handcrafted 12 (verified, high quality)
    with open("app/schemes/schemes.json", encoding="utf-8") as f:
        handcrafted = json.load(f)

    # Load LLM-extracted schemes
    try:
        with open("data/schemes_extracted.json", encoding="utf-8") as f:
            extracted = json.load(f)
    except FileNotFoundError:
        print("Run extract_schema.py first")
        return

    # Handcrafted takes priority — never overwrite with LLM version
    handcrafted_ids = {s["id"] for s in handcrafted["schemes"]}
    new_schemes = [s for s in extracted["schemes"]
                   if s["id"] not in handcrafted_ids]

    merged = {
        "schemes": handcrafted["schemes"] + new_schemes
    }

    with open("app/schemes/schemes_full.json", "w",
              encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"Handcrafted:  {len(handcrafted['schemes'])}")
    print(f"LLM-extracted (new): {len(new_schemes)}")
    print(f"Total merged: {len(merged['schemes'])}")
    print("Saved: app/schemes/schemes_full.json")

if __name__ == "__main__":
    merge()
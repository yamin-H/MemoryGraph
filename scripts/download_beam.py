"""One-time script to download BEAM dataset and save locally."""

import json
import ast
from pathlib import Path


def download_beam():
    """Download BEAM benchmark dataset from HuggingFace to local storage."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("Install datasets library first:")
        print("pip install datasets")
        return

    print("Downloading BEAM dataset from HuggingFace...")
    dataset = load_dataset("Mohammadta/BEAM")
    
    print(f"Available splits: {list(dataset.keys())}")

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # Download smallest split only
    split_name = list(dataset.keys())[0]
    print(f"Using split: {split_name}")

    conversations = []
    for item in dataset[split_name]:
        # probing_questions is a string — parse it
        try:
            questions = ast.literal_eval(item["probing_questions"])
        except Exception:
            questions = []

        conversations.append({
            "conversation_seed": item.get("conversation_seed", {}),
            "chat": item.get("chat", []),
            "user_profile": item.get("user_profile", {}),
            "probing_questions": questions,
        })

    output_file = data_dir / "beam_100k.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(conversations, f, indent=2)

    print(f"Saved {len(conversations)} conversations to {output_file}")
    
    # Show first item structure
    if conversations:
        first = conversations[0]
        print(f"\nFirst item keys: {list(first.keys())}")
        print(f"Chat turns: {len(first['chat'])}")
        print(f"Questions: {len(first['probing_questions'])}")
        if first['probing_questions']:
            print(f"First question: {first['probing_questions'][0]}")


if __name__ == "__main__":
    download_beam()
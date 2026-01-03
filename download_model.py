"""download_model.py

Download a model repository from Hugging Face Hub using huggingface_hub.snapshot_download.
"""
import os
import argparse
from huggingface_hub import snapshot_download


def download_model_repo(model_id: str, cache_dir: str = None, token: str = None, revision: str = None) -> str:
    path = snapshot_download(repo_id=model_id, cache_dir=cache_dir, token=token, revision=revision)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a model repo from Hugging Face Hub")
    parser.add_argument("--model-id", required=True, help="Model repo id on HF Hub, e.g., Qwen/Qwen-2.5-32b")
    parser.add_argument("--cache-dir", default=None, help="Directory to place the downloaded repo (optional)")
    parser.add_argument("--revision", default=None, help="Specific revision/commit to download")
    parser.add_argument("--test-tokenizer", action="store_true", help="Load tokenizer after download to verify (needs transformers installed)")
    args = parser.parse_args()

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("Warning: HF_TOKEN not set. You may not have access to private or gated model repos.")

    print(f"Downloading model {args.model_id}...")
    local_path = download_model_repo(args.model_id, cache_dir=args.cache_dir, token=hf_token, revision=args.revision)
    print("Downloaded to:", local_path)

    if args.test_tokenizer:
        try:
            from transformers import AutoTokenizer
            print("Testing tokenizer load from local path...")
            tok = AutoTokenizer.from_pretrained(local_path, trust_remote_code=True)
            print("Tokenizer loaded. Vocab size:", getattr(tok, 'vocab_size', 'unknown'))
        except Exception as e:
            print("Tokenizer test failed:", e)

    print("Done.")

# Loads Qwen2.5-32B-Instruct locally using HuggingFace
# Assumes GPU (recommended: ≥24GB VRAM) or quantized/optimized weights

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"


def load_llm(model_name: str = MODEL_NAME, force_cpu: bool = False):
    """Lazily load tokenizer and model. Imports heavy libs inside the function
    to avoid import-time side effects (segfaults or CUDA init) when the module
    is imported in a minimal environment.

    Parameters:
        model_name: HF model identifier
        force_cpu: if True, force loading on CPU even if CUDA is available

    Returns: (tokenizer, model)
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as e:
        raise RuntimeError("transformers is required to load the LLM. Install with: pip install transformers") from e

    try:
        import torch
    except Exception as e:
        raise RuntimeError("PyTorch is required to load the LLM. Install with: pip install torch") from e

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    # Choose dtype/device settings based on availability and user override
    if force_cpu:
        dtype = torch.float32
        device_map = "cpu"
    else:
        if torch.cuda.is_available():
            # Using device_map="auto" requires the accelerate package.
            try:
                import accelerate  # noqa: F401
            except Exception as exc:
                raise RuntimeError(
                    "CUDA appears available but the `accelerate` package is not installed. "
                    "Install it with: pip install accelerate\n"
                    "Or set force_cpu=True to load the model on CPU (may be slower/higher RAM usage)."
                ) from exc
            dtype = torch.float16
            device_map = "auto"
        else:
            # On CPU-only systems, float32 is safer and will avoid dtype-related crashes
            dtype = torch.float32
            device_map = "cpu"

    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=dtype,
            device_map=device_map,
            trust_remote_code=True
        )
    except Exception as e:
        raise RuntimeError(
            "Failed to load the model. If you're on a CPU-only machine or have insufficient memory, consider using a smaller model or follow the project's guidance to run model sharding/quantization."
        ) from e

    model.eval()
    return tokenizer, model

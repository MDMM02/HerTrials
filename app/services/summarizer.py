import re
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
)

# --- Models ---
PEGASUS_MODEL = "google/pegasus-pubmed"          # summarization (biomed)
REWRITE_MODEL = "google/flan-t5-small"           # rewriting (CPU-friendly)

device = torch.device("cpu")

_pegasus_tokenizer = None
_pegasus_model = None

_rewrite_tokenizer = None
_rewrite_model = None


def _lazy_load_pegasus():
    global _pegasus_tokenizer, _pegasus_model
    if _pegasus_tokenizer is None or _pegasus_model is None:
        print("Loading Pegasus PubMed model...")
        _pegasus_tokenizer = AutoTokenizer.from_pretrained(PEGASUS_MODEL, use_fast=False)
        _pegasus_model = AutoModelForSeq2SeqLM.from_pretrained(PEGASUS_MODEL).to(device)
        _pegasus_model.eval()
        print("Pegasus loaded successfully.")


def _lazy_load_rewriter():
    global _rewrite_tokenizer, _rewrite_model
    if _rewrite_tokenizer is None or _rewrite_model is None:
        print("Loading rewrite model (Flan-T5)...")
        _rewrite_tokenizer = AutoTokenizer.from_pretrained(REWRITE_MODEL, use_fast=True)
        _rewrite_model = AutoModelForSeq2SeqLM.from_pretrained(REWRITE_MODEL).to(device)
        _rewrite_model.eval()
        print("Rewrite model loaded successfully.")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("<n>", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s([?.!,;:])", r"\1", text)
    return text.strip()


def _pegasus_summarize(text: str) -> str:
    _lazy_load_pegasus()

    base = clean_text(text)
    inputs = _pegasus_tokenizer(
        base,
        truncation=True,
        padding="longest",
        max_length=1024,
        return_tensors="pt",
    )

    with torch.no_grad():
        summary_ids = _pegasus_model.generate(
            **{k: v.to(device) for k, v in inputs.items()},
            max_length=200,
            min_length=50,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True,
        )

    out = _pegasus_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return clean_text(out)


def _rewrite(text: str, mode: str) -> str:
    _lazy_load_rewriter()

    base = clean_text(text)

    if mode == "layman":
        prompt = (
            "Rewrite the following scientific summary for a general audience. "
            "Use simple words, short sentences, avoid jargon, keep it accurate:\n\n"
            f"{base}"
        )
        max_len = 220
    elif mode == "children":
        prompt = (
            "Explain the following in a way a 10-year-old can understand. "
            "Very simple words, short sentences, friendly tone. No jargon:\n\n"
            f"{base}"
        )
        max_len = 180
    else:
        return base

    inputs = _rewrite_tokenizer(
        prompt,
        truncation=True,
        padding="longest",
        max_length=512,
        return_tensors="pt",
    )

    with torch.no_grad():
        out_ids = _rewrite_model.generate(
            **{k: v.to(device) for k, v in inputs.items()},
            max_length=max_len,
            min_length=60 if mode == "layman" else 40,
            num_beams=4,
            length_penalty=1.0,
            early_stopping=True,
        )

    out = _rewrite_tokenizer.decode(out_ids[0], skip_special_tokens=True)
    return clean_text(out)


def summarize_text(text: str, mode: str = "scientific") -> str:
    if not text or len(text.strip()) < 50:
        return "No abstract available."

    # Always start from a solid scientific summary
    scientific = _pegasus_summarize(text)

    if mode == "scientific":
        return scientific
    if mode in ("layman", "children"):
        return _rewrite(scientific, mode)

    # fallback
    return scientific

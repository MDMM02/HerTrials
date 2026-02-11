import torch
import re
from transformers import PegasusTokenizer, PegasusForConditionalGeneration

MODEL_NAME = "google/pegasus-pubmed"
device = torch.device("cpu")

print("Loading Pegasus PubMed model...")

tokenizer = PegasusTokenizer.from_pretrained(MODEL_NAME)
model = PegasusForConditionalGeneration.from_pretrained(MODEL_NAME).to(device)

print("Model loaded successfully.")


def clean_text(text: str) -> str:
    text = text.replace("<n>", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s([?.!,;:])", r"\1", text)
    return text.strip()


def summarize_text(text: str, mode: str = "scientific") -> str:
    if not text or len(text.strip()) < 50:
        return "No abstract available."

    base = clean_text(text)

    if mode == "scientific":
        prompt = base
    elif mode == "layman":
        prompt = f"Explain in simple terms for a general audience:\n{base}"
    elif mode == "children":
        prompt = f"Explain to a 10-year-old with very simple words:\n{base}"
    else:
        prompt = base

    inputs = tokenizer(
        prompt,
        truncation=True,
        padding="longest",
        max_length=1024,
        return_tensors="pt"
    )

    summary_ids = model.generate(
        **inputs,
        max_length=200,
        min_length=50,
        num_beams=4,
        length_penalty=2.0,
        early_stopping=True
    )

    out = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return clean_text(out)

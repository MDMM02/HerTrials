import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_NAME = "google/pegasus-pubmed"

device = torch.device("cpu")

print("Loading Pegasus PubMed model...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=False)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)

print("Model loaded successfully.")


def summarize_text(text: str) -> str:
    if not text:
        return "No abstract available."

    inputs = tokenizer(
        text,
        truncation=True,
        padding=True,
        max_length=1024,
        return_tensors="pt"
    )

    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=200,
        min_length=50,
        num_beams=4,
        length_penalty=2.0,
        early_stopping=True
    )

    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

import torch
from transformers import PegasusTokenizer, PegasusForConditionalGeneration

MODEL_NAME = "google/pegasus-pubmed"

# On force CPU pour stabilité
device = torch.device("cpu")

print("Loading Pegasus PubMed model... (this may take a moment)")
tokenizer = PegasusTokenizer.from_pretrained(MODEL_NAME)
model = PegasusForConditionalGeneration.from_pretrained(MODEL_NAME).to(device)
print("Model loaded successfully.")


def summarize_text(text: str) -> str:
    if not text or len(text.strip()) == 0:
        return "No abstract available."

    inputs = tokenizer(
        text,
        truncation=True,
        padding="longest",
        return_tensors="pt",
        max_length=1024
    )

    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=256,
        min_length=60,
        num_beams=4,
        early_stopping=True
    )

    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    return summary
